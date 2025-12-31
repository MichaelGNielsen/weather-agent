import os
import sys
from dotenv import load_dotenv
from anthropic import Anthropic
import requests

load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("Sæt ANTHROPIC_API_KEY i .env")

client = Anthropic(api_key=api_key)

# Funktion til at hente vejrdata
def get_weather(city: str = "Aalborg") -> dict:
    """Henter vejrdata fra Open-Meteo API"""
    try:
        # Slå koordinater op via Geocoding API
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geo_response = requests.get(geo_url)
        geo_response.raise_for_status()
        geo_data = geo_response.json()

        if "results" not in geo_data or not geo_data["results"]:
            return {"error": f"Kunne ikke finde koordinater for {city}"}

        location = geo_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]
        found_name = location["name"]

        # Open-Meteo API (gratis, ingen API-nøgle nødvendig)
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,windspeed_10m,weathercode&timezone=Europe/Copenhagen"

        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        return {
            "city": found_name,
            "temperature": data["current"]["temperature_2m"],
            "wind_speed": data["current"]["windspeed_10m"],
            "weather_code": data["current"]["weathercode"]
        }
    except Exception as e:
        return {"error": str(e)}

# Tool definition
tools = [
    {
        "name": "get_weather",
        "description": "Henter aktuelle vejrdata for en given by i Danmark",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Navnet på byen, f.eks. 'Aalborg'"
                }
            }
        }
    }
]

# Første API-kald
if len(sys.argv) > 1:
    city_arg = " ".join(sys.argv[1:])
    prompt = f"Hej, kan du skrive en kort opsummering af vejret i {city_arg} i dag?"
else:
    prompt = "Hej, kan du skrive en kort opsummering af vejret i Aalborg i dag?"

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": prompt}
    ]
)

print("=== FØRSTE RESPONS ===")
print(f"Stop reason: {response.stop_reason}")
print(f"Content: {response.content}")

# Håndter tool calls
while response.stop_reason == "tool_use":
    tool_use = next(block for block in response.content if block.type == "tool_use")
    tool_name = tool_use.name
    tool_input = tool_use.input

    print(f"\n=== TOOL CALL: {tool_name} ===")
    print(f"Input: {tool_input}")

    # Kald funktionen
    if tool_name == "get_weather":
        tool_result = get_weather(**tool_input)
    else:
        tool_result = {"error": "Ukendt tool"}

    print(f"Result: {tool_result}")

    # Send resultatet tilbage til Claude
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=tools,
        messages=[
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response.content},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": str(tool_result)
                    }
                ]
            }
        ]
    )

# Udskriv det endelige svar
print("\n=== ENDELIGT SVAR ===")
for block in response.content:
    if hasattr(block, "text"):
        print(block.text)