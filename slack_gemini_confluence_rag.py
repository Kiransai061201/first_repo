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
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from atlassian import Confluence
import json
import io
import PyPDF2

load_dotenv()

# Load API keys and configuration
groq_api_key = os.getenv('GROQ_API_KEY')
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
CONFLUENCE_EMAIL = os.getenv("CONFLUENCE_EMAIL")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
CONFLUENCE_BASE_URL = os.getenv("CONFLUENCE_BASE_URL")
CONFLUENCE_SPACE_KEY = os.getenv("CONFLUENCE_SPACE_KEY")

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
current_page = None
global current_document
current_document = None

confluence = Confluence(
    url=CONFLUENCE_BASE_URL,
    username=CONFLUENCE_EMAIL,
    password=CONFLUENCE_API_TOKEN,
    cloud=True
)

def setup_vector_store(content):
    global vectors
    
    # Process the content
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.create_documents([content])
    if not docs:
        raise ValueError("No content could be extracted from the Confluence page.")
    
    # Create FAISS vector store
    vectors = FAISS.from_documents(docs, embeddings)

def get_answer(question):
    if vectors is None:
        return "No document has been processed yet. Please select a Confluence page first."
    
    document_chain = create_stuff_documents_chain(llm, prompt)
    retriever = vectors.as_retriever()
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    
    start = time.process_time()
    response = retrieval_chain.invoke({'input': question})
    print("Response time:", time.process_time() - start)
    
    return response['answer']

def get_confluence_pdfs():
    try:
        print(f"Attempting to access Confluence space: {CONFLUENCE_SPACE_KEY}")
        space_info = confluence.get_space(CONFLUENCE_SPACE_KEY)
        print(f"Successfully accessed space: {space_info['name']}")
        
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

def get_confluence_pages():
    try:
        print(f"Attempting to access Confluence space: {CONFLUENCE_SPACE_KEY}")
        print(f"Using Confluence URL: {CONFLUENCE_BASE_URL}")
        print(f"Using Confluence email: {CONFLUENCE_EMAIL}")
        
        # First, try to get space information to check permissions
        space_info = confluence.get_space(CONFLUENCE_SPACE_KEY)
        print(f"Successfully accessed space: {space_info['name']}")
        
        # If space access is successful, try to get pages
        pages = confluence.get_all_pages_from_space(CONFLUENCE_SPACE_KEY, start=0, limit=50)
        return [{"id": page["id"], "title": page["title"]} for page in pages], None
    except Exception as e:
        # Print the full error for debugging
        print(f"Full error: {str(e)}")
        
        # Check if it's a JSON parsing error
        try:
            error_content = json.loads(str(e))
            if 'message' in error_content:
                return None, f"Confluence API Error: {error_content['message']}"
        except json.JSONDecodeError:
            pass
        
        # If it's not a JSON error, return the original error message
        return None, f"Error during Confluence page retrieval: {str(e)}"

def test_confluence_connection():
    print("Testing Confluence connection...")
    try:
        space_info = confluence.get_space(CONFLUENCE_SPACE_KEY)
        print(f"Successfully connected to Confluence. Space name: {space_info['name']}")
        return True
    except Exception as e:
        print(f"Failed to connect to Confluence: {str(e)}")
        return False

def get_and_process_confluence_page(page_id):
    global current_page
    try:
        page = confluence.get_page_by_id(page_id, expand='body.storage')
        content = page['body']['storage']['value']
        
        # Process the content
        setup_vector_store(content)
        current_page = page['title']
        return True, f"Page '{page['title']}' is now ready for questions. Use /askdoc to ask questions."
    except Exception as e:
        return False, f"Error processing Confluence page: {str(e)}"

def get_confluence_attachments():
    try:
        print("Attempting to access Confluence page")
        
        # Use the specific page ID from the URL
        page_id = "851969"
        
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


def get_confluence_page_content():
    try:
        print(f"Attempting to access Confluence space: {CONFLUENCE_SPACE_KEY}")
        space_info = confluence.get_space(CONFLUENCE_SPACE_KEY)
        print(f"Successfully accessed space: {space_info['name']}")
        
        pages = confluence.get_all_pages_from_space(CONFLUENCE_SPACE_KEY, start=0, limit=10)
        page_contents = []
        
        for page in pages:
            content = confluence.get_page_by_id(page['id'], expand='body.storage')
            page_contents.append({
                "page_id": page['id'],
                "page_title": page['title'],
                "content": content['body']['storage']['value'][:500]  # First 500 characters
            })
        
        return page_contents, None
    except Exception as e:
        return None, f"Error during Confluence page content retrieval: {str(e)}"

def get_and_process_document(doc_name):
    global current_document, vectors
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

def extract_pdf_content(pdf_bytes):
    pdf_file = io.BytesIO(pdf_bytes)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

@app.command("/listpagecontent")
def handle_listpagecontent_command(ack, respond):
    ack()
    page_contents, error = get_confluence_page_content()
    if error:
        respond(f"Error: {error}")
    else:
        if page_contents:
            content_list = ""
            for page in page_contents:
                content_list += f"\nPage: {page['page_title']} (ID: {page['page_id']})\n"
                content_list += f"Preview: {page['content'][:200]}...\n"
            respond(f"Page contents in Confluence:\n{content_list}")
        else:
            respond("No page contents found in the specified Confluence space.")

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

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)

@app.command("/usedoc")
def handle_usedoc_command(ack, respond, command):
    ack()
    doc_name = command["text"].strip()
    success, message = get_and_process_document(doc_name)
    respond(message)


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

@app.command("/askdoc")
def handle_askdoc_command(ack, respond, command):
    ack()
    global current_document
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