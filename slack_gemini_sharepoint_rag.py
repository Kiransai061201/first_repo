import os
import time
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from msal import ConfidentialClientApplication
import tempfile
from urllib.parse import quote, urlparse

load_dotenv()

# Load API keys
groq_api_key = os.getenv('GROQ_API_KEY')
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Initialize the Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# Initialize LLM
llm = ChatGroq(groq_api_key=groq_api_key, model_name="Llama3-8b-8192")

# Define prompt template
prompt = ChatPromptTemplate.from_template(
    """
    Answer the questions based on the provided context only.
    Please provide the most accurate response based on the question.
    <context>
    {context}
    </context>
    Question: {input}
    """
)

# Global variables to store vector store and other components
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
vectors = None

# SharePoint configuration
SHAREPOINT_SITE_URL = os.getenv("SHAREPOINT_SITE_URL")
SHAREPOINT_DOCUMENT_LIBRARY = os.getenv("SHAREPOINT_DOCUMENT_LIBRARY")
SHAREPOINT_CLIENT_ID = os.getenv("SHAREPOINT_CLIENT_ID")
SHAREPOINT_CLIENT_SECRET = os.getenv("SHAREPOINT_CLIENT_SECRET")
SHAREPOINT_TENANT_ID = os.getenv("SHAREPOINT_TENANT_ID")

current_pdf = None

def setup_vector_store(file_path):
    global vectors
    
    # Load and process the uploaded PDF
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    if not docs:
        raise ValueError("No documents found in the PDF.")
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    final_documents = text_splitter.split_documents(docs)
    if not final_documents:
        raise ValueError("No text could be extracted from the PDF.")
    
    # Create FAISS vector store
    vectors = FAISS.from_documents(final_documents, embeddings)

def get_answer(question):
    if vectors is None:
        return "No document has been processed yet. Please upload a PDF file first."
    
    document_chain = create_stuff_documents_chain(llm, prompt)
    retriever = vectors.as_retriever()
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    
    start = time.process_time()
    response = retrieval_chain.invoke({'input': question})
    print("Response time:", time.process_time() - start)
    
    return response['answer']

def get_sharepoint_access_token():
    app = ConfidentialClientApplication(
        SHAREPOINT_CLIENT_ID,
        authority=f'https://login.microsoftonline.com/{SHAREPOINT_TENANT_ID}',
        client_credential=SHAREPOINT_CLIENT_SECRET
    )
    result = app.acquire_token_for_client(scopes=['https://graph.microsoft.com/.default'])
    return result.get('access_token')

def get_sharepoint_files():
    try:
        access_token = get_sharepoint_access_token()
        if not access_token:
            return None, "Failed to authenticate with SharePoint."

        parsed_url = urlparse(SHAREPOINT_SITE_URL)
        host = parsed_url.netloc
        site_path = parsed_url.path.strip('/').split('/')[-1]

        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Get site ID
        site_response = requests.get(f"https://graph.microsoft.com/v1.0/sites/{host}:/sites/{site_path}", headers=headers)
        site_data = site_response.json()
        if 'id' not in site_data:
            return None, f"Failed to retrieve SharePoint site information. Response: {site_data}"
        site_id = site_data['id']
        
        # Get drive ID
        drives_response = requests.get(f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives", headers=headers)
        drives_data = drives_response.json()
        if 'value' not in drives_data:
            return None, f"Failed to retrieve SharePoint drives information. Response: {drives_data}"
        drive = next((d for d in drives_data['value'] if d['name'] == SHAREPOINT_DOCUMENT_LIBRARY), None)
        if not drive:
            return None, f"Document library '{SHAREPOINT_DOCUMENT_LIBRARY}' not found."
        drive_id = drive['id']
        
        # Get files in the General folder
        files_response = requests.get(f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/General:/children", headers=headers)
        files_data = files_response.json()
        if 'value' not in files_data:
            return None, f"Failed to retrieve files. Response: {files_data}"
        
        file_names = [item["name"] for item in files_data["value"] if item.get("file") and item["name"].lower().endswith('.pdf')]
        return file_names, None
    except Exception as e:
        return None, f"Error during SharePoint file retrieval: {str(e)}"

def download_and_process_sharepoint_pdf(filename):
    global current_pdf
    try:
        access_token = get_sharepoint_access_token()
        if not access_token:
            return False, "Failed to authenticate with SharePoint."

        parsed_url = urlparse(SHAREPOINT_SITE_URL)
        host = parsed_url.netloc
        site_path = parsed_url.path.strip('/').split('/')[-1]

        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Get site ID
        site_response = requests.get(f"https://graph.microsoft.com/v1.0/sites/{host}:/sites/{site_path}", headers=headers)
        site_data = site_response.json()
        if 'id' not in site_data:
            return False, f"Failed to retrieve SharePoint site information. Response: {site_data}"
        site_id = site_data['id']
        
        # Get drive ID
        drives_response = requests.get(f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives", headers=headers)
        drives_data = drives_response.json()
        if 'value' not in drives_data:
            return False, f"Failed to retrieve SharePoint drives information. Response: {drives_data}"
        drive = next((d for d in drives_data['value'] if d['name'] == SHAREPOINT_DOCUMENT_LIBRARY), None)
        if not drive:
            return False, f"Document library '{SHAREPOINT_DOCUMENT_LIBRARY}' not found."
        drive_id = drive['id']
        
        # Get file download URL
        encoded_filename = quote(filename)
        file_response = requests.get(f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/General/{encoded_filename}:/content", headers=headers, allow_redirects=False)
        
        if file_response.status_code == 302:  # Redirect response
            download_url = file_response.headers['Location']
        else:
            return False, f"Failed to retrieve download URL for {filename}. Status: {file_response.status_code}, Response: {file_response.text}"

        # Download and process the file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            response = requests.get(download_url)
            temp_file.write(response.content)
            temp_file_path = temp_file.name

        try:
            setup_vector_store(temp_file_path)
            current_pdf = filename
            return True, f"Document '{filename}' is now ready for questions. Use /askdoc to ask questions."
        except Exception as e:
            return False, f"Error processing PDF: {str(e)}"
        finally:
            os.unlink(temp_file_path)

    except Exception as e:
        return False, f"An unexpected error occurred: {str(e)}"

@app.command("/listdocs")
def handle_listdocs_command(ack, respond):
    ack()
    files, error = get_sharepoint_files()
    if error:
        respond(f"Error: {error}")
    else:
        file_list = "\n".join(f"{i+1}. {file}" for i, file in enumerate(files))
        respond(f"Files in SharePoint:\n\n{file_list}")

@app.command("/usedoc")
def handle_usedoc_command(ack, respond, command):
    ack()
    doc_name = command["text"].strip()
    success, message = download_and_process_sharepoint_pdf(doc_name)
    respond(message)

@app.command("/askdoc")
def handle_askdoc_command(ack, respond, command):
    ack()
    if current_pdf:
        question = command["text"]
        answer = get_answer(question)
        respond(answer)
    else:
        respond("Please use /usedoc to select a document first.")

@app.event("message")
def handle_file_share_events(event, say):
    if event.get("subtype") == "file_share":
        file_id = event['files'][0]['id']
        file_info = app.client.files_info(file=file_id)['file']
        if file_info['filetype'] == 'pdf':
            file_url = file_info['url_private']
            headers = {
                'Authorization': f"Bearer {os.environ['SLACK_BOT_TOKEN']}"
            }
            response = requests.get(file_url, headers=headers)
            if response.status_code == 200:
                file_path = os.path.join("pdfs", file_info['name'])
                with open(file_path, "wb") as f:
                    f.write(response.content)
                setup_vector_store(file_path)
                global current_pdf
                current_pdf = file_info['name']
                say(f"PDF {file_info['name']} has been processed and is ready for queries.")
            else:
                say("Failed to download the file.")
        else:
            say("Please upload a valid PDF file.")

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()