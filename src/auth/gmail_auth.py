import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

class GmailAuth:
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    TOKEN_FILE = os.path.join(BASE_DIR, 'token.pickle')
    CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')

    def __init__(self):
        self.creds = None
        self.service = None

    def authenticate(self):
        if os.path.exists(self.TOKEN_FILE):
            with open(self.TOKEN_FILE, 'rb') as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.CREDENTIALS_FILE):
                    print(f'Credentials file not found at: {self.CREDENTIALS_FILE}')
                    return False
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CREDENTIALS_FILE, self.SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open(self.TOKEN_FILE, 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('gmail', 'v1', credentials=self.creds)
        return True

    def get_service(self):
        return self.service

    def logout(self):
        """Clear credentials and remove token file"""
        if os.path.exists(self.TOKEN_FILE):
            os.remove(self.TOKEN_FILE)
        self.creds = None
        self.service = None
        return True