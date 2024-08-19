import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from slack_sdk import WebClient
from ibm_watson_machine_learning.foundation_models import Model
from ibm_watson_machine_learning.metanames import GenTextParamsMetaNames as GenParams

# Load environment variables
load_dotenv()

# Configure Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

# Configure Watsonx
api_key = os.getenv("IBM_WATSON_API_KEY")
api_url = os.getenv("IBM_WATSON_URL")
project_id = os.getenv("IBM_WATSON_PROJECT_ID")
model_id = "mistralai/mixtral-8x7b-instruct-v01"

credentials = {
    "url": api_url,
    "apikey": api_key
}

params = {
    GenParams.DECODING_METHOD: "greedy",
    GenParams.MAX_NEW_TOKENS: 1000
}

model = Model(
    model_id=model_id,
    params=params,
    credentials=credentials,
    project_id=project_id
)

# Store the timestamps of all messages sent by the bot
message_timestamps = []

def get_watsonx_response(question):
    try:
        # Generate the prompt
        input_prompt = f"""<s>[INST] You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature.
If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.

Question:
{question}
[/INST]
"""
        # Generate response
        response_generator = model.generate_text_stream(prompt=input_prompt)
        # Extract the response text from the generator
        response_text = ''.join(response_generator)
        return response_text
    except Exception as e:
        print(f"Error generating response: {e}")
        return "Sorry, I couldn't process your request."

@app.event("app_mention")
def handle_mention(event, say):
    global message_timestamps
    user_question = event['text'].split('>')[1].strip()
    response = get_watsonx_response(user_question)
    last_message = say(response)
    message_timestamps.append(last_message['ts'])

@app.event("message")
def handle_message(event, say):
    global message_timestamps
    if event.get("channel_type") == "im":
        user_question = event['text']
        response = get_watsonx_response(user_question)
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
