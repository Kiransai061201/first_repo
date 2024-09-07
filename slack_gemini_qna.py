

import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import google.generativeai as genai
from slack_sdk import WebClient


# Load environment variables
load_dotenv()


# Configure Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])


# Configure Gemini
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-pro")
chat = model.start_chat(history=[])


# Store the timestamps of all messages sent by the bot
message_timestamps = []


def get_gemini_response(question):
    response = chat.send_message(question)
    return response.text


@app.event("app_mention")
def handle_mention(event, say):
    global message_timestamps
    user_question = event['text'].split('>')[1].strip()
    response = get_gemini_response(user_question)
    last_message = say(response)
    message_timestamps.append(last_message['ts'])


@app.event("message")
def handle_message(event, say):
    global message_timestamps
    if event.get("channel_type") == "im":
        user_question = event['text']
        response = get_gemini_response(user_question)
        last_message = say(response)
        message_timestamps.append(last_message['ts'])


@app.command("/delete_all")
def delete_all_command(ack, body):
    global message_timestamps
    ack()  # Acknowledge the command request
    if message_timestamps:
        for ts in message_timestamps:
            client.chat_delete(channel=body['channel_id'], ts=ts)
        message_timestamps = []


if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()

