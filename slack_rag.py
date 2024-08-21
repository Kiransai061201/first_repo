import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import time

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

# Global variables to store vector store and other components
embeddings = None
vectors = None

def setup_vector_store():
    global embeddings, vectors
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    loader = PyPDFDirectoryLoader("pdfs")  # Data Ingestion
    docs = loader.load()  # Document Loading
    if not docs:
        print("No documents found in the ./us_census directory. Please check if the directory exists and contains PDF files.")
        return
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)  # Chunk Creation
    final_documents = text_splitter.split_documents(docs[:20])  # splitting
    if not final_documents:
        print("No text could be extracted from the documents. Please check the content of your PDF files.")
        return
    vectors = FAISS.from_documents(final_documents, embeddings)  # vector OpenAI embeddings
    print(f"Vector store created with {len(final_documents)} documents.")

# Set up vector store on startup
setup_vector_store()

def get_answer(question):
    document_chain = create_stuff_documents_chain(llm, prompt)
    retriever = vectors.as_retriever()
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    
    start = time.process_time()
    response = retrieval_chain.invoke({'input': question})
    print("Response time:", time.process_time() - start)
    
    return response['answer']

@app.event("app_mention")
def handle_mention(event, say):
    question = event["text"].split(">")[1].strip()
    answer = get_answer(question)
    say(answer)


@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)


@app.command("/askdoc")
def handle_command(ack, respond, command):
    ack()
    question = command["text"]
    answer = get_answer(question)
    respond(answer)

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()

    #