import logging
import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from fefe.Secrets import secrets
from fefe.Message import FefeMessage

spec = {
    "type": "function",
    "function": {
        "name": "calendar_events",
        "description": "Fetch next 10 events from Google Calendar.",
        "parameters": {
            "type": "object",
            "properties": {
                "timeMax": {
                    "type": "string",
                    "description": "Optional parameter. Must be an RFC3339 timestamp with mandatory time zone offset, for example, 2011-06-03T10:00:00-07:00, 2011-06-03T10:00:00Z. If timeMax is set, timeMin must be smaller than timeMax. If not set, will return the next 10 events from the current time."
                },
                "timeMin": {
                    "type": "string",
                    "description": "Optional parameter. Must be an RFC3339 timestamp with mandatory time zone offset, for example, 2011-06-03T10:00:00-07:00, 2011-06-03T10:00:00Z. If timeMax is set, timeMin must be smaller than timeMax. Defaults to the current time."
                }
            }
        }
    }
}

class GoogleService:
    def __init__(self):
        self.oauth_client_secret = secrets.google_oauth_client_secret # Json file 

class GoogleCalendar(GoogleService):
    def __init__(self, message: FefeMessage):
        super().__init__()
        self.SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        self.message = message
        self.credentials_path = os.path.join(message.user_dir, '.token.json')
        self.credentials = None
        if os.path.exists(self.credentials_path):
            self.credentials = Credentials.from_authorized_user_file(self.credentials_path, self.SCOPES)
    
    async def authenticate(self):
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.oauth_client_secret,self.SCOPES)
                self.credentials = flow.run_local_server(port=8085, prompt='consent', access_type='offline')

                import time 
                time.sleep(4)  # Wait for user to authorize
                # Sleep for 5 minutes, checking for user input
                sleep_time = 300
                start_time = time.time()
                while time.time() - start_time < sleep_time:
                    if self.credentials and self.credentials.valid:
                        break
                    time.sleep(3)
                # Check chat history to see if the user has entered the authorization code
                #chat_history = await self.message

                # Save the credentials for the next run
                with open(self.credentials_path, 'w') as token:
                    token.write(self.credentials.to_json())
        
    def get_service(self):
        service = build('calendar', 'v3', credentials=self.credentials)
        return service
    def get_events(self, tool_call_id, timeMin = None, timeMax=None, max_results=10):
        tool_call_response = {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": []
                }
        # Fetch calendars
        calendar_list_result = self.get_service().calendarList().list().execute()
        calendars = calendar_list_result.get('items', [])
        print(f"Calendars found: {calendars}")
        if timeMin is None:
            now = datetime.datetime.now().astimezone(datetime.timezone.utc).isoformat().replace('+00:00','Z') # Ensure we have the correct timezone
        all_events = []
        for calendar in calendars:
            print(f"Calendar ID: {calendar['id']}, Summary: {calendar['summary']}")
            page_token = None 
            events = 0

            while True:
                calendar_events = self.get_service().events().list(
                        calendarId=calendar['id'],
                        timeMin=now,
                        maxResults=max_results,
                        singleEvents=True,
                        pageToken=page_token,
                        orderBy='startTime'
                    ).execute()
                for event in calendar_events.get('items',[]):
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    end = event['end'].get('dateTime', event['end'].get('date'))
                    summary = event.get('summary', 'No Title')
                    description = event.get('description', 'No Description')
                    attendees = event.get('attendees', [])
                    attendees = [f"{attendee['displayName']} ({attendee['responseStatus']})" for attendee in attendees]
                    location = event.get('location', 'No Location')
                    status = event.get('status', 'No Status')
                    output_text = f"""
Event: {summary}
Description: {description}
Start: {start}
End: {end}
Attendees: {', '.join(attendees) if attendees else 'No Attendees'}
Location: {location}
Status: {status}
"""
                    all_events.append(output_text)
                page_token = calendar_events.get('nextPageToken')
                events += len(calendar_events.get('items', []))
                if not page_token:
                    break
                if timeMax is None:
                    if events >= max_results:
                        break
        for event in all_events:
            tool_call_response['content'].append({
                "type": "text",
                "text": event
            })
            print(event)
        return [tool_call_response]