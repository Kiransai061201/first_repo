import os
import asyncio
import logging
from dotenv import load_dotenv
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity, Attachment
from quart import Quart, request, Response
from botbuilder.core.integration import aiohttp_error_middleware

from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings

import aiohttp
import tempfile

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize LLM and other components
groq_api_key = os.getenv('GROQ_API_KEY')
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

llm = ChatGroq(groq_api_key=groq_api_key, model_name="Llama3-8b-8192")

prompt = ChatPromptTemplate.from_template("""
    Answer the questions based on the provided context only.
    Please provide the most accurate response based on the question.
    <context>
    {context}
    </context>
    Question: {input}
    """)

embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
vectors = None

# Create Quart app
app = Quart(__name__)

# Create adapter
SETTINGS = BotFrameworkAdapterSettings(
    app_id=os.environ.get("MicrosoftAppId"),
    app_password=os.environ.get("MicrosoftAppPassword")
)
ADAPTER = BotFrameworkAdapter(SETTINGS)

def setup_vector_store(file_path):
    global vectors
    
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
    
    # Create FAISS vector store
    vectors = FAISS.from_documents(final_documents, embeddings)
    logging.info("Vector store setup completed successfully.")

async def get_answer(question):
    if vectors is None:
        return "No document has been processed yet. Please upload a PDF file first."
    
    document_chain = create_stuff_documents_chain(llm, prompt)
    retriever = vectors.as_retriever()
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    
    response = await retrieval_chain.ainvoke({'input': question})
    
    return response['answer']

class TeamsBot:
    async def on_turn(self, turn_context: TurnContext):
        logging.info(f"Received activity type: {turn_context.activity.type}")
        if turn_context.activity.type == "message":
            if turn_context.activity.text:
                text = turn_context.activity.text.lower()
                if text.startswith("/askdoc"):
                    question = text[len("/askdoc"):].strip()
                    answer = await get_answer(question)
                    await turn_context.send_activity(answer)
                else:
                    await turn_context.send_activity("I can answer questions about uploaded documents. Use /askdoc followed by your question, or upload a PDF file.")
            elif turn_context.activity.attachments:
                await self.handle_file_upload(turn_context)
            else:
                await turn_context.send_activity("I didn't receive any text or attachments. Please try again.")
        else:
            logging.info(f"Received non-message activity: {turn_context.activity.type}")


    async def handle_file_upload(self, turn_context: TurnContext):
        logging.info(f"Handling file upload. Attachments: {len(turn_context.activity.attachments)}")
        for attachment in turn_context.activity.attachments:
            logging.info(f"Processing attachment: {attachment.name}, Content Type: {attachment.content_type}")
            
            if attachment.content_type == "application/vnd.microsoft.teams.file.download.info":
                file_download_info = attachment.content
                file_url = file_download_info.get('downloadUrl')
                
                if file_url and attachment.name.lower().endswith('.pdf'):
                    file_content = await self.download_file(file_url)
                    if file_content:
                        # Create a 'pdfs' directory if it doesn't exist
                        pdf_dir = os.path.join(os.getcwd(), 'pdfs')
                        os.makedirs(pdf_dir, exist_ok=True)
                        
                        # Save the PDF to the 'pdfs' directory
                        file_path = os.path.join(pdf_dir, attachment.name)
                        with open(file_path, 'wb') as pdf_file:
                            pdf_file.write(file_content)
                        
                        logging.info(f"PDF saved to: {file_path}")
                        try:
                            setup_vector_store(file_path)
                            await turn_context.send_activity(f"PDF {attachment.name} has been processed and is ready for queries.")
                        except Exception as e:
                            logging.error(f"Error processing PDF: {str(e)}")
                            await turn_context.send_activity(f"Error processing PDF: {str(e)}")
                    else:
                        logging.error("Failed to download the PDF file.")
                        await turn_context.send_activity("Failed to download the PDF file.")
                else:
                    logging.warning(f"Unsupported file type or missing download URL: {attachment.name}")
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