import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Discord bot
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Configure Gemini
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-pro")
chat = model.start_chat(history=[])

# Store the message IDs of all messages sent by the bot
message_ids = []

def get_gemini_response(question):
    response = chat.send_message(question)
    return response.text

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    global message_ids

    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        user_question = message.content
        response = get_gemini_response(user_question)
        bot_message = await message.channel.send(response)
        message_ids.append(bot_message.id)
    else:
        if bot.user.mentioned_in(message):
            user_question = message.content.split(f'<@!{bot.user.id}>')[1].strip()
            response = get_gemini_response(user_question)
            bot_message = await message.channel.send(response)
            message_ids.append(bot_message.id)

@bot.command()
async def delete_all(ctx):
    global message_ids
    if message_ids:
        for msg_id in message_ids:
            try:
                await ctx.channel.delete_messages([msg_id])
            except discord.NotFound:
                continue
        message_ids = []
        await ctx.send("All bot messages have been deleted.")

# Run the bot
bot.run(os.environ["DISCORD_BOT_TOKEN"])
