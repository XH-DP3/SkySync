import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
REQUEST_TIMEOUT_SECONDS = 10
WEATHER_CACHE_TTL_SECONDS = 60 * 5

DEFAULT_LOCATION = {
    "name": "Vancouver",
    "latitude": 49.2827,
    "longitude": -123.1207,
    "timezone": "America/Vancouver",
    "country": "Canada",
    "admin1": "British Columbia"
}

CONDITION_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy rain showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail"
}

_weather_cache = {}


def _cache_key(location, forecast_mode):
    return (
        round(float(location["latitude"]), 3),
        round(float(location["longitude"]), 3),
        str(location.get("timezone") or "auto"),
        forecast_mode
    )


def _get_from_cache(cache_key):
    entry = _weather_cache.get(cache_key)
    if not entry:
        return None
    if (time.time() - entry["timestamp"]) > WEATHER_CACHE_TTL_SECONDS:
        return None
    return dict(entry["value"])


def _set_cache(cache_key, value):
    _weather_cache[cache_key] = {
        "timestamp": time.time(),
        "value": dict(value)
    }


def _to_category(code):
    if code in {0, 1}:
        return "clear"
    if code in {2}:
        return "partly cloudy"
    if code in {3}:
        return "overcast"
    if code in {45, 48}:
        return "fog"
    if code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
        return "rain"
    if code in {71, 73, 75, 77, 85, 86}:
        return "snow"
    if code in {95, 96, 99}:
        return "thunderstorm"
    return "clear"


def _to_hhmm(iso_time):
    return datetime.fromisoformat(iso_time).strftime("%H:%M")


def _parse_iso_local(iso_value):
    return datetime.fromisoformat(iso_value)


def _classify_time_of_day(current_time, sunrise_time, sunset_time):
    current_dt = datetime.combine(datetime.today().date(), current_time)
    sunrise_dt = datetime.combine(datetime.today().date(), sunrise_time)
    sunset_dt = datetime.combine(datetime.today().date(), sunset_time)

    if abs(current_dt - sunrise_dt) <= timedelta(hours=1):
        return "Sunrise"
    if abs(current_dt - sunset_dt) <= timedelta(hours=1):
        return "Sunset"
    if current_time < datetime.strptime("06:00", "%H:%M").time():
        return "Night"
    if current_time < datetime.strptime("12:00", "%H:%M").time():
        return "Morning"
    if current_time < datetime.strptime("16:00", "%H:%M").time():
        return "Afternoon"
    if current_time < datetime.strptime("20:00", "%H:%M").time():
        return "Evening"
    return "Night"


def _choose_daily_sun_times(daily_data, selected_date):
    dates = daily_data.get("time", [])
    sunrises = daily_data.get("sunrise", [])
    sunsets = daily_data.get("sunset", [])

    fallback_sunrise = sunrises[0] if sunrises else None
    fallback_sunset = sunsets[0] if sunsets else None

    for index, date_value in enumerate(dates):
        if date_value == selected_date and index < len(sunrises) and index < len(sunsets):
            return sunrises[index], sunsets[index]

    return fallback_sunrise, fallback_sunset


def _resolve_hourly_target_datetime(forecast_mode, timezone_name):
    now_local = datetime.now(ZoneInfo(timezone_name))

    if forecast_mode == "tonight":
        target = now_local.replace(hour=21, minute=0, second=0, microsecond=0)
        if now_local.hour >= 22:
            target = target + timedelta(days=1)
        return target

    if forecast_mode == "tomorrow_morning":
        return (now_local + timedelta(days=1)).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0
        )

    return now_local


def _select_weather_point(payload, forecast_mode, timezone_name):
    current_weather = payload.get("current_weather") or {}

    if forecast_mode == "now":
        observation_time = current_weather.get("time")
        if observation_time:
            selected_dt = _parse_iso_local(observation_time)
        else:
            selected_dt = datetime.now(ZoneInfo(timezone_name)).replace(tzinfo=None)

        weather_code = current_weather.get("weathercode", current_weather.get("weather_code"))
        return {
            "selected_dt": selected_dt,
            "temperature": current_weather.get("temperature", 0),
            "weather_code": weather_code,
            "is_day": int(current_weather.get("is_day", 1))
        }

    hourly = payload.get("hourly") or {}
    hourly_times = [_parse_iso_local(value) for value in hourly.get("time", [])]
    temperatures = hourly.get("temperature_2m", [])
    weather_codes = hourly.get("weather_code", [])
    is_day_values = hourly.get("is_day", [])

    if not hourly_times:
        raise RuntimeError("Hourly forecast data unavailable for selected forecast mode.")

    target = _resolve_hourly_target_datetime(forecast_mode, timezone_name)
    target_naive = target.replace(tzinfo=None)

    best_index = min(
        range(len(hourly_times)),
        key=lambda idx: abs(hourly_times[idx] - target_naive)
    )

    return {
        "selected_dt": hourly_times[best_index],
        "temperature": temperatures[best_index] if best_index < len(temperatures) else 0,
        "weather_code": weather_codes[best_index] if best_index < len(weather_codes) else None,
        "is_day": int(is_day_values[best_index]) if best_index < len(is_day_values) else 1
    }


def search_locations(query, count=6):
    if not query or not query.strip():
        return []

    response = requests.get(
        OPEN_METEO_GEOCODING_URL,
        params={"name": query.strip(), "count": max(1, min(count, 10)), "language": "en", "format": "json"},
        timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    payload = response.json()

    results = []
    for item in payload.get("results", []):
        location_name = item.get("name") or "Unknown"
        admin1 = item.get("admin1") or ""
        country = item.get("country") or ""
        label_parts = [location_name]
        if admin1:
            label_parts.append(admin1)
        if country:
            label_parts.append(country)

        results.append(
            {
                "name": location_name,
                "country": country,
                "admin1": admin1,
                "timezone": item.get("timezone") or "auto",
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "label": ", ".join(label_parts)
            }
        )

    return results


def resolve_location(location_payload=None):
    if not location_payload:
        return dict(DEFAULT_LOCATION)

    latitude = location_payload.get("latitude")
    longitude = location_payload.get("longitude")
    timezone_name = location_payload.get("timezone") or DEFAULT_LOCATION["timezone"]

    if latitude is not None and longitude is not None:
        return {
            "name": location_payload.get("name") or "Custom Location",
            "country": location_payload.get("country") or "",
            "admin1": location_payload.get("admin1") or "",
            "timezone": timezone_name,
            "latitude": float(latitude),
            "longitude": float(longitude)
        }

    query = (location_payload.get("query") or "").strip()
    if query:
        matches = search_locations(query, count=1)
        if matches:
            return matches[0]

    return dict(DEFAULT_LOCATION)


def get_clean_weather(location_payload=None, forecast_mode="now", use_cache=True):
    resolved_mode = forecast_mode if forecast_mode in {"now", "tonight", "tomorrow_morning"} else "now"
    location = resolve_location(location_payload)

    cache_key = _cache_key(location, resolved_mode)
    if use_cache:
        cached_weather = _get_from_cache(cache_key)
        if cached_weather:
            return cached_weather

    timezone_name = location.get("timezone") or "auto"
    response = requests.get(
        OPEN_METEO_URL,
        params={
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current_weather": True,
            "hourly": "temperature_2m,weather_code,is_day",
            "daily": "sunrise,sunset",
            "timezone": timezone_name,
            "forecast_days": 3
        },
        timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    payload = response.json()

    point = _select_weather_point(payload, resolved_mode, timezone_name)
    weather_code = point["weather_code"]
    if weather_code is None:
        raise RuntimeError("Weather API response missing weather code.")

    selected_dt = point["selected_dt"]
    selected_date = selected_dt.strftime("%Y-%m-%d")

    daily = payload.get("daily") or {}
    sunrise_raw, sunset_raw = _choose_daily_sun_times(daily, selected_date)
    if not sunrise_raw or not sunset_raw:
        raise RuntimeError("Weather API response missing sunrise or sunset data.")

    sunrise_clock = datetime.strptime(_to_hhmm(sunrise_raw), "%H:%M").time()
    sunset_clock = datetime.strptime(_to_hhmm(sunset_raw), "%H:%M").time()
    current_clock = selected_dt.time()

    result = {
        "date": selected_dt.strftime("%Y-%m-%d"),
        "time": selected_dt.strftime("%H:%M"),
        "temperature": round(float(point["temperature"]), 1),
        "condition": CONDITION_MAP.get(weather_code, "Unknown"),
        "sunrise": _to_hhmm(sunrise_raw),
        "sunset": _to_hhmm(sunset_raw),
        "is_day": point["is_day"],
        "category": _to_category(weather_code),
        "forecast_mode": resolved_mode,
        "time_of_day": _classify_time_of_day(current_clock, sunrise_clock, sunset_clock),
        "location": {
            "name": location.get("name") or "Unknown",
            "admin1": location.get("admin1") or "",
            "country": location.get("country") or "",
            "timezone": timezone_name,
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude")
        }
    }

    if use_cache:
        _set_cache(cache_key, result)

    return result


def get_weather_state(location_payload=None, forecast_mode="now", use_cache=True):
    snapshot = get_clean_weather(
        location_payload=location_payload,
        forecast_mode=forecast_mode,
        use_cache=use_cache
    )
    return {
        "current_weather": snapshot["condition"],
        "current_time": snapshot["time_of_day"],
        "weather_snapshot": snapshot
    }
