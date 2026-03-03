import urllib.request
import json

data = json.dumps({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(
    "http://localhost:8000/api/v1/auth/login",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f"Status: {resp.status}")
        print(resp.read().decode())
except Exception as e:
    print(f"Error: {e}")
