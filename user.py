import requests

access_token = 'rSM2JZbnn4Jid6VQDRwWddfeCo1JxG'

headers = {
    'Authorization': f'Bearer {access_token}'
}

response = requests.get('https://discord.com/api/v10/users/@me', headers=headers)
user_data = response.json()

print(user_data)
