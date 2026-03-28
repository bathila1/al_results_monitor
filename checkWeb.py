import requests

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

try:
    response = session.get("https://result.doenets.lk/result/service/examDetails", timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Page Length: {len(response.text)} characters")
    print("SUCCESS - Site is accessible!")
    print(response.text)
except Exception as e:
    print(f"FAILED - {e}")