import requests
from datetime import datetime

def get_clean_weather():
    # Vancouver's coordinate
    latitude = 49.2593
    longitude = -123.2475

    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}"
        f"&longitude={longitude}&current_weather=true&daily=sunrise,sunset&timezone=auto"
    )

    res = requests.get(url).json()

    w = res["current_weather"]
    sunrise_raw = res["daily"]["sunrise"][0]
    sunset_raw = res["daily"]["sunset"][0]

    def format_time(iso):
        return datetime.fromisoformat(iso).strftime("%H:%M")

    sunrise = format_time(sunrise_raw)
    sunset = format_time(sunset_raw)
    now = datetime.now().strftime("%H:%M")
    today = sunrise_raw.split("T")[0]

    condition_map = {
        0: "Clear sky", 1: "Clear sky",
        2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Fog",
        51: "Rain", 53: "Rain", 55: "Rain", 56: "Rain",
        61: "Rain", 63: "Rain", 65: "Rain",
        67: "Rain",
        71: "Snow", 73: "Snow", 75: "Snow", 77: "Snow",
        80: "Rain", 81: "Rain", 82: "Rain",
        85: "Snow", 86: "Snow",
        95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm"
    }

    def category(code):
        if code in [0]: return "clear"
        if code in [1, 2]: return "partly cloudy"
        if code in [3]: return "overcast"
        if code in [45, 48]: return "fog"
        if code in [51, 53, 55, 61, 63, 65, 80]: return "rain"
        if code in [71]: return "snow"
        if code in [95, 96, 99]: return "thunderstorm"
        return "clear"

    code = w["weathercode"]

    return {
        "date": today,
        "time": now,
        "temperature": w["temperature"],
        "condition": condition_map.get(code, "Unknown"),
        "sunrise": sunrise,
        "sunset": sunset,
        "is_day": w["is_day"],
        "category": category(code)
    }

