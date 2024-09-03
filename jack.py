import requests

# Replace this with your actual access token
access_token = 'rSM2JZbnn4Jid6VQDRwWddfeCo1JxG'

headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}

# Fetch user information
response = requests.get('https://discord.com/api/v10/users/@me', headers=headers)
user_data = response.json()

print("User Information:", user_data)
