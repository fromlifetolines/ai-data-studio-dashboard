import httpx

api_key = "AIzaSyBgmLnmlV0XKe47d5e_ub4Dyr3YGQLvf1o"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

r = httpx.get(url)
print("HTTP Status:", r.status_code)
if r.status_code == 200:
    models = r.json().get("models", [])
    for m in models:
        print(m.get("name"), m.get("supportedGenerationMethods"))
else:
    print(r.text)
