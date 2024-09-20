import os
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Slack and JIRA credentials
slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
slack_app_token = os.getenv("SLACK_APP_TOKEN")
jira_url = os.getenv("JIRA_URL")
jira_email = os.getenv("JIRA_EMAIL")
jira_api_token = os.getenv("JIRA_API_TOKEN")
jira_project_key = os.getenv("JIRA_PROJECT_KEY")

# Initialize the Slack app
app = App(token=slack_bot_token)

# Store file IDs temporarily
file_ids = {}

# Function to create JIRA issue
def create_jira_issue(summary, description):
    url = f"{jira_url}/rest/api/3/issue"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    auth = (jira_email, jira_api_token)

    payload = {
        "fields": {
            "project": {
                "key": jira_project_key
            },
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": description
                            }
                        ]
                    }
                ]
            },
            "issuetype": {
                "name": "Task"
            }
        }
    }

    response = requests.post(url, json=payload, headers=headers, auth=auth)

    if response.status_code == 201:
        issue_key = response.json().get("key")
        return issue_key
    else:
        return f"Failed to create issue in JIRA: {response.status_code} - {response.text}"

def attach_file_to_issue(issue_key, file_id):
    url = f"{jira_url}/rest/api/3/issue/{issue_key}/attachments"
    headers = {
        "X-Atlassian-Token": "no-check"
    }
    auth = (jira_email, jira_api_token)

    # Get the public URL of the file
    file_info_url = f"https://slack.com/api/files.info?file={file_id}"
    response = requests.get(file_info_url, headers={"Authorization": f"Bearer {slack_bot_token}"})
    
    if response.status_code == 200:
        file_info = response.json()
        file_url = file_info.get('file', {}).get('url_private', '')
        
        if file_url:
            # Download the file from Slack
            file_response = requests.get(file_url, headers={"Authorization": f"Bearer {slack_bot_token}"}, stream=True)
            files = {'file': ('file', file_response.raw)}

            # Attach the file to the JIRA issue
            response = requests.post(url, headers=headers, auth=auth, files=files)

            if response.status_code == 200:
                print(f"File attached successfully: {response.json()}")
                return "File attached successfully."
            else:
                print(f"Failed to attach file: {response.status_code} - {response.text}")
                return f"Failed to attach file: {response.status_code} - {response.text}"
        else:
            return "File URL not found."
    else:
        return f"Failed to get file info: {response.status_code} - {response.text}"

# Command to create JIRA issue
@app.command("/gatherreq")
def handle_command(ack, respond, command):
    ack()
    user_input = command['text']

    parts = user_input.split(":")
    summary = parts[0].strip()
    description = parts[1].strip() if len(parts) > 1 else "No description provided."
    
    issue_key = create_jira_issue(summary, description)
    
    # Attach file if provided
    file_id = file_ids.get(command['user_id'])
    if file_id:
        result = attach_file_to_issue(issue_key, file_id)
        file_ids.pop(command['user_id'], None)
    else:
        result = f"Issue created successfully in JIRA: {issue_key}"

    respond(result)


# Function to get JIRA issues
def get_jira_issues(jql):
    url = f"{jira_url}/rest/api/3/search"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    auth = (jira_email, jira_api_token)
    params = {
        "jql": jql,
        "maxResults": 10
    }

    response = requests.get(url, headers=headers, auth=auth, params=params)

    if response.status_code == 200:
        issues = response.json().get('issues', [])
        return issues
    else:
        return f"Failed to retrieve issues: {response.status_code} - {response.text}"

@app.command("/listissues")
def handle_list_issues(ack, respond, command):
    ack()
    jql_query = command['text']  # Users can provide a JQL query after the command
    issues = get_jira_issues(jql_query)

    if isinstance(issues, str):  # Error message
        respond(issues)
    else:
        if not issues:
            respond("No issues found.")
        else:
            issue_list = []
            for issue in issues:
                issue_key = issue['key']
                summary = issue['fields']['summary']
                
                # Safely get the description
                description = "No description provided."
                if issue['fields'].get('description'):
                    desc = issue['fields']['description']
                    if isinstance(desc, dict) and 'content' in desc:
                        for content in desc['content']:
                            if content.get('type') == 'paragraph' and content.get('content'):
                                for text in content['content']:
                                    if text.get('type') == 'text':
                                        description = text.get('text', 'No description provided.')
                                        break
                                if description != "No description provided.":
                                    break
                
                status = issue['fields']['status']['name']
                issue_list.append(f"{issue_key} - {summary}\nDescription: {description}\nStatus: {status}\n")

            respond("\n".join(issue_list))

def add_comment_to_issue(issue_key, comment_body):
    url = f"{jira_url}/rest/api/3/issue/{issue_key}/comment"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    auth = (jira_email, jira_api_token)

    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": comment_body
                        }
                    ]
                }
            ]
        }
    }

    response = requests.post(url, json=payload, headers=headers, auth=auth)

    if response.status_code == 201:
        return f"Comment added successfully to issue {issue_key}."
    elif response.status_code == 404:
        return f"Issue {issue_key} does not exist or you do not have permission to access it."
    else:
        return f"Failed to add comment: {response.status_code} - {response.text}"



@app.command("/addcomment")
def handle_add_comment(ack, respond, command):
    ack()  # Acknowledge the command

    # Extract arguments from the command text
    args = command['text'].split(maxsplit=1)
    if len(args) != 2:
        respond("Please provide a comment in the format: `/addcomment ISSUE-KEY Comment text`")
        return
    
    issue_key = args[0].strip()
    comment_body = args[1].strip()
    
    # Call the function to add a comment
    result = add_comment_to_issue(issue_key, comment_body)
    
    respond(result)

def get_user_account_id(username):
    url = f"{jira_url}/rest/api/3/user/search"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    auth = (jira_email, jira_api_token)
    params = {
        "query": username
    }

    response = requests.get(url, headers=headers, auth=auth, params=params)

    if response.status_code == 200:
        users = response.json()
        if users:
            return users[0].get('accountId')
        else:
            return None
    else:
        return f"Failed to retrieve user details: {response.status_code} - {response.text}"




@app.command("/assignissue")
def handle_assign_issue_dm(ack, respond, command):
    ack()
    # Extract arguments from the command text
    args = command['text'].split(maxsplit=1)
    if len(args) != 2:
        respond("Usage: `/assignissue <issue_key> <assignee_username>`")
        return

    issue_key, assignee_username = args[0].strip(), args[1].strip()

    # Get accountId for the assignee
    account_id = get_user_account_id(assignee_username)
    if not account_id:
        respond(f"Failed to find user with username {assignee_username}.")
        return

    # JIRA API endpoint to assign an issue
    url = f"{jira_url}/rest/api/3/issue/{issue_key}/assignee"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    auth = (jira_email, jira_api_token)
    
    # Payload for the JIRA API request
    payload = {
        "accountId": account_id
    }
    
    # Make the API request to assign the issue
    response = requests.put(url, json=payload, headers=headers, auth=auth)
    
    if response.status_code == 204:
        respond(f"Issue {issue_key} has been successfully assigned to {assignee_username}.")
    else:
        respond(f"Failed to assign issue: {response.status_code} - {response.text}")


@app.command("/userinfo")
def handle_user_info(ack, respond, command):
    ack()
    # Extract user key or username from the command text
    user_key = command['text'].strip()
    
    # JIRA API endpoint to get user information
    url = f"{jira_url}/rest/api/3/user?accountId={user_key}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    auth = (jira_email, jira_api_token)
    
    # Make the API request to get user info
    response = requests.get(url, headers=headers, auth=auth)
    
    if response.status_code == 200:
        user_info = response.json()
        user_details = f"User: {user_info.get('displayName', 'N/A')}\n"
        
        # Check if email address is available
        if 'emailAddress' in user_info:
            user_details += f"Email: {user_info['emailAddress']}\n"
        else:
            user_details += "Email: Not available\n"
        
        # Add more user details if available
        user_details += f"Account ID: {user_info.get('accountId', 'N/A')}\n"
        user_details += f"Active: {'Yes' if user_info.get('active', False) else 'No'}\n"
        
        respond(user_details)
    else:
        respond(f"Failed to retrieve user information: {response.status_code} - {response.text}")


@app.command("/report")
def handle_generate_report(ack, respond, command):
    ack()
    # Extract report type from the command text
    report_type = command['text'].strip().lower()
    
    # JIRA API endpoint to get project or issue data based on report type
    if report_type == 'progress':
        url = f"{jira_url}/rest/api/3/search?jql=project={jira_project_key}"
    elif report_type == 'status':
        url = f"{jira_url}/rest/api/3/search?jql=project={jira_project_key} AND status in (Open, \"In Progress\", Closed)"
    elif report_type == 'performance':
        url = f"{jira_url}/rest/api/3/search?jql=project={jira_project_key} AND updated >= -1w"
    else:
        respond("Usage: `/report <progress|status|performance>`")
        return
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    auth = (jira_email, jira_api_token)
    
    # Make the API request to generate the report
    response = requests.get(url, headers=headers, auth=auth)
    
    if response.status_code == 200:
        report_data = response.json()
        # Simplified example of report data extraction
        report_summary = f"Report Type: {report_type.capitalize()}\nTotal Issues: {report_data['total']} issues found."
        respond(report_summary)
    else:
        respond(f"Failed to generate report: {response.status_code} - {response.text}")


def get_all_users():
    url = f"{jira_url}/rest/api/3/users/search"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    auth = (jira_email, jira_api_token)

    response = requests.get(url, headers=headers, auth=auth)

    if response.status_code == 200:
        users = response.json()
        return users
    else:
        return f"Failed to retrieve users: {response.status_code} - {response.text}"

@app.command("/listusers")
def handle_list_users(ack, respond):
    ack()
    users = get_all_users()

    if isinstance(users, str):  # Error message
        respond(users)
    else:
        if not users:
            respond("No users found.")
        else:
            # Keywords to filter out non-human accounts
            ignore_keywords = [
                'jira', 'service', 'widget', 'spreadsheets', 
                'atlas', 'cloud', 'bot', 'trello', 
                'slack', 'system', 'migrator', 'proforma'
            ]

            # Filter out non-human accounts and format the output
            human_users = []
            for user in users:
                user_name = user['displayName']
                user_key = user['accountId']
                
                # Check if the user is likely a human
                if all(keyword not in user_name.lower() for keyword in ignore_keywords):
                    human_users.append(f"Username: {user_name}\nUser ID: {user_key}\n")

            if human_users:
                respond("Human Users:\n\n" + "\n".join(human_users))
            else:
                respond("No human users found.")


@app.event("message")
def handle_message_events(body, logger, say):
    event = body.get('event', {})
    if event.get('type') == 'message' and event.get('subtype') == 'file_share':
        file_id = event.get('files', [{}])[0].get('id')
        user_id = event.get('user')
        if file_id:
            file_ids[user_id] = file_id

@app.message("create jira issue")
def message_create_jira_issue(message, say):
    say("Sure! Please provide the requirement in the format Summary: Description. You can also upload a file, and it will be attached to the issue.")

@app.message("list jira issues")
def message_list_jira_issues(message, say):
    say("Please provide a JQL query to list the issues, like /listissues project=TEST.")

@app.message("hello")
def message_hello(message, say):
    say("Hello! I can help you create and list JIRA issues. Type /listissues <JQL> to get a list of issues or /gatherreq Summary: Description to create a new issue.")

if __name__ == "__main__":
    handler = SocketModeHandler(app, slack_app_token)
    handler.start()




# /gatherreq Summary: Description
# /gatherreq "Fix login bug": "There is an issue with the login button not working on mobile.
# /listissues <JQL query>
# /addcomment <ISSUE-KEY> Comment text
# /addcomment ISSUE-123 "This issue needs urgent attention.
# /assignissue <issue_key> <assignee_username>
# /assignissue ISSUE-123 john.doe
# /userinfo <account_id>
# /report progress
# /listusers

