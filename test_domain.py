import requests
from bs4 import BeautifulSoup

url = "https://globalitinnovation.com/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}
resp = requests.get(url, headers=headers)
print(f"Status: {resp.status_code}")
print(f"URL: {resp.url}")

soup = BeautifulSoup(resp.text, "html.parser")
links = soup.find_all('a', href=True)
print(f"Found {len(links)} links")
if len(links) > 0:
    for a in links[:5]:
        print(a['href'])
    print("...")

html_head = resp.text[:500]
print("HTML Start:", html_head)
