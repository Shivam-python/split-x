import requests
import json, time

def trylogin():
    url = "http://localhost:8000/users/login/"

    payload = json.dumps({
        "email": "sam.dev2@yopmail.com",
        "password": "sam123"
    })
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return response.status_code


def test_throttle(limit=100, delay=0.1):
    success = 0
    throttle_hit = 0
    other_errors = 0

    print(f"\n🚀 Starting login burst: trying {limit} times with {delay}s delay")

    for i in range(limit):
        status = trylogin()
        if status == 200:
            success += 1
        elif status == 429:
            throttle_hit += 1
            print("⚠️ Throttled!")
        else:
            other_errors += 1
        time.sleep(delay)

    print(f"\n✅ Completed {limit} login attempts:")
    print(f"  - Successful: {success}")
    print(f"  - Throttled (429): {throttle_hit}")
    print(f"  - Other errors: {other_errors}")

test_throttle()