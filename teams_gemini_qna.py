import os
import asyncio
import logging
from dotenv import load_dotenv
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity
import google.generativeai as genai
from quart import Quart, request, Response
from botbuilder.core.integration import aiohttp_error_middleware

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Configure Gemini
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel("gemini-pro")
    chat = model.start_chat(history=[])
    logging.info("Gemini configured successfully")
except Exception as e:
    logging.error(f"Error configuring Gemini: {str(e)}")
    raise

# Simple in-memory storage for message tracking
message_store = {}

# Create Quart app
app = Quart(__name__)

# Create adapter
SETTINGS = BotFrameworkAdapterSettings(
    app_id=os.environ.get("MicrosoftAppId"),
    app_password=os.environ.get("MicrosoftAppPassword")
)
ADAPTER = BotFrameworkAdapter(SETTINGS)

class TeamsBot:
    async def on_turn(self, turn_context: TurnContext):
        if turn_context.activity.type == "message":
            logging.info(f"Received message: {turn_context.activity.text}")
            if turn_context.activity.text.lower() == "/delete_all":
                await self.delete_all_messages(turn_context)
                await turn_context.send_activity("All bot messages have been deleted.")
            else:
                try:
                    response = await self.get_gemini_response(turn_context.activity.text)
                    if response and response.strip():
                        await turn_context.send_activity(response)
                        self.store_message(turn_context, response)
                    else:
                        await turn_context.send_activity("I'm sorry, I couldn't generate a response. Please try again.")
                except Exception as e:
                    logging.error(f"Error in on_turn: {str(e)}")
                    await turn_context.send_activity("I encountered an error while processing your request. Please try again later.")

    async def get_gemini_response(self, question):
        logging.info(f"Generating response for: {question}")
        try:
            response = chat.send_message(question)
            logging.info(f"Gemini response: {response.text}")
            return response.text
        except Exception as e:
            logging.error(f"Error getting Gemini response: {str(e)}")
            return "Sorry, I encountered an error while processing your request."

    def store_message(self, turn_context: TurnContext, response: str):
        channel_id = turn_context.activity.channel_id
        if channel_id not in message_store:
            message_store[channel_id] = []
        message_store[channel_id].append({
            "message": response,
            "timestamp": turn_context.activity.timestamp.isoformat()
        })
        logging.info(f"Stored message for channel {channel_id}")

    async def delete_all_messages(self, turn_context: TurnContext):
        channel_id = turn_context.activity.channel_id
        if channel_id in message_store:
            del message_store[channel_id]
            logging.info(f"Deleted all messages for channel {channel_id}")

BOT = TeamsBot()

@app.route("/api/messages", methods=["POST"])
async def messages():
    logging.info("Received a message")
    if "application/json" in request.headers["Content-Type"]:
        body = await request.get_json()
    else:
        return Response(status=415)

    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    try:
        response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
        if response:
            return Response(status=response.status, headers=response.headers)
        return Response(status=201)
    except Exception as exception:
        logging.error(f"Error processing activity: {str(exception)}")
        return Response(status=500)

if __name__ == "__main__":
    app.run(debug=True, port=3978)