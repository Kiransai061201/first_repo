import discord
import os
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
discord_token = os.getenv('DISCORD_BOT_TOKEN')

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
    
    response = retrieval_chain.invoke({'input': question})
    return response['answer']

class MyDiscordBot(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content.startswith('/askdoc'):
            question = message.content[len('/askdoc '):].strip()
            answer = get_answer(question)
            await message.channel.send(answer)

    async def on_message_edit(self, before, after):
        await self.on_message(after)

    async def on_message_with_attachment(self, message):
        for attachment in message.attachments:
            if attachment.filename.endswith('.pdf'):
                file_path = os.path.join("pdfs", attachment.filename)
                await attachment.save(file_path)
                setup_vector_store(file_path)
                await message.channel.send(f"PDF {attachment.filename} has been processed and is ready for queries.")
            else:
                await message.channel.send("Please upload a valid PDF file.")

intents = discord.Intents.default()
intents.message_content = True

client = MyDiscordBot(intents=intents)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('/askdoc'):
        question = message.content[len('/askdoc '):].strip()
        answer = get_answer(question)
        await message.channel.send(answer)

    if message.attachments:
        await client.on_message_with_attachment(message)

if __name__ == "__main__":
    client.run(discord_token)
