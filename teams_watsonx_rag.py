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
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from ibm_watsonx_ai.foundation_models.utils.enums import EmbeddingTypes, ModelTypes
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import DecodingMethods
from botbuilder.schema import Attachment, Activity, ActivityTypes

import aiohttp
import time
import requests
from msal import ConfidentialClientApplication
import tempfile
from urllib.parse import quote, urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize IBM Watson components
watsonx_api_key = os.getenv("IBM_WATSON_API_KEY")
watsonx_url = os.getenv("IBM_WATSON_URL")
project_id = os.getenv("IBM_WATSON_PROJECT_ID")

# SharePoint configuration
SHAREPOINT_SITE_URL = os.getenv("SHAREPOINT_SITE_URL")
SHAREPOINT_DOCUMENT_LIBRARY = os.getenv("SHAREPOINT_DOCUMENT_LIBRARY")
SHAREPOINT_CLIENT_ID = os.getenv("SHAREPOINT_CLIENT_ID")
SHAREPOINT_CLIENT_SECRET = os.getenv("SHAREPOINT_CLIENT_SECRET")
SHAREPOINT_TENANT_ID = os.getenv("SHAREPOINT_TENANT_ID")

AVAILABLE_MODELS = {
    "flan_t5_xxl": ModelTypes.FLAN_T5_XXL,
    "flan_ul2": ModelTypes.FLAN_UL2,
    "mt0_xxl": ModelTypes.MT0_XXL,
    "gpt_neox": ModelTypes.GPT_NEOX,
    "mpt_7b_instruct2": ModelTypes.MPT_7B_INSTRUCT2,
    "starcoder": ModelTypes.STARCODER,
    "llama_2_70b_chat": ModelTypes.LLAMA_2_70B_CHAT,
    "llama_2_13b_chat": ModelTypes.LLAMA_2_13B_CHAT,
    "granite_13b_instruct": ModelTypes.GRANITE_13B_INSTRUCT,
    "granite_13b_chat": ModelTypes.GRANITE_13B_CHAT,
    "flan_t5_xl": ModelTypes.FLAN_T5_XL,
    "granite_13b_chat_v2": ModelTypes.GRANITE_13B_CHAT_V2,
    "granite_13b_instruct_v2": ModelTypes.GRANITE_13B_INSTRUCT_V2,
    "elyza_japanese_llama_2_7b_instruct": ModelTypes.ELYZA_JAPANESE_LLAMA_2_7B_INSTRUCT,
    "mixtral_8x7b_instruct_v01_q": ModelTypes.MIXTRAL_8X7B_INSTRUCT_V01_Q,
    "codellama_34b_instruct_hf": ModelTypes.CODELLAMA_34B_INSTRUCT_HF,
    "granite_20b_multilingual": ModelTypes.GRANITE_20B_MULTILINGUAL,
    "merlinite_7b": ModelTypes.MERLINITE_7B,
    "granite_20b_code_instruct": ModelTypes.GRANITE_20B_CODE_INSTRUCT,
    "granite_34b_code_instruct": ModelTypes.GRANITE_34B_CODE_INSTRUCT,
    "granite_3b_code_instruct": ModelTypes.GRANITE_3B_CODE_INSTRUCT,
    "granite_7b_lab": ModelTypes.GRANITE_7B_LAB,
    "granite_8b_code_instruct": ModelTypes.GRANITE_8B_CODE_INSTRUCT,
    "llama_3_70b_instruct": ModelTypes.LLAMA_3_70B_INSTRUCT,
    "llama_3_8b_instruct": ModelTypes.LLAMA_3_8B_INSTRUCT,
    "mixtral_8x7b_instruct_v01": ModelTypes.MIXTRAL_8X7B_INSTRUCT_V01,
}

# Default model
DEFAULT_MODEL = ModelTypes.GRANITE_13B_CHAT_V2

# Initialize LLM with default model
llm = WatsonxLLM(
    model_id=DEFAULT_MODEL.value,
    url=watsonx_url,
    apikey=watsonx_api_key,
    project_id=project_id,
    params={
        GenParams.DECODING_METHOD: DecodingMethods.GREEDY,
        GenParams.MIN_NEW_TOKENS: 1,
        GenParams.MAX_NEW_TOKENS: 1024,
        GenParams.REPETITION_PENALTY: 1.2,
        GenParams.TEMPERATURE: 0.7,
        GenParams.TOP_K: 50,
        GenParams.TOP_P: 0.9,
    }
)

embeddings = WatsonxEmbeddings(
    model_id=EmbeddingTypes.IBM_SLATE_30M_ENG.value,
    url=watsonx_url,
    apikey=watsonx_api_key,
    project_id=project_id
)

# Global variable to store vector store
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
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    if not docs:
        raise ValueError("No documents found in the PDF.")
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    final_documents = text_splitter.split_documents(docs)
    if not final_documents:
        raise ValueError("No text could be extracted from the PDF.")
    
    vectors = Chroma.from_documents(final_documents, embeddings)
    logging.info("Vector store setup completed successfully.")

async def get_answer(question):
    if vectors is None:
        return "No document has been processed yet. Please upload a PDF file first."
    
    prompt = ChatPromptTemplate.from_template("""
    You are an AI assistant that only answers questions based on the provided context.
    If the question cannot be answered using the information in the context, respond with "I'm sorry, but I don't have information about that in the document I've been provided."
    Do not use any external knowledge or make assumptions beyond what is explicitly stated in the context.
    
    Context:
    {context}
    
    Human: {input}
    AI: """)
    
    document_chain = create_stuff_documents_chain(llm, prompt)
    retriever = vectors.as_retriever(search_kwargs={"k": 3})
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    
    try:
        response = await retrieval_chain.ainvoke({'input': question})
        return response['answer'].strip()
    except Exception as e:
        logging.error(f"Error retrieving answer: {str(e)}")
        return f"An error occurred while retrieving the answer: {str(e)}"
    
class TeamsBot:
    def __init__(self):
        self.current_pdf = None
        self.current_model = DEFAULT_MODEL

    async def on_turn(self, turn_context: TurnContext):
        if turn_context.activity.type == "message":
            if turn_context.activity.text:
                text = turn_context.activity.text.lower()
                if text.startswith("/askdoc"):
                    if self.current_pdf:
                        question = text[len("/askdoc"):].strip()
                        answer = await get_answer(question)
                        await turn_context.send_activity(answer)
                    else:
                        await turn_context.send_activity("Please use /usedoc to select a document first.")
                elif text.startswith("/listdocs"):
                    folder_structure, error = await self.get_sharepoint_files()
                    if error:
                        await turn_context.send_activity(f"Error: {error}")
                    else:
                        if folder_structure:
                            card = generate_folder_card(folder_structure)
                            attachment = Attachment(
                                content_type="application/vnd.microsoft.card.adaptive",
                                content=card
                            )
                            await turn_context.send_activity(Activity(
                                type=ActivityTypes.message,
                                attachments=[attachment]
                            ))
                        else:
                            await turn_context.send_activity("No files found in the SharePoint Documents library.")
                elif text.startswith("/usedoc"):
                    doc_name = text[len("/usedoc"):].strip()
                    success, message = await self.download_and_process_sharepoint_pdf(doc_name)
                    await turn_context.send_activity(message)
                elif text.startswith("/select_model"):
                    await self.send_model_selection_card(turn_context)
                elif text.startswith("/listmodels"):
                    model_list = "\n".join(AVAILABLE_MODELS.keys())
                    await turn_context.send_activity(f"Available models:\n{model_list}")
                else:
                    await turn_context.send_activity("Available commands:\n/listdocs - List SharePoint documents\n/usedoc [filename] - Select a document to use\n/askdoc [question] - Ask a question about the selected document\n/select_model - Select an AI model\n/listmodels - List available AI models")
            elif turn_context.activity.attachments:
                await self.handle_file_upload(turn_context)
            elif turn_context.activity.value:
                # Handle adaptive card submissions
                await self.handle_adaptive_card_submission(turn_context)
            else:
                await turn_context.send_activity("I didn't receive any text or attachments. Please try again with a valid command or upload a PDF file.")

    async def send_model_selection_card(self, turn_context: TurnContext):
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.3",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Select a model:",
                    "weight": "Bolder"
                },
                {
                    "type": "Input.ChoiceSet",
                    "id": "modelChoice",
                    "style": "compact",
                    "choices": [
                        {
                            "title": model_name,
                            "value": model_name
                        } for model_name in AVAILABLE_MODELS.keys()
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Select Model",
                    "data": {"action": "selectModel"}
                }
            ]
        }

        attachment = Attachment(
            content_type="application/vnd.microsoft.card.adaptive",
            content=card
        )

        await turn_context.send_activity(Activity(
            type=ActivityTypes.message,
            attachments=[attachment]
        ))

    async def handle_adaptive_card_submission(self, turn_context: TurnContext):
        if turn_context.activity.value.get("action") == "selectModel":
            selected_model = turn_context.activity.value.get("modelChoice")
            if selected_model in AVAILABLE_MODELS:
                self.current_model = AVAILABLE_MODELS[selected_model]
                global llm
                llm = WatsonxLLM(
                    model_id=self.current_model.value,
                    url=watsonx_url,
                    apikey=watsonx_api_key,
                    project_id=project_id,
                    params={
                        GenParams.DECODING_METHOD: DecodingMethods.GREEDY,
                        GenParams.MIN_NEW_TOKENS: 1,
                        GenParams.MAX_NEW_TOKENS: 1024,
                        GenParams.REPETITION_PENALTY: 1.2,
                        GenParams.TEMPERATURE: 0.7,
                        GenParams.TOP_K: 50,
                        GenParams.TOP_P: 0.9,
                    }
                )
                await turn_context.send_activity(f"Model updated to: {self.current_model.value}")
            else:
                await turn_context.send_activity("Invalid model selection. Please try again.")

        elif turn_context.activity.value.get("action") == "selectFile":
            selected_file = turn_context.activity.value.get("path")
            success, message = await self.download_and_process_sharepoint_pdf(selected_file)
            await turn_context.send_activity(message)

    async def download_and_process_sharepoint_pdf(self, filename):
        try:
            # Get SharePoint access token
            app = ConfidentialClientApplication(
                SHAREPOINT_CLIENT_ID,
                authority=f'https://login.microsoftonline.com/{SHAREPOINT_TENANT_ID}',
                client_credential=SHAREPOINT_CLIENT_SECRET
            )
            result = app.acquire_token_for_client(scopes=['https://graph.microsoft.com/.default'])
            access_token = result.get('access_token')
            
            if not access_token:
                return False, "Failed to authenticate with SharePoint."

            # Parse the SharePoint site URL to get the host and site path
            parsed_url = urlparse(SHAREPOINT_SITE_URL)
            host = parsed_url.netloc
            site_path = parsed_url.path.strip('/').split('/')[-1]

            # Get site ID
            headers = {"Authorization": f"Bearer {access_token}"}
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
            
            # Search for the file
            search_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{filename}:/content"
            file_response = requests.get(search_url, headers=headers, allow_redirects=False)
            
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
                self.current_pdf = filename
                return True, f"Document '{filename}' is now ready for questions. Use /askdoc to ask questions."
            except Exception as e:
                return False, f"Error processing PDF: {str(e)}"
            finally:
                os.unlink(temp_file_path)

        except Exception as e:
            return False, f"An unexpected error occurred: {str(e)}"

    async def get_sharepoint_files(self):
        try:
            app = ConfidentialClientApplication(
                SHAREPOINT_CLIENT_ID,
                authority=f'https://login.microsoftonline.com/{SHAREPOINT_TENANT_ID}',
                client_credential=SHAREPOINT_CLIENT_SECRET
            )
            result = app.acquire_token_for_client(scopes=['https://graph.microsoft.com/.default'])
            access_token = result.get('access_token')

            if not access_token:
                return None, "Access token not found. Check the token acquisition process."
            
            parsed_url = urlparse(SHAREPOINT_SITE_URL)
            host = parsed_url.netloc
            site_path = parsed_url.path.strip('/').split('/')[-1]

            graph_endpoint = f"https://graph.microsoft.com/v1.0/sites/{host}:/sites/{site_path}"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }

            async def get_files_recursive(session, folder_endpoint, current_path=""):
                    # Initialize folder structure with separate sections for files and subfolders
                    folder_content = {"folders": [], "files": []}
                    async with session.get(folder_endpoint, headers=headers) as response:
                        if response.status == 200:
                            folder_data = await response.json()
                            for item in folder_data.get('value', []):
                                item_name = item['name']
                                item_path = f"{current_path}/{item_name}" if current_path else item_name

                                # Check if item is a PDF file
                                if item.get('file') and item_name.lower().endswith('.pdf'):
                                    folder_content["files"].append({"name": item_name, "path": item_path})
                                # If it's a folder, recursively fetch its contents
                                elif item.get('folder'):
                                    subfolder_endpoint = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item['id']}/children"
                                    subfolder_content = await get_files_recursive(session, subfolder_endpoint, item_path)
                                    folder_content["folders"].append({"name": item_name, "content": subfolder_content})

                            # Handle pagination
                            next_link = folder_data.get('@odata.nextLink')
                            while next_link:
                                async with session.get(next_link, headers=headers) as next_response:
                                    if next_response.status == 200:
                                        next_data = await next_response.json()
                                        for item in next_data.get('value', []):
                                            item_name = item['name']
                                            item_path = f"{current_path}/{item_name}" if current_path else item_name

                                            # Process PDF files
                                            if item.get('file') and item_name.lower().endswith('.pdf'):
                                                folder_content["files"].append({"name": item_name, "path": item_path})
                                            # Process folders recursively
                                            elif item.get('folder'):
                                                subfolder_endpoint = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item['id']}/children"
                                                subfolder_content = await get_files_recursive(session, subfolder_endpoint, item_path)
                                                folder_content["folders"].append({"name": item_name, "content": subfolder_content})

                                        next_link = next_data.get('@odata.nextLink')
                                    else:
                                        break
                    return folder_content

            async with aiohttp.ClientSession() as session:
                async with session.get(graph_endpoint, headers=headers) as response:
                    if response.status == 200:
                        site_data = await response.json()
                        site_id = site_data['id']

                        # Retrieve the document library drives
                        drives_endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
                        async with session.get(drives_endpoint, headers=headers) as drives_response:
                            if drives_response.status == 200:
                                drives_data = await drives_response.json()
                                # Select the appropriate drive
                                drive = next((d for d in drives_data['value'] if d['name'] == SHAREPOINT_DOCUMENT_LIBRARY), None)
                                if not drive:
                                    return None, f"Document library '{SHAREPOINT_DOCUMENT_LIBRARY}' not found"

                                global drive_id
                                drive_id = drive['id']

                                # Start recursive file retrieval from the root of the drive
                                root_folder_endpoint = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
                                folder_structure = await get_files_recursive(session, root_folder_endpoint)

                                return folder_structure, None
                            else:
                                error_text = await drives_response.text()
                                return None, f"Error accessing SharePoint drives: {drives_response.status} - {error_text}"
                    else:
                        error_text = await response.text()
                        return None, f"Error accessing SharePoint site: {response.status} - {error_text}"
        except Exception as e:
            return None, f"Error during SharePoint file retrieval: {str(e)}"

    async def handle_file_upload(self, turn_context: TurnContext):
        for attachment in turn_context.activity.attachments:
            if attachment.content_type == "application/vnd.microsoft.teams.file.download.info":
                file_download_info = attachment.content
                file_url = file_download_info.get('downloadUrl')
                
                if file_url and attachment.name.lower().endswith('.pdf'):
                    file_content = await self.download_file(file_url)
                    if file_content:
                        pdf_dir = os.path.join(os.getcwd(), 'pdfs')
                        os.makedirs(pdf_dir, exist_ok=True)
                        
                        file_path = os.path.join(pdf_dir, attachment.name)
                        with open(file_path, 'wb') as pdf_file:
                            pdf_file.write(file_content)
                        
                        try:
                            setup_vector_store(file_path)
                            self.current_pdf = attachment.name
                            await turn_context.send_activity(f"PDF {attachment.name} has been processed and is ready for queries.")
                        except Exception as e:
                            logging.error(f"Error processing PDF: {str(e)}")
                            await turn_context.send_activity(f"Error processing PDF: {str(e)}")
                    else:
                        await turn_context.send_activity("Failed to download the PDF file.")
                else:
                    await turn_context.send_activity(f"Unsupported file type: {attachment.name}. Please upload a PDF file.")
            else:
                logging.warning(f"Unsupported attachment type: {attachment.content_type}")
        
        if not any(att.content_type == "application/vnd.microsoft.teams.file.download.info" for att in turn_context.activity.attachments):
            await turn_context.send_activity("Please upload a valid PDF file.")

    async def download_file(self, file_url: str) -> bytes:
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    return await response.read()
        return None
    
def generate_folder_card(folder_structure, is_root=True, parent_path=""):
    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.3",
        "body": [
            {
                "type": "TextBlock",
                "text": "SharePoint Documents",
                "weight": "Bolder",
                "size": "Medium"
            }
        ]
    }

    def add_folder_content(content, indent=0, current_path=""):
        items = []
        for folder in content["folders"]:
            folder_path = f"{current_path}/{folder['name']}" if current_path else folder['name']
            folder_id = f"folder_{folder_path.replace('/', '_')}"
            items.append({
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": f"{indent * 20}px",
                        "items": []
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "📁",
                                "size": "Small"
                            }
                        ]
                    },
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": folder['name'],
                                "wrap": True
                            }
                        ],
                        "selectAction": {
                            "type": "Action.ToggleVisibility",
                            "targetElements": [folder_id]
                        }
                    }
                ]
            })
            sub_items = add_folder_content(folder["content"], indent + 1, folder_path)
            items.append({
                "type": "Container",
                "id": folder_id,
                "items": sub_items,
                "isVisible": False
            })
        for file in content["files"]:
            file_path = f"{current_path}/{file['name']}" if current_path else file['name']
            items.append({
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": f"{indent * 20}px",
                        "items": []
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "📄",
                                "size": "Small"
                            }
                        ]
                    },
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": file['name'],
                                "wrap": True,
                                "color": "Accent"
                            }
                        ]
                    }
                ],
                "selectAction": {
                    "type": "Action.Submit",
                    "title": file['name'],
                    "data": {"action": "selectFile", "path": file_path}
                }
            })
        return items

    card["body"].extend(add_folder_content(folder_structure))
    
    return card

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