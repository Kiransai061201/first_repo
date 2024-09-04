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

@app.command("/askdoc")
def handle_command(ack, respond, command):
    ack()
    question = command["text"]
    answer = get_answer(question)
    respond(answer)

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
                say(f"PDF {file_info['name']} has been processed and is ready for queries.")
            else:
                say("Failed to download the file.")
        else:
            say("Please upload a valid PDF file.")

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()

#