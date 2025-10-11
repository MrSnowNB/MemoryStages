import requests

# Test main health first
url_main_health = "http://127.0.0.1:8000/health"
response_main = requests.get(url_main_health)
print(f"Main Health Status Code: {response_main.status_code}")
if response_main.status_code == 200:
    print("Main Health Response:")
    print(response_main.json())
else:
    print("Main Health failed")

# Test chat health first
url_health = "http://127.0.0.1:8000/chat/health"
response_health = requests.get(url_health)
print(f"Chat Health Status Code: {response_health.status_code}")
if response_health.status_code == 200:
    print("Chat Health Response:")
    print(response_health.json())
else:
    print("Chat Health failed")

# Test message
url = "http://127.0.0.1:8000/chat/message"
data = {"content": "Test message", "user_id": "default"}
response = requests.post(url, json=data)
print(f"Message Status Code: {response.status_code}")
print("Response:")
print(response.json())
