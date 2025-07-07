from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from dotenv import load_dotenv

import os
import json
import sys

load_dotenv()

if __name__ == '__main__':
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    filename = sys.argv[1]
    gcp_key = os.getenv("GCP_KEY")

    credentials = Credentials.from_service_account_info(
        json.loads(gcp_key),
        scopes=SCOPES
    )
    drive_service = build('drive', 'v3', credentials=credentials)

    query = f"name contains '{filename}' and mimeType='application/vnd.google-apps.spreadsheet'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = results['files']
    for file in files:        
        drive_service.files().delete(fileId=file['id']).execute()