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

# Global variable to store vector store
docsearch = None

def setup_vector_store(file_path):
    global docsearch

    # Load and process the uploaded PDF
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    if not docs:
        raise ValueError("No documents found in the PDF.")
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    final_documents = text_splitter.split_documents(docs)
    if not final_documents:
        raise ValueError("No text could be extracted from the PDF.")
    
    # Create Chroma vector store
    docsearch = Chroma.from_documents(final_documents, embeddings)

def get_answer(question):
    if docsearch is None:
        return "No document has been processed yet. Please upload a PDF file first."

    # Set up a RetrievalQA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=docsearch.as_retriever(),
        chain_type="stuff",  # Use "map_reduce" or "refine" for larger documents
    )

    start = time.process_time()
    try:
        # Run the chain with the question
        response = qa_chain({"query": question})
        print("Response time:", time.process_time() - start)
        return response.get('result', 'No output found')
    except Exception as e:
        print(f"Error during retrieval: {e}")
        return "An error occurred while retrieving the answer."

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
