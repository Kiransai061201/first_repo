import os
import asyncio
import logging
from dotenv import load_dotenv
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity, ActivityTypes, Attachment
from quart import Quart, request, Response
from botbuilder.core.integration import aiohttp_error_middleware

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_ibm import WatsonxLLM, WatsonxEmbeddings
from ibm_watsonx_ai.foundation_models.utils.enums import EmbeddingTypes, ModelTypes
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import DecodingMethods

import aiohttp
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Load IBM Watsonx credentials
watsonx_api_key = os.getenv("IBM_WATSON_API_KEY")
watsonx_url = os.getenv("IBM_WATSON_URL")
project_id = os.getenv("IBM_WATSON_PROJECT_ID")

# Debug: Print environment variables
print(f"API Key: {watsonx_api_key}")
print(f"URL: {watsonx_url}")
print(f"Project ID: {project_id}")

# Initialize Watsonx LLM and Embeddings
try:
    llm = WatsonxLLM(
        model_id=ModelTypes.GRANITE_13B_CHAT_V2.value,
        url=watsonx_url,
        apikey=watsonx_api_key,
        project_id=project_id,
        params={
            GenParams.DECODING_METHOD: DecodingMethods.GREEDY,
            GenParams.MIN_NEW_TOKENS: 1,
            GenParams.MAX_NEW_TOKENS: 100,
            GenParams.STOP_SEQUENCES: [".", "?", "!"]
        }
    )
    logging.info("WatsonxLLM initialized successfully")
except Exception as e:
    logging.error(f"Error initializing WatsonxLLM: {str(e)}")
    raise

try:
    embeddings = WatsonxEmbeddings(
        model_id=EmbeddingTypes.IBM_SLATE_30M_ENG.value,
        url=watsonx_url,
        apikey=watsonx_api_key,
        project_id=project_id
    )
    logging.info("WatsonxEmbeddings initialized successfully")
except Exception as e:
    logging.error(f"Error initializing WatsonxEmbeddings: {str(e)}")
    raise

# Global variable to store vector store
docsearch = None

# Create Quart app
app = Quart(__name__)

# Create adapter
SETTINGS = BotFrameworkAdapterSettings(
    app_id=os.environ.get("MicrosoftAppId"),
    app_password=os.environ.get("MicrosoftAppPassword")
)
ADAPTER = BotFrameworkAdapter(SETTINGS)

def setup_vector_store(file_path):
    global docsearch
    
    logging.info(f"Setting up vector store for file: {file_path}")
    # Load and process the uploaded PDF
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    if not docs:
        logging.warning("No documents found in the PDF.")
        raise ValueError("No documents found in the PDF.")
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    final_documents = text_splitter.split_documents(docs)
    if not final_documents:
        logging.warning("No text could be extracted from the PDF.")
        raise ValueError("No text could be extracted from the PDF.")
    
    # Create Chroma vector store
    docsearch = Chroma.from_documents(final_documents, embeddings)
    logging.info("Vector store setup completed successfully.")

async def get_answer(question):
    if docsearch is None:
        return "No document has been processed yet. Please upload a PDF file first."

    # Set up a RetrievalQA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=docsearch.as_retriever(),
        chain_type="stuff",  # Use "map_reduce" or "refine" for larger documents
    )

    try:
        # Run the chain with the question
        response = await qa_chain.acall({"query": question})
        return response.get('result', 'No output found')
    except Exception as e:
        logging.error(f"Error during retrieval: {e}")
        return "An error occurred while retrieving the answer."

class TeamsBot:
    async def on_turn(self, turn_context: TurnContext):
        if turn_context.activity.type == ActivityTypes.message:
            text = turn_context.activity.text.lower() if turn_context.activity.text else ""
            if text.startswith("/askdoc"):
                question = text[len("/askdoc"):].strip()
                answer = await get_answer(question)
                await turn_context.send_activity(answer)
            elif turn_context.activity.attachments:
                await self.handle_file_upload(turn_context)
            else:
                await turn_context.send_activity("I can answer questions about uploaded documents. Use /askdoc followed by your question, or upload a PDF file.")

    async def handle_file_upload(self, turn_context: TurnContext):
        for attachment in turn_context.activity.attachments:
            if attachment.content_type == "application/vnd.microsoft.teams.file.download.info":
                file_download_info = attachment.content
                file_url = file_download_info.get('downloadUrl')
                
                if file_url and attachment.name.lower().endswith('.pdf'):
                    file_content = await self.download_file(file_url)
                    if file_content:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                            temp_file.write(file_content)
                            temp_file_path = temp_file.name
                        
                        logging.info(f"Temporary file created: {temp_file_path}")
                        try:
                            setup_vector_store(temp_file_path)
                            await turn_context.send_activity(f"PDF {attachment.name} has been processed and is ready for queries.")
                        except Exception as e:
                            logging.error(f"Error processing PDF: {str(e)}")
                            await turn_context.send_activity(f"Error processing PDF: {str(e)}")
                        finally:
                            os.unlink(temp_file_path)
                            logging.info(f"Temporary file deleted: {temp_file_path}")
                    else:
                        await turn_context.send_activity("Failed to download the PDF file.")
                else:
                    await turn_context.send_activity(f"Unsupported file type: {attachment.name}. Please upload a PDF file.")
            else:
                logging.warning(f"Unsupported attachment type: {attachment.content_type}")
        
        if not any(att.content_type == "application/vnd.microsoft.teams.file.download.info" for att in turn_context.activity.attachments):
            await turn_context.send_activity("Please upload a valid PDF file.")

    async def download_file(self, file_url: str) -> bytes:
        logging.info(f"Downloading file from URL: {file_url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    content = await response.read()
                    logging.info(f"Successfully downloaded file, Size: {len(content)} bytes")
                    return content
                else:
                    logging.error(f"Failed to download file, Status: {response.status}")
        return None

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
    app.run(debug=True, port=3978)