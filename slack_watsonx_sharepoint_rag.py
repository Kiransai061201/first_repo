import os
import time
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_ibm import WatsonxLLM, WatsonxEmbeddings
from ibm_watsonx_ai.foundation_models.utils.enums import EmbeddingTypes, ModelTypes
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import DecodingMethods
from msal import ConfidentialClientApplication
import tempfile
from urllib.parse import quote, urlparse

load_dotenv()

# Load IBM Watsonx credentials
watsonx_api_key = os.getenv("IBM_WATSON_API_KEY")
watsonx_url = os.getenv("IBM_WATSON_URL")
project_id = os.getenv("IBM_WATSON_PROJECT_ID")

# Initialize the Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# Initialize Watsonx LLM and Embeddings
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

embeddings = WatsonxEmbeddings(
    model_id=EmbeddingTypes.IBM_SLATE_30M_ENG.value,
    url=watsonx_url,
    apikey=watsonx_api_key,
    project_id=project_id
)

# Global variables
docsearch = None
current_pdf = None

# SharePoint configuration
SHAREPOINT_SITE_URL = os.getenv("SHAREPOINT_SITE_URL")
SHAREPOINT_DOCUMENT_LIBRARY = os.getenv("SHAREPOINT_DOCUMENT_LIBRARY")
SHAREPOINT_CLIENT_ID = os.getenv("SHAREPOINT_CLIENT_ID")
SHAREPOINT_CLIENT_SECRET = os.getenv("SHAREPOINT_CLIENT_SECRET")
SHAREPOINT_TENANT_ID = os.getenv("SHAREPOINT_TENANT_ID")

def setup_vector_store(file_path):
    global docsearch

    loader = PyPDFLoader(file_path)
    docs = loader.load()
    if not docs:
        raise ValueError("No documents found in the PDF.")
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    final_documents = text_splitter.split_documents(docs)
    if not final_documents:
        raise ValueError("No text could be extracted from the PDF.")
    
    docsearch = Chroma.from_documents(final_documents, embeddings)

def get_answer(question):
    if docsearch is None:
        return "No document has been processed yet. Please use /usedoc to select a document first."

    qa_prompt = PromptTemplate(
        template="""You are an AI assistant that answers questions based on the given context. 
        If the answer cannot be found in the context, say "I'm sorry, but I don't have enough information to answer that question based on the document I've been given."
        Do not use any external knowledge.

        Context: {context}

        Human: {question}
        AI Assistant: Provide a clear and concise answer to the question based on the given context. If the information is not in the context, state that you don't have enough information to answer.""",
        input_variables=["context", "question"]
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=docsearch.as_retriever(),
        chain_type="stuff",
        chain_type_kwargs={"prompt": qa_prompt}
    )

    start = time.process_time()
    try:
        response = qa_chain({"query": question})
        print("Response time:", time.process_time() - start)
        answer = response.get('result', 'No output found')
        
        # Remove any mention of sources or file paths
        answer = answer.split("\n\nSources:")[0]
        answer = answer.replace("C:\\Users\\PC\\AppData\\Local\\Temp\\", "")
        
        return answer.strip()
    except Exception as e:
        print(f"Error during retrieval: {e}")
        return "An error occurred while retrieving the answer."

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
        
        site_response = requests.get(f"https://graph.microsoft.com/v1.0/sites/{host}:/sites/{site_path}", headers=headers)
        site_data = site_response.json()
        if 'id' not in site_data:
            return None, f"Failed to retrieve SharePoint site information. Response: {site_data}"
        site_id = site_data['id']
        
        drives_response = requests.get(f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives", headers=headers)
        drives_data = drives_response.json()
        if 'value' not in drives_data:
            return None, f"Failed to retrieve SharePoint drives information. Response: {drives_data}"
        drive = next((d for d in drives_data['value'] if d['name'] == SHAREPOINT_DOCUMENT_LIBRARY), None)
        if not drive:
            return None, f"Document library '{SHAREPOINT_DOCUMENT_LIBRARY}' not found."
        drive_id = drive['id']
        
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
        
        site_response = requests.get(f"https://graph.microsoft.com/v1.0/sites/{host}:/sites/{site_path}", headers=headers)
        site_data = site_response.json()
        if 'id' not in site_data:
            return False, f"Failed to retrieve SharePoint site information. Response: {site_data}"
        site_id = site_data['id']
        
        drives_response = requests.get(f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives", headers=headers)
        drives_data = drives_response.json()
        if 'value' not in drives_data:
            return False, f"Failed to retrieve SharePoint drives information. Response: {drives_data}"
        drive = next((d for d in drives_data['value'] if d['name'] == SHAREPOINT_DOCUMENT_LIBRARY), None)
        if not drive:
            return False, f"Document library '{SHAREPOINT_DOCUMENT_LIBRARY}' not found."
        drive_id = drive['id']
        
        encoded_filename = quote(filename)
        file_response = requests.get(f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/General/{encoded_filename}:/content", headers=headers, allow_redirects=False)
        
        if file_response.status_code == 302:  # Redirect response
            download_url = file_response.headers['Location']
        else:
            return False, f"Failed to retrieve download URL for {filename}. Status: {file_response.status_code}, Response: {file_response.text}"

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