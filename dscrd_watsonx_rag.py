import os
import time
import discord
from discord.ext import commands
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
import requests

# Load environment variables
load_dotenv()

# Load IBM Watsonx credentials
watsonx_api_key = os.getenv("IBM_WATSON_API_KEY")
watsonx_url = os.getenv("IBM_WATSON_URL")
project_id = os.getenv("IBM_WATSON_PROJECT_ID")

# Configure Discord bot
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

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

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command(name="askdoc")
async def handle_command(ctx, *, question: str):
    answer = get_answer(question)
    await ctx.send(answer)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.attachments and message.attachments[0].filename.endswith('.pdf'):
        attachment = message.attachments[0]
        file_url = attachment.url
        file_name = attachment.filename
        
        # Download the PDF file
        try:
            response = requests.get(file_url)
            if response.status_code == 200:
                file_path = os.path.join("pdfs", file_name)
                with open(file_path, "wb") as f:
                    f.write(response.content)
                # Process the PDF to create a vector store
                setup_vector_store(file_path)
                await message.channel.send(f"PDF {file_name} has been processed and is ready for queries.")
            else:
                await message.channel.send("Failed to download the file.")
        except Exception as e:
            await message.channel.send(f"An error occurred: {e}")

    elif isinstance(message.channel, discord.DMChannel):
        if docsearch is None:
            await message.channel.send("No document has been processed yet. Please upload a PDF file first.")
        else:
            user_question = message.content
            answer = get_answer(user_question)
            await message.channel.send(answer)

    await bot.process_commands(message)


@bot.command(name="process_pdf")
async def process_pdf(ctx, file_url: str):
    try:
        response = requests.get(file_url)
        if response.status_code == 200:
            file_name = file_url.split("/")[-1]
            file_path = os.path.join("pdfs", file_name)
            with open(file_path, "wb") as f:
                f.write(response.content)
            setup_vector_store(file_path)
            await ctx.send(f"PDF {file_name} has been processed and is ready for queries.")
        else:
            await ctx.send("Failed to download the file.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Run the bot
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
