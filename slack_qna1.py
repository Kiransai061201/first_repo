import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import google.generativeai as genai
from slack_sdk import WebClient
import time
import random
from collections import defaultdict

# Load environment variables
load_dotenv()

# Configure Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

# Configure Gemini
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-pro")

# Store the timestamps and prompt details
message_timestamps = []
prompts_history = []

# Analytics data
total_characters_used = 0
total_cost = 0
COST_PER_1000_CHARS = 0.0001

# Prompt Management
session_history = defaultdict(list)

# A/B Testing
prompt_versions = {
    "A": "You are a helpful assistant. Respond in a friendly and concise manner.",
    "B": "You are an AI expert. Provide detailed and technical responses."
}

# Prompt Analytics
prompt_analytics = defaultdict(lambda: {"count": 0, "total_tokens": 0, "total_chars": 0})

def estimate_tokens(char_count):
    return char_count // 4

def structure_prompt(user_input, user_id):
    structured_prompt = f"User input: {user_input}\n\nPlease provide a helpful response."
    
    # Add context from session history if available
    if user_id in session_history:
        context = "\n".join([f"Human: {item['human']}\nAssistant: {item['assistant']}" 
                             for item in session_history[user_id][-3:]])  # Last 3 interactions
        structured_prompt = f"Previous context:\n{context}\n\n{structured_prompt}"
    
    # A/B testing: randomly choose prompt version
    prompt_version = random.choice(["A", "B"])
    structured_prompt = f"{prompt_versions[prompt_version]}\n\n{structured_prompt}"
    
    return structured_prompt, prompt_version

def get_gemini_response(question, user_id):
    global total_characters_used, total_cost
    
    structured_prompt, prompt_version = structure_prompt(question, user_id)
    
    start_time = time.time()
    
    # Convert session history to Gemini-compatible format
    gemini_history = [
        {"role": "user" if i % 2 == 0 else "model", "parts": [item["human"] if i % 2 == 0 else item["assistant"]]}
        for i, item in enumerate(session_history[user_id])
    ]
    
    chat = model.start_chat(history=gemini_history)
    response = chat.send_message(structured_prompt)
    end_time = time.time()
    response_text = response.text
    
    chars_used = len(structured_prompt) + len(response_text)
    total_characters_used += chars_used
    cost = (chars_used / 1000) * COST_PER_1000_CHARS
    total_cost += cost
    duration = end_time - start_time
    
    # Update prompt analytics
    prompt_analytics[prompt_version]["count"] += 1
    prompt_analytics[prompt_version]["total_tokens"] += estimate_tokens(chars_used)
    prompt_analytics[prompt_version]["total_chars"] += chars_used
    
    # Update session history
    session_history[user_id].append({"human": question, "assistant": response_text})
    
    return response_text, chars_used, cost, duration, prompt_version

@app.event("app_mention")
def handle_mention(event, say):
    user_id = event['user']
    user_question = event['text'].split('>')[1].strip()
    response_text, chars_used, cost, duration, prompt_version = get_gemini_response(user_question, user_id)
    last_message = say(response_text)
    message_timestamps.append(last_message['ts'])
    prompts_history.append({
        'prompt': user_question, 
        'response': response_text, 
        'characters': chars_used, 
        'cost': cost,
        'duration': duration,
        'prompt_version': prompt_version,
        'timestamp': time.time()
    })

@app.event("message")
def handle_message(event, say):
    if event.get("channel_type") == "im":
        user_id = event['user']
        user_question = event['text']
        response_text, chars_used, cost, duration, prompt_version = get_gemini_response(user_question, user_id)
        last_message = say(response_text)
        message_timestamps.append(last_message['ts'])
        prompts_history.append({
            'prompt': user_question, 
            'response': response_text, 
            'characters': chars_used, 
            'cost': cost,
            'duration': duration,
            'prompt_version': prompt_version,
            'timestamp': time.time()
        })

@app.command("/delete_all")
def delete_all_command(ack, body):
    global message_timestamps
    ack()
    if message_timestamps:
        for ts in message_timestamps:
            try:
                client.chat_delete(channel=body['channel_id'], ts=ts)
            except Exception as e:
                print(f"Error deleting message: {e}")
        message_timestamps = []
    client.chat_postMessage(channel=body['channel_id'], text="All bot messages have been deleted.")

@app.command("/stats")
def stats_command(ack, body):
    ack()
    total_prompts = len(prompts_history)
    avg_chars = total_characters_used / total_prompts if total_prompts > 0 else 0
    estimated_tokens = estimate_tokens(total_characters_used)
    response_text = (
        f"Total prompts: {total_prompts}\n"
        f"Total characters used: {total_characters_used}\n"
        f"Estimated total tokens: {estimated_tokens}\n"
        f"Average characters per prompt: {avg_chars:.2f}\n"
        f"Estimated total cost: ${total_cost:.4f}\n"
    )
    client.chat_postMessage(channel=body['channel_id'], text=response_text)

@app.command("/analytics")
def analytics_command(ack, body):
    ack()
    if not prompts_history:
        client.chat_postMessage(channel=body['channel_id'], text="No data available yet.")
        return

    most_expensive = max(prompts_history, key=lambda x: x['cost'])
    most_chars = max(prompts_history, key=lambda x: x['characters'])
    avg_response_time = sum(p['duration'] for p in prompts_history) / len(prompts_history)

    # A/B testing results
    ab_results = "A/B Testing Results:\n"
    for version, data in prompt_analytics.items():
        avg_tokens = data['total_tokens'] / data['count'] if data['count'] > 0 else 0
        ab_results += f"Version {version}: Count: {data['count']}, Avg Tokens: {avg_tokens:.2f}\n"

    response_text = (
        f"Analytics:\n"
        f"Most expensive prompt (${most_expensive['cost']:.4f}):\n{most_expensive['prompt']}\n\n"
        f"Prompt with most characters ({most_chars['characters']}):\n{most_chars['prompt']}\n\n"
        f"Average response time: {avg_response_time:.2f} seconds\n\n"
        f"{ab_results}"
    )
    client.chat_postMessage(channel=body['channel_id'], text=response_text)

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()