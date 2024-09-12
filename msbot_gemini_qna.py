import os
import asyncio
from dotenv import load_dotenv
from botbuilder.core import BotFrameworkAdapterSettings, TurnContext, BotFrameworkAdapter
from botbuilder.schema import Activity
import google.generativeai as genai
from quart import Quart, request, Response

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-pro")
chat = model.start_chat(history=[])

# Simple in-memory storage for message tracking
message_store = {}

# Create Quart app
app = Quart(__name__)

# Create adapter
SETTINGS = BotFrameworkAdapterSettings(os.environ.get("MicrosoftAppId", ""), os.environ.get("MicrosoftAppPassword", ""))
ADAPTER = BotFrameworkAdapter(SETTINGS)

class TeamsBot:
    async def on_turn(self, turn_context: TurnContext):
        if turn_context.activity.type == "message":
            if turn_context.activity.text.lower() == "/delete_all":
                await self.delete_all_messages(turn_context)
                await turn_context.send_activity("All bot messages have been deleted.")
            else:
                response = await self.get_gemini_response(turn_context.activity.text)
                await turn_context.send_activity(response)
                self.store_message(turn_context, response)

    async def get_gemini_response(self, question):
        response = chat.send_message(question)
        return response.text

    def store_message(self, turn_context: TurnContext, response: str):
        channel_id = turn_context.activity.channel_id
        if channel_id not in message_store:
            message_store[channel_id] = []
        message_store[channel_id].append({
            "message": response,
            "timestamp": turn_context.activity.timestamp.isoformat()
        })

    async def delete_all_messages(self, turn_context: TurnContext):
        channel_id = turn_context.activity.channel_id
        if channel_id in message_store:
            del message_store[channel_id]

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