import os.path
from datetime import datetime
import time
import base64
import re
from bs4 import BeautifulSoup

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def gmail_authenticate():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def get_emails(service, query):
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    return messages

def clean_html_content(html):
    """
    Cleans and normalizes HTML content using BeautifulSoup and regex.
    
    Args:
        html (str): Raw HTML content.

    Returns:
        str: Cleaned and normalized plain text.
    """
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator="\n")  # Keep logical newlines

    # Normalize whitespace
    text = text.replace('\xa0', ' ')           # Non-breaking spaces → normal spaces
    text = re.sub(r'[ \t]+', ' ', text)        # Collapse tabs and multiple spaces
    text = re.sub(r'\n\s*\n+', '\n\n', text)   # Collapse multiple blank lines
    text = text.strip()                        # Trim leading/trailing whitespace

    return text

def extract_parts(parts):
    body = ""
    for part in parts:
        mime_type = part.get('mimeType')
        if part.get('parts'):
            extract_parts(part['parts'])
        elif mime_type in ['text/plain', 'text/html']:
            data = part['body'].get('data')
            if data:
                decoded = base64.urlsafe_b64decode(data.encode('UTF-8')).decode('utf-8')
                if mime_type == 'text/html':
                    soup = BeautifulSoup(decoded, 'html.parser')
                    decoded = soup.get_text()
                body += decoded + "\n"
    return body

def get_content(service, messages) -> str:
    emails_data = []

    for msg in messages:
        msg_id = msg['id']
        msg_detail = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

        payload = msg_detail.get('payload', {})
        headers = payload.get('headers', [])

        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')

        parts = payload.get('parts', [])
        body = ""

        if 'data' in payload.get('body', {}):
            # Handle non-multipart emails
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        else:
            body = extract_parts(parts)

        emails_data.append({
            'subject': subject,
            'from': sender,
            'body': clean_html_content(body.strip())
        })
    return emails_data

def create_podcast_content(service):

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    unix_todaystart = int(time.mktime(today_start.timetuple()))
    query = f'from:@axios.com after:{unix_todaystart}'
    print("Getting News After: " + str(today_start))
    emails = get_emails(service, query)

    daily_content = ""

    if emails:
        news = get_content(service, emails)
        count = 1
        with open("output.txt", "w", encoding="utf-8") as f:
            for content in news:
                f.write(f"NEWSLETTER {count}\n")
                f.write(content['body'])
                daily_content = daily_content + f"NEWSLETTER {count}\n" + content['body']
                count+=1
        return daily_content
    else:
        print("No morning news.")


# Test
if __name__ == "__main__":
    service = gmail_authenticate()
    newsletter_content = create_podcast_content(service)
    # print(newsletter_content)