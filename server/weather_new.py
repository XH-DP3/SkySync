import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from requests import HTTPError

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ECMWF_URL = "https://api.open-meteo.com/v1/ecmwf"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WTTR_URL_TEMPLATE = "https://wttr.in/{query}"
REQUEST_TIMEOUT_SECONDS = 4
WEATHER_CACHE_TTL_SECONDS = 60 * 5
WEATHER_API_RETRY_COUNT = 2

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


def _get_json_with_retry(url, params):
    last_error = None

    for attempt in range(WEATHER_API_RETRY_COUNT + 1):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except HTTPError as error:
            status_code = error.response.status_code if error.response is not None else None
            last_error = error
            if status_code is None or status_code < 500 or attempt >= WEATHER_API_RETRY_COUNT:
                raise
            time.sleep(0.35 * (attempt + 1))
        except requests.RequestException as error:
            last_error = error
            if attempt >= WEATHER_API_RETRY_COUNT:
                raise
            time.sleep(0.35 * (attempt + 1))

    if last_error:
        raise _weather_service_unavailable_error() from last_error
    raise RuntimeError("Weather request failed without an error response.")


def _fetch_weather_payload(params):
    last_error = None
    for url in (OPEN_METEO_FORECAST_URL, OPEN_METEO_ECMWF_URL):
        try:
            return _get_json_with_retry(url, params)
        except requests.RequestException as error:
            last_error = error

    if last_error:
        raise last_error
    raise RuntimeError("Weather request failed without an error response.")


def _weather_service_unavailable_error():
    return RuntimeError("Weather service is temporarily unavailable. Please try again.")


def _parse_clock_time(value):
    if not value:
        return datetime.strptime("06:00", "%H:%M").time()
    if "AM" in value or "PM" in value:
        return datetime.strptime(value, "%I:%M %p").time()
    return datetime.strptime(value, "%H:%M").time()


def _wttr_weather_code_to_condition(code):
    weather_code = int(code)
    if weather_code in {113}:
        return "clear", "Clear sky"
    if weather_code in {116}:
        return "partly cloudy", "Partly cloudy"
    if weather_code in {119, 122}:
        return "overcast", "Overcast"
    if weather_code in {143, 248, 260}:
        return "fog", "Fog"
    if weather_code in {
        176, 263, 266, 281, 284, 293, 296, 299, 302, 305, 308, 311, 314, 353, 356, 359
    }:
        return "rain", "Rain"
    if weather_code in {
        179, 182, 185, 227, 230, 317, 320, 323, 326, 329, 332, 335, 338, 350, 362, 365,
        368, 371, 374, 377, 392, 395
    }:
        return "snow", "Snow"
    if weather_code in {200, 386, 389}:
        return "thunderstorm", "Thunderstorm"
    return "clear", "Clear sky"


def _normalize_wttr_hour_time(value):
    hour = int(value or 0) // 100
    return f"{hour:02d}:00"


def _fetch_wttr_weather(location, resolved_mode):
    timezone_name = location.get("timezone") or DEFAULT_LOCATION["timezone"]
    query_value = (location.get("query") or "").strip()
    wttr_query = query_value or f"{location['latitude']},{location['longitude']}"
    payload = _get_json_with_retry(
        WTTR_URL_TEMPLATE.format(query=wttr_query),
        {"format": "j1"}
    )

    current = (payload.get("current_condition") or [{}])[0]
    weather_days = payload.get("weather") or []
    if not weather_days:
        raise RuntimeError("Fallback weather provider returned no forecast data.")

    now_local = datetime.now(ZoneInfo(timezone_name))
    if resolved_mode == "tomorrow_morning" and len(weather_days) > 1:
        selected_day = weather_days[1]
        target_hour = 900
        base_dt = now_local + timedelta(days=1)
    else:
        selected_day = weather_days[0]
        target_hour = 2100 if resolved_mode == "tonight" else None
        base_dt = now_local

    hourly_blocks = selected_day.get("hourly") or []
    selected_hourly = None
    if target_hour is not None and hourly_blocks:
        selected_hourly = min(
            hourly_blocks,
            key=lambda item: abs(int(item.get("time", "0")) - target_hour)
        )

    if selected_hourly:
        time_text = _normalize_wttr_hour_time(selected_hourly.get("time", "0"))
        selected_dt = base_dt.replace(
            hour=int(time_text[:2]),
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=None
        )
        temperature = float(selected_hourly.get("tempC", 0))
        wttr_code = selected_hourly.get("weatherCode", current.get("weatherCode", 113))
        is_day = 1 if 6 <= selected_dt.hour < 20 else 0
    else:
        selected_dt = base_dt.replace(tzinfo=None)
        time_text = selected_dt.strftime("%H:%M")
        temperature = float(current.get("temp_C", 0))
        wttr_code = current.get("weatherCode", 113)
        is_day = 1 if current.get("isdaytime", "yes").lower() == "yes" else 0

    astronomy = (selected_day.get("astronomy") or [{}])[0]
    sunrise_clock = _parse_clock_time(astronomy.get("sunrise", "06:00 AM"))
    sunset_clock = _parse_clock_time(astronomy.get("sunset", "06:00 PM"))
    category, condition = _wttr_weather_code_to_condition(wttr_code)
    computed_is_day = _compute_is_day(_parse_clock_time(time_text), sunrise_clock, sunset_clock)

    return {
        "date": selected_day.get("date") or selected_dt.strftime("%Y-%m-%d"),
        "time": time_text,
        "temperature": round(temperature, 1),
        "condition": condition,
        "sunrise": sunrise_clock.strftime("%H:%M"),
        "sunset": sunset_clock.strftime("%H:%M"),
        "is_day": computed_is_day,
        "category": category,
        "forecast_mode": resolved_mode,
        "time_of_day": _classify_time_of_day(
            _parse_clock_time(time_text),
            sunrise_clock,
            sunset_clock
        ),
        "location": {
            "name": location.get("name") or query_value or "Unknown",
            "admin1": location.get("admin1") or "",
            "country": location.get("country") or "",
            "timezone": timezone_name,
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude")
        }
    }


def _cache_key(location, forecast_mode):
    if location.get("latitude") is None or location.get("longitude") is None:
        return (
            (location.get("query") or location.get("name") or "").strip().lower(),
            str(location.get("timezone") or "auto"),
            forecast_mode
        )
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


def _get_stale_cache(cache_key):
    entry = _weather_cache.get(cache_key)
    if not entry:
        return None
    cached_value = dict(entry["value"])
    cached_value["stale"] = True
    return cached_value


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


def _compute_is_day(current_time, sunrise_time, sunset_time):
    return int(sunrise_time <= current_time < sunset_time)


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
    current = payload.get("current") or {}
    current_payload = current or current_weather

    if forecast_mode == "now":
        observation_time = current_payload.get("time")
        if observation_time:
            selected_dt = _parse_iso_local(observation_time)
        else:
            selected_dt = datetime.now(ZoneInfo(timezone_name)).replace(tzinfo=None)

        weather_code = current_payload.get("weathercode", current_payload.get("weather_code"))
        return {
            "selected_dt": selected_dt,
            "temperature": current_payload.get(
                "temperature",
                current_payload.get("temperature_2m", 0)
            ),
            "weather_code": weather_code,
            "is_day": int(current_payload.get("is_day", 1))
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

    try:
        response = requests.get(
            OPEN_METEO_GEOCODING_URL,
            params={"name": query.strip(), "count": max(1, min(count, 10)), "language": "en", "format": "json"},
            timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        raise RuntimeError(
            "Location search is temporarily unavailable. Try typing a city and loading weather directly."
        ) from error

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
        try:
            matches = search_locations(query, count=1)
        except requests.RequestException:
            matches = []
        if matches:
            return matches[0]
        return {
            "name": query,
            "query": query,
            "country": "",
            "admin1": "",
            "timezone": timezone_name,
            "latitude": None,
            "longitude": None
        }

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
    try:
        if location.get("latitude") is None or location.get("longitude") is None:
            result = _fetch_wttr_weather(location, resolved_mode)
        else:
            request_params = {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": "temperature_2m,weather_code,is_day",
                "hourly": "temperature_2m,weather_code,is_day",
                "daily": "sunrise,sunset",
                "timezone": timezone_name,
                "forecast_days": 3
            }
            payload = _fetch_weather_payload(request_params)

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
            computed_is_day = _compute_is_day(current_clock, sunrise_clock, sunset_clock)

            result = {
                "date": selected_dt.strftime("%Y-%m-%d"),
                "time": selected_dt.strftime("%H:%M"),
                "temperature": round(float(point["temperature"]), 1),
                "condition": CONDITION_MAP.get(weather_code, "Unknown"),
                "sunrise": _to_hhmm(sunrise_raw),
                "sunset": _to_hhmm(sunset_raw),
                "is_day": computed_is_day,
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
    except Exception:
        try:
            result = _fetch_wttr_weather(location, resolved_mode)
        except Exception:
            stale_weather = _get_stale_cache(cache_key)
            if stale_weather:
                return stale_weather
            raise _weather_service_unavailable_error()

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
