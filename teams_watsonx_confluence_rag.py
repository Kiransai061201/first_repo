import os
import asyncio
import logging
from dotenv import load_dotenv
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity
from quart import Quart, request, Response
from botbuilder.core.integration import aiohttp_error_middleware

from langchain_ibm import WatsonxLLM, WatsonxEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, EmbeddingTypes
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import DecodingMethods
from atlassian import Confluence
from langchain.prompts import PromptTemplate

import aiohttp
import time
import requests
import io
import PyPDF2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize IBM Watson components
watsonx_api_key = os.getenv("IBM_WATSON_API_KEY")
watsonx_url = os.getenv("IBM_WATSON_URL")
project_id = os.getenv("IBM_WATSON_PROJECT_ID")

# Confluence configuration
CONFLUENCE_EMAIL = os.getenv("CONFLUENCE_EMAIL")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
CONFLUENCE_BASE_URL = os.getenv("CONFLUENCE_BASE_URL")
CONFLUENCE_SPACE_KEY = os.getenv("CONFLUENCE_SPACE_KEY")

llm = WatsonxLLM(
    model_id=ModelTypes.GRANITE_13B_CHAT_V2.value,
    url=watsonx_url,
    apikey=watsonx_api_key,
    project_id=project_id,
    params={
        GenParams.DECODING_METHOD: DecodingMethods.GREEDY,
        GenParams.MIN_NEW_TOKENS: 1,
        GenParams.MAX_NEW_TOKENS: 300,
        GenParams.STOP_SEQUENCES: ["\n\nHuman:", "\n\nAssistant:"]
    }
)

embeddings = WatsonxEmbeddings(
    model_id=EmbeddingTypes.IBM_SLATE_30M_ENG.value,
    url=watsonx_url,
    apikey=watsonx_api_key,
    project_id=project_id
)

# Initialize Confluence client
confluence = Confluence(
    url=CONFLUENCE_BASE_URL,
    username=CONFLUENCE_EMAIL,
    password=CONFLUENCE_API_TOKEN,
    cloud=True
)

# Create Quart app
app = Quart(__name__)

# Create adapter
SETTINGS = BotFrameworkAdapterSettings(
    app_id=os.environ.get("MicrosoftAppId"),
    app_password=os.environ.get("MicrosoftAppPassword")
)
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Global variables
docsearch = None
current_document = None

def setup_vector_store(content):
    global docsearch
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.create_documents([content])
    if not docs:
        raise ValueError("No content could be extracted from the document.")
    
    docsearch = Chroma.from_documents(docs, embeddings)

async def get_answer(question):
    if docsearch is None:
        return "No document has been processed yet. Please select a Confluence page or attachment first."
    
    custom_prompt_template = """You are an AI assistant that only answers questions based on the given context. 
    Do not use any external knowledge or information not present in the context.
    If the answer cannot be found in the context, or if the context is not relevant to the question, say "I don't have enough information to answer that question based on the current document."
    Be very strict about only using information from the given context.

    Context: {context}

    Question: {question}

    Answer:"""

    CUSTOM_PROMPT = PromptTemplate(
        template=custom_prompt_template, input_variables=["context", "question"]
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=docsearch.as_retriever(search_kwargs={"k": 3}),
        chain_type="stuff",
        return_source_documents=True,
        chain_type_kwargs={"prompt": CUSTOM_PROMPT}
    )
    
    start = time.process_time()
    try:
        response = await qa_chain.acall({"query": question})
        print("Response time:", time.process_time() - start)
        
        # Check if the retrieved documents are relevant
        if not response['source_documents'] or all(doc.page_content.strip() == '' for doc in response['source_documents']):
            return "I don't have enough information to answer that question based on the current document."
        
        # Check if the answer is actually relevant to the question
        if "I don't have enough information" in response['result'] or len(response['result']) < 10:
            return "I don't have enough information to answer that question based on the current document."
        
        return response['result']
    except Exception as e:
        logging.error(f"Error during retrieval: {e}")
        return "An error occurred while retrieving the answer from the current document."


async def get_confluence_pages():
    try:
        pages = confluence.get_all_pages_from_space(CONFLUENCE_SPACE_KEY, start=0, limit=50)
        return [{"id": page["id"], "title": page["title"]} for page in pages], None
    except Exception as e:
        return None, f"Error during Confluence page retrieval: {str(e)}"

async def get_confluence_attachments(page_id="851969"):  # Use a specific page ID or make it dynamic
    try:
        attachments = confluence.get_attachments_from_content(page_id)
        if attachments['results']:
            attachment_list = []
            for att in attachments['results']:
                attachment_list.append({
                    "id": att['id'],
                    "title": att['title'],
                    "type": att['metadata']['mediaType'],
                    "downloadUrl": att['_links']['download']
                })
            return attachment_list, None
        else:
            return None, "No attachments found on the specified Confluence page."
    except Exception as e:
        return None, f"Error during Confluence attachment retrieval: {str(e)}"

async def get_attachment_content(download_url):
    auth = aiohttp.BasicAuth(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN)
    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.get(f"{CONFLUENCE_BASE_URL}{download_url}") as response:
            if response.status == 200:
                return await response.read()
            else:
                raise Exception(f"Failed to download attachment. Status code: {response.status}")

def extract_pdf_content(pdf_bytes):
    pdf_file = io.BytesIO(pdf_bytes)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

async def get_and_process_document(doc_name):
    global current_document, docsearch
    try:
        # Check if it's a page or an attachment
        pages, error = await get_confluence_pages()
        if error:
            return False, error
        
        for page in pages:
            if page['title'].lower() == doc_name.lower():
                # It's a page
                page_content = confluence.get_page_by_id(page['id'], expand='body.storage')['body']['storage']['value']
                setup_vector_store(page_content)
                current_document = doc_name
                return True, f"Page '{doc_name}' is now ready for questions. Use /askdoc to ask questions."
        
        # If not found as a page, check attachments
        attachments, error = await get_confluence_attachments()
        if error:
            return False, error
        
        for att in attachments:
            if att['title'].lower() == doc_name.lower():
                # It's an attachment
                attachment_content = await get_attachment_content(att['downloadUrl'])
                if att['type'] == 'application/pdf':
                    # Process PDF content
                    pdf_content = extract_pdf_content(attachment_content)
                    setup_vector_store(pdf_content)
                else:
                    # For other types, assume it's text
                    setup_vector_store(attachment_content.decode('utf-8'))
                current_document = doc_name
                return True, f"Attachment '{doc_name}' is now ready for questions. Use /askdoc to ask questions."
        
        return False, f"Document '{doc_name}' not found as a page or attachment."
    except Exception as e:
        return False, f"Error processing document: {str(e)}"

class TeamsBot:
    async def on_turn(self, turn_context: TurnContext):
        if turn_context.activity.type == "message":
            text = turn_context.activity.text.lower()
            if text.startswith("/listdocs"):
                pages, error = await get_confluence_pages()
                if error:
                    await turn_context.send_activity(f"Error: {error}")
                else:
                    page_list = "\n".join(f"{i+1}. {page['title']} (ID: {page['id']})" for i, page in enumerate(pages))
                    await turn_context.send_activity(f"Pages in Confluence:\n\n{page_list}")
            elif text.startswith("/listattachments"):
                attachments, error = await get_confluence_attachments()
                if error:
                    await turn_context.send_activity(f"Error: {error}")
                else:
                    if attachments:
                        attachment_list = "Attachments on the Confluence page:\n"
                        for att in attachments:
                            attachment_list += f"- {att['title']} (Type: {att['type']}, ID: {att['id']})\n"
                        await turn_context.send_activity(attachment_list)
                    else:
                        await turn_context.send_activity("No attachments found on the specified Confluence page.")
            elif text.startswith("/usedoc"):
                doc_name = text[len("/usedoc"):].strip()
                success, message = await get_and_process_document(doc_name)
                await turn_context.send_activity(message)
            elif text.startswith("/askdoc"):
                if current_document:
                    question = text[len("/askdoc"):].strip()
                    answer = await get_answer(question)
                    await turn_context.send_activity(f"Based on '{current_document}': {answer}")
                else:
                    await turn_context.send_activity("Please use /usedoc to select a Confluence page or attachment first.")
            else:
                await turn_context.send_activity("Available commands:\n/listdocs - List Confluence pages\n/listattachments - List attachments\n/usedoc [filename] - Select a document to use\n/askdoc [question] - Ask a question about the selected document")

BOT = TeamsBot()

@app.route("/api/messages", methods=["POST"])
async def messages():
    if "application/json" in request.headers["Content-Type"]:
        body = await request.get_json()
    else:
        return Response(status=415)

    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    try:
        response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
        if response:
            return Response(status=response.status, headers=response.headers)
        return Response(status=201)
    except Exception as exception:
        logging.error(f"Error processing activity: {str(exception)}")
        return Response(status=500)

if __name__ == "__main__":
    app.run(debug=False, port=3978)