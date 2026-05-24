# # eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiUEFUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzY5OTY1Mjc5LCJqdGkiOiI2MjI5NjJkZC02YjU0LTRiZWEtOTJmMi1hM2Q5ODQ2NzliYTIiLCJ1c2VyX3V1aWQiOiI1MzM3MzZmMy02N2U5LTQ0YmMtYjQxOS1iOWRkOWQzZjMxYzkifQ.fsyGCwbKBh54d5i8qPG3qVU0z7H1_Ul1Luf6MVwUNaiRNTSRyG7duPaSAbulF-V-1g-tMytHEMsvBXs_YuPXDg

# import requests
# from datetime import datetime, timedelta
# from dateutil import parser

# CALENDLY_TOKEN = "eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiUEFUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzY5OTY1Mjc5LCJqdGkiOiI2MjI5NjJkZC02YjU0LTRiZWEtOTJmMi1hM2Q5ODQ2NzliYTIiLCJ1c2VyX3V1aWQiOiI1MzM3MzZmMy02N2U5LTQ0YmMtYjQxOS1iOWRkOWQzZjMxYzkifQ.fsyGCwbKBh54d5i8qPG3qVU0z7H1_Ul1Luf6MVwUNaiRNTSRyG7duPaSAbulF-V-1g-tMytHEMsvBXs_YuPXDg"

# HEADERS = {
#     "Authorization": f"Bearer {CALENDLY_TOKEN}",
#     "Content-Type": "application/json"
# }

# def create_calendly_event(name: str, email: str, start_time: str, duration_minutes: int = 30, location: str = None):
#     """
#     Create a scheduled event on Calendly.
#     """
#     try:
#         # Convert start_time to ISO 8601 if string
#         if isinstance(start_time, str):
#             start_time_dt = parser.isoparse(start_time)
#         else:
#             start_time_dt = start_time

#         end_time_dt = start_time_dt + timedelta(minutes=duration_minutes)

#         payload = {
#             "invitees": [
#                 {
#                     "name": name,
#                     "email": email
#                 }
#             ],
#             "event_type": "One-on-One",  # or your Calendly event type
#             "start_time": start_time_dt.isoformat(),
#             "end_time": end_time_dt.isoformat(),
#             "location": location
#         }

#         url = "https://api.calendly.com/scheduled_events"

#         response = requests.post(url, json=payload, headers=HEADERS)

#         if response.status_code in [200, 201]:
#             return {
#                 "success": True,
#                 "message": f"Call scheduled successfully for {start_time_dt.strftime('%Y-%m-%d %H:%M')}",
#                 "data": response.json()
#             }
#         else:
#             return {
#                 "success": False,
#                 "message": f"Failed to schedule call: {response.text}"
#             }

#     except Exception as e:
#         return {"success": False, "message": str(e)}
    
# if __name__ == "__main__":
#         # Example usage
#     event = create_calendly_event(
#     name="Shivank Shekhar",
#     email="shivank@example.com",
#     start_time="2026-02-02T15:00:00+05:30",  # ISO 8601 format
#     duration_minutes=30
# )
#     if event["success"]:
#         print(event["message"])
#     else:
#         print(event["message"])



import os
import requests
from datetime import timedelta
from dateutil import parser

# ==============================
# CONFIG
# ==============================

CALENDLY_TOKEN ="eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiUEFUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzY5OTY1Mjc5LCJqdGkiOiI2MjI5NjJkZC02YjU0LTRiZWEtOTJmMi1hM2Q5ODQ2NzliYTIiLCJ1c2VyX3V1aWQiOiI1MzM3MzZmMy02N2U5LTQ0YmMtYjQxOS1iOWRkOWQzZjMxYzkifQ.fsyGCwbKBh54d5i8qPG3qVU0z7H1_Ul1Luf6MVwUNaiRNTSRyG7duPaSAbulF-V-1g-tMytHEMsvBXs_YuPXDg"
if not CALENDLY_TOKEN:
    raise Exception("CALENDLY_TOKEN environment variable not set")

HEADERS = {
    "Authorization": f"Bearer {CALENDLY_TOKEN}",
    "Content-Type": "application/json"
}

# ==============================
# STEP 1: CHECK AVAILABILITY
# ==============================

def is_time_available(event_type_uri: str, start_time: str, duration_minutes: int):

    start_dt = parser.isoparse(start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    url = "https://api.calendly.com/event_type_available_times"
    params = {
        "event_type": event_type_uri,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat()
    }

    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code != 200:
        return False, response.text

    data = response.json()
    return len(data.get("collection", [])) > 0, data

# ==============================
# STEP 2: CREATE INVITEE
# ==============================

def create_invitee(
    event_type_uri: str,
    name: str,
    email: str,
    start_time: str,
    timezone: str = "Asia/Kolkata"
):
    payload = {
        "event_type": event_type_uri,
        "start_time": start_time,
        "invitee": {
            "name": name,
            "email": email,
            "timezone": timezone
        },
        "location": {
            "kind": "google_conference"
        }
    }

    url = "https://api.calendly.com/invitees"
    response = requests.post(url, headers=HEADERS, json=payload)

    if response.status_code in (200, 201):
        return {"success": True, "data": response.json()}

    return {"success": False, "error": response.text}

# ==============================
# STEP 3: MAIN WRAPPER
# ==============================

def schedule_calendly_meeting(
    event_type_uri: str,
    name: str,
    email: str,
    start_time: str,
    duration_minutes: int = 30
):
    print("Scheduling Calendly meeting...\n")
    available, info = is_time_available(
        event_type_uri,
        start_time,
        duration_minutes
    )

    if not available:
        return {
            "success": False,
            "message": "Selected time slot is not available"
        }

    return create_invitee(
        event_type_uri=event_type_uri,
        name=name,
        email=email,
        start_time=start_time
    )

# ==============================
# EXAMPLE RUN
# ==============================

if __name__ == "__main__":
    EVENT_TYPE_URI = "https://api.calendly.com/event_types/3677b0d0-1e8d-458e-98ea-575bb00c1cb0"

    result = schedule_calendly_meeting(
        event_type_uri=EVENT_TYPE_URI,
        name="Shivank Shekhar",
        email="ssshivank120@gmail.com",
        start_time="2026-02-04T09:30:00Z"
    )

    print(result)
