import os
import tempfile
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
import time
import requests

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
    Please provide the most accurate response based on the question
    <context>
    {context}
    </context>
    Question: {input}
    """
)

# Global variables
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
default_vectors = None
temp_vectors = None
temp_file_id = None
pdf_processed = False


def setup_default_vector_store():
    global default_vectors
    default_file_path = "./default_document.pdf"
    
    if not os.path.exists(default_file_path) or os.path.getsize(default_file_path) == 0:
        print(f"Warning: Default document '{default_file_path}' does not exist or is empty.")
        print("Creating an empty vector store. Please upload a PDF to use the Q&A functionality.")
        default_vectors = FAISS.from_texts(["Empty document"], embeddings)
    else:
        try:
            loader = PyPDFLoader(default_file_path)
            docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            final_documents = text_splitter.split_documents(docs)
            default_vectors = FAISS.from_documents(final_documents, embeddings)
            print(f"Default vector store created with {len(final_documents)} documents.")
        except Exception as e:
            print(f"Error processing default document: {str(e)}")
            print("Creating an empty vector store. Please upload a PDF to use the Q&A functionality.")
            default_vectors = FAISS.from_texts(["Empty document"], embeddings)

setup_default_vector_store()

def process_pdf(file_path):
    global temp_vectors, pdf_processed
    try:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        final_documents = text_splitter.split_documents(docs)
        temp_vectors = FAISS.from_documents(final_documents, embeddings)
        pdf_processed = True
        print(f"Temporary vector store created with {len(final_documents)} documents.")
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        temp_vectors = None
        pdf_processed = False

def get_answer(question):
    global pdf_processed
    print(f"PDF processed: {pdf_processed}")
    if pdf_processed and temp_vectors is not None:
        vectors = temp_vectors
        print("Using temporary vector store for uploaded PDF")
    elif default_vectors is not None:
        vectors = default_vectors
        print("Using default vector store")
    else:
        return "No document has been processed yet. Please upload a PDF file first."
    
    try:
        document_chain = create_stuff_documents_chain(llm, prompt)
        retriever = vectors.as_retriever()
        retrieval_chain = create_retrieval_chain(retriever, document_chain)
        
        start = time.process_time()
        response = retrieval_chain.invoke({'input': question})
        print("Response time:", time.process_time() - start)
        
        return response['answer']
    except Exception as e:
        print(f"Error in get_answer: {str(e)}")
        return f"An error occurred while processing your question: {str(e)}"

@app.event("app_mention")
def handle_mention(event, say):
    question = event["text"].split(">")[1].strip()
    answer = get_answer(question)
    say(answer)

@app.command("/askdoc")
def handle_command(ack, respond, command):
    ack()
    question = command["text"]
    answer = get_answer(question)
    respond(answer)

@app.event("file_shared")
def handle_file_shared(event, say):
    global temp_file_id, temp_vectors, pdf_processed
    file_id = event["file_id"]
    try:
        file_info = app.client.files_info(file=file_id)
        
        if file_info["file"]["mimetype"] == "application/pdf":
            temp_file_id = file_id
            file_url = file_info["file"]["url_private_download"]
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                response = requests.get(file_url, headers={"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"})
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            process_pdf(temp_file_path)
            os.unlink(temp_file_path)
            
            if pdf_processed:
                say("PDF processed successfully. You can now ask questions about this document using /askdoc or by mentioning me.")
            else:
                say("Error processing PDF. Please try uploading again.")
        else:
            say("Please upload a PDF file. Other file types are not supported.")
    except Exception as e:
        say(f"Error handling file: {str(e)}")
        print(f"Error in handle_file_shared: {str(e)}")

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()