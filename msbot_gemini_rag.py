import asyncio
import time
from dotenv import load_dotenv
from botbuilder.core import BotFrameworkAdapterSettings, TurnContext, BotFrameworkAdapter
from botbuilder.schema import Activity, ActivityTypes
from quart import Quart, request, Response
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
import aiohttp
import aiofiles


# Load environment variables
load_dotenv()

# Configure API keys
groq_api_key = os.getenv('GROQ_API_KEY')
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Create Quart app
app = Quart(__name__)

# Create adapter
SETTINGS = BotFrameworkAdapterSettings(os.environ.get("MicrosoftAppId", ""), os.environ.get("MicrosoftAppPassword", ""))
ADAPTER = BotFrameworkAdapter(SETTINGS)

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


class TeamsBot:
    async def on_turn(self, turn_context: TurnContext):
        if turn_context.activity.type == ActivityTypes.message:
            if turn_context.activity.attachments and turn_context.activity.attachments[0].content_type == 'application/pdf':
                # Handle PDF upload
                attachment = turn_context.activity.attachments[0]
                file_url = attachment.content_url
                file_name = attachment.name or "uploaded.pdf"
                
                # Download the file
                async with aiohttp.ClientSession() as session:
                    async with session.get(file_url) as resp:
                        if resp.status == 200:
                            file_path = os.path.join("pdfs", file_name)
                            os.makedirs("pdfs", exist_ok=True)
                            async with aiofiles.open(file_path, mode='wb') as f:
                                await f.write(await resp.read())
                            
                            # Process the PDF
                            try:
                                setup_vector_store(file_path)
                                await turn_context.send_activity(f"PDF {file_name} has been processed and is ready for queries.")
                            except Exception as e:
                                await turn_context.send_activity(f"Error processing PDF: {str(e)}")
                        else:
                            await turn_context.send_activity("Failed to download the PDF file.")
            elif turn_context.activity.text:
                text = turn_context.activity.text.lower()
                if text.startswith("ask:"):
                    question = text.split("ask:")[1].strip()
                    answer = get_answer(question)
                    await turn_context.send_activity(answer)
                else:
                    await turn_context.send_activity("I can process PDFs and answer questions. Upload a PDF file or use 'ask: [question]' to ask a question.")
            else:
                await turn_context.send_activity("I didn't understand that. Please upload a PDF or ask a question using 'ask: [your question]'.")

BOT = TeamsBot()

@app.route("/api/messages", methods=["POST"])
async def messages():
    if "application/json" in request.headers["Content-Type"]:
        body = await request.get_json()
    else:
        return Response(status=415)

    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return Response(status=response.status, headers=response.headers)
    return Response(status=201)

if __name__ == "__main__":
    app.run(debug=True, port=3978)