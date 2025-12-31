import requests

url = "https://dmigw.govcloud.dk/v2/observations/aggregate"
params = {
    "station": "2624886",  # Aalborg
    "parameter": "t,ff,rr1",
    "time": "latest"
}

try:
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    print(data)
except Exception as e:
    print("Kunne ikke hente vejret:", e)
