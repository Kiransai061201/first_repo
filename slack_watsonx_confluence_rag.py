import os
import time
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from langchain_ibm import WatsonxLLM, WatsonxEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, EmbeddingTypes
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import DecodingMethods
from atlassian import Confluence
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
import json
import io
import PyPDF2

load_dotenv()

# Load API keys and configuration
watsonx_api_key = os.getenv("IBM_WATSON_API_KEY")
watsonx_url = os.getenv("IBM_WATSON_URL")
project_id = os.getenv("IBM_WATSON_PROJECT_ID")
CONFLUENCE_EMAIL = os.getenv("CONFLUENCE_EMAIL")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
CONFLUENCE_BASE_URL = os.getenv("CONFLUENCE_BASE_URL")
CONFLUENCE_SPACE_KEY = os.getenv("CONFLUENCE_SPACE_KEY")

# Initialize the Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# Initialize Watson LLM and Embeddings
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

def get_answer(question):
    if docsearch is None:
        return "No document has been processed yet. Please select a Confluence page or attachment first."
    
    custom_prompt_template = """You are an AI assistant that only answers questions based on the given context. 
    Do not use any external knowledge or information not present in the context.
    If the answer cannot be found in the context, or if the context is not relevant to the question, say "I don't have enough information to answer that question."

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
        response = qa_chain({"query": question})
        print("Response time:", time.process_time() - start)
        
        # Check if the retrieved documents are relevant
        if not response['source_documents'] or all(doc.page_content.strip() == '' for doc in response['source_documents']):
            return "I don't have enough information to answer that question."
        
        # Check if the answer is actually relevant to the question
        if "I don't have enough information" in response['result'] or len(response['result']) < 10:
            return "I don't have enough information to answer that question."
        
        return response['result']
    except Exception as e:
        print(f"Error during retrieval: {e}")
        return "An error occurred while retrieving the answer."

def get_confluence_pages():
    try:
        pages = confluence.get_all_pages_from_space(CONFLUENCE_SPACE_KEY, start=0, limit=50)
        return [{"id": page["id"], "title": page["title"]} for page in pages], None
    except Exception as e:
        return None, f"Error during Confluence page retrieval: {str(e)}"

def get_confluence_pdfs():
    try:
        pages = confluence.get_all_pages_from_space(CONFLUENCE_SPACE_KEY, start=0, limit=50)
        pdf_list = []
        
        for page in pages:
            attachments = confluence.get_attachments_from_content(page['id'])
            pdf_attachments = [att for att in attachments['results'] if att['title'].lower().endswith('.pdf')]
            
            if pdf_attachments:
                pdf_list.append({
                    "page_id": page['id'],
                    "page_title": page['title'],
                    "pdfs": [{"id": pdf['id'], "title": pdf['title']} for pdf in pdf_attachments]
                })
        
        return pdf_list, None
    except Exception as e:
        return None, f"Error during Confluence PDF retrieval: {str(e)}"

def get_confluence_attachments():
    try:
        page_id = "851969"  # Use the specific page ID from the URL
        
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

def get_attachment_content(download_url):
    auth = (CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN)
    response = requests.get(f"{CONFLUENCE_BASE_URL}{download_url}", auth=auth)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Failed to download attachment. Status code: {response.status_code}")

def extract_pdf_content(pdf_bytes):
    pdf_file = io.BytesIO(pdf_bytes)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def get_and_process_document(doc_name):
    global current_document, docsearch
    try:
        # Check if it's a page or an attachment
        pages = confluence.get_all_pages_from_space(CONFLUENCE_SPACE_KEY, start=0, limit=50)
        for page in pages:
            if page['title'].lower() == doc_name.lower():
                # It's a page
                page_content = confluence.get_page_by_id(page['id'], expand='body.storage')['body']['storage']['value']
                setup_vector_store(page_content)
                current_document = doc_name
                return True, f"Page '{doc_name}' is now ready for questions. Use /askdoc to ask questions."
        
        # If not found as a page, check attachments
        attachments, _ = get_confluence_attachments()
        for att in attachments:
            if att['title'].lower() == doc_name.lower():
                # It's an attachment
                attachment_content = get_attachment_content(att['downloadUrl'])
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

@app.command("/listdocs")
def handle_listdocs_command(ack, respond):
    ack()
    pages, error = get_confluence_pages()
    if error:
        respond(f"Error: {error}")
    else:
        if pages:
            page_list = "\n".join(f"{i+1}. {page['title']} (ID: {page['id']})" for i, page in enumerate(pages))
            respond(f"Pages in Confluence:\n\n{page_list}")
        else:
            respond("No pages found in the specified Confluence space.")

@app.command("/listpdfs")
def handle_listpdfs_command(ack, respond):
    ack()
    pdfs, error = get_confluence_pdfs()
    if error:
        respond(f"Error: {error}")
    else:
        if pdfs:
            pdf_list = ""
            for page in pdfs:
                pdf_list += f"\nPage: {page['page_title']} (ID: {page['page_id']})\n"
                for pdf in page['pdfs']:
                    pdf_list += f"  - {pdf['title']} (ID: {pdf['id']})\n"
            respond(f"PDFs in Confluence:\n{pdf_list}")
        else:
            respond("No PDFs found in the specified Confluence space.")

@app.command("/listattachments")
def handle_listattachments_command(ack, respond):
    ack()
    attachments, error = get_confluence_attachments()
    if error:
        respond(f"Error: {error}")
    else:
        if attachments:
            attachment_list = "Attachments on the Confluence page:\n"
            for att in attachments:
                attachment_list += f"- {att['title']} (Type: {att['type']}, ID: {att['id']})\n"
            respond(attachment_list)
        else:
            respond("No attachments found on the specified Confluence page.")

@app.command("/usedoc")
def handle_usedoc_command(ack, respond, command):
    ack()
    doc_name = command["text"].strip()
    success, message = get_and_process_document(doc_name)
    respond(message)

@app.command("/askdoc")
def handle_askdoc_command(ack, respond, command):
    ack()
    if current_document:
        question = command["text"]
        answer = get_answer(question)
        respond(answer)
    else:
        respond("Please use /usedoc to select a Confluence page or attachment first.")

if __name__ == "__main__":
    print("Starting Slack bot...")
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()