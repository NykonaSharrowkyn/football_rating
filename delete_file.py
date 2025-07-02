from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import sys

if __name__ == '__main__':
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    filename = sys.argv[1]

    credentials = Credentials.from_service_account_file(
        'eternal-delight-433008-q1-1bb6245a61a9.json',
        scopes=SCOPES
    )
    drive_service = build('drive', 'v3', credentials=credentials)

    query = f"name contains '{filename}' and mimeType='application/vnd.google-apps.spreadsheet'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = results['files']
    for file in files:        
        drive_service.files().delete(fileId=file['id']).execute()