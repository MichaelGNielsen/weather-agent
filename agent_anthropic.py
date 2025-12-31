import os
from dotenv import load_dotenv
from anthropic import Anthropic
import requests

load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("Sæt ANTHROPIC_API_KEY i .env")

client = Anthropic(api_key=api_key)

# Funktion til at hente vejrdata
def get_weather(city: str) -> dict:
    """Henter vejrdata fra Open-Meteo API"""
    # Koordinater for Aalborg
    coordinates = {
        "aalborg": {"lat": 57.048, "lon": 9.9187}
    }

    city_lower = city.lower()
    if city_lower not in coordinates:
        return {"error": f"Kender ikke koordinater for {city}"}

    lat = coordinates[city_lower]["lat"]
    lon = coordinates[city_lower]["lon"]

    # Open-Meteo API (gratis, ingen API-nøgle nødvendig)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,windspeed_10m,weathercode&timezone=Europe/Copenhagen"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        return {
            "city": city,
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
            },
            "required": ["city"]
        }
    }
]

# Første API-kald
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
        tool_result = get_weather(tool_input["city"])
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