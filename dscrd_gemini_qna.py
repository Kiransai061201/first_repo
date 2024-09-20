import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Discord bot
intents = discord.Intents.default()
intents.message_content = True
intents.guild_messages = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Configure Gemini
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-pro")
chat = model.start_chat(history=[])

def get_gemini_response(question):
    response = chat.send_message(question)
    return response.text

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    
    # Sync commands globally
    await bot.tree.sync()
    
    print("Slash commands synced!")

@bot.tree.command(name="gemini", description="Ask a question to Gemini AI")
@app_commands.describe(question="The question you want to ask Gemini")
async def gemini_command(interaction: discord.Interaction, question: str):
    print(f"Received /gemini command from {interaction.user.name}: {question}")
    await interaction.response.defer()
    response = get_gemini_response(question)
    await interaction.followup.send(f"Question: {question}\n\nAnswer: {response}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Handle Direct Messages to the bot
    if isinstance(message.channel, discord.DMChannel):
        response = get_gemini_response(message.content)
        await message.channel.send(response)
    
    # Handle mentions in servers
    elif bot.user.mentioned_in(message):
        # Remove the bot mention from the message
        question = message.content.replace(f'<@!{bot.user.id}>', '').replace(f'<@{bot.user.id}>', '').strip()
        if question:
            response = get_gemini_response(question)
            await message.channel.send(f"{message.author.mention} Here's the response to your question:\n\n{response}")
        else:
            await message.channel.send(f"{message.author.mention} Please provide a question after mentioning me.")

    await bot.process_commands(message)

# Run the bot
bot.run(os.environ["DISCORD_BOT_TOKEN"])