import requests
from flask import Flask, request, redirect

app = Flask(__name__)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        print("No code in the request.")
        return "No code found", 400
    
    print(f"Authorization code received: {code}")
    
    token_url = "https://discord.com/api/oauth2/token"
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': 'http://localhost:5000/callback',
        'client_id': '1278332179092340840',
        'client_secret': 'XYCZ4K1m9pPmfseFLA9f02Cvcq8jdqcN'
    }

    response = requests.post(token_url, data=data)
    token_data = response.json()
    
    if 'access_token' in token_data:
        access_token = token_data['access_token']
        print(f"Access Token: {access_token}")
        return f"Access Token: {access_token}"
    else:
        print(f"Error obtaining access token: {token_data}")
        return f"Error obtaining access token: {token_data}", 400

if __name__ == '__main__':
    app.run(port=5000)
