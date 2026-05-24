import requests

# REPLACE THIS WITH YOUR NEW, SECURE TOKEN
CALENDLY_TOKEN = "eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiUEFUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzY5OTY1Mjc5LCJqdGkiOiI2MjI5NjJkZC02YjU0LTRiZWEtOTJmMi1hM2Q5ODQ2NzliYTIiLCJ1c2VyX3V1aWQiOiI1MzM3MzZmMy02N2U5LTQ0YmMtYjQxOS1iOWRkOWQzZjMxYzkifQ.fsyGCwbKBh54d5i8qPG3qVU0z7H1_Ul1Luf6MVwUNaiRNTSRyG7duPaSAbulF-V-1g-tMytHEMsvBXs_YuPXDg"

HEADERS = {
    "Authorization": f"Bearer {CALENDLY_TOKEN}",
    "Content-Type": "application/json"
}

def get_event_type_uris():
    # Step 1: Get your "User URI" (Required to filter event types)
    user_resp = requests.get("https://api.calendly.com/users/me", headers=HEADERS)
    if user_resp.status_code != 200:
        print(f"Error getting user: {user_resp.text}")
        return

    user_uri = user_resp.json()['resource']['uri']
    print(f"Found User: {user_uri}")

    # Step 2: Get Event Types using that User URI
    params = {"user": user_uri, "active": "true"}
    events_resp = requests.get("https://api.calendly.com/event_types", headers=HEADERS, params=params)

    if events_resp.status_code == 200:
        events = events_resp.json().get('collection', [])
        print(f"\nFound {len(events)} active event types:\n")
        
        for event in events:
            print(f"Name: {event['name']}")
            print(f"URI:  {event['uri']}") # <--- THIS IS YOUR EVENT TYPE URI
            print("-" * 40)
    else:
        print(f"Error getting events: {events_resp.text}")

if __name__ == "__main__":
    get_event_type_uris()