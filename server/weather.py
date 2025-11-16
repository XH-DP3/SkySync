import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

from datetime import datetime, timedelta, time
import pytz  # Optional, for timezone handling


WEATHER_CODE_MAP = {
    0:  "Clear sky",

    1:  "Mainly clear",
    2:  "Partly cloudy",
    3:  "Overcast",

    45: "Fog",
    48: "Depositing rime fog",

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

    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",

    77: "Snow grains",

    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",

    85: "Slight snow showers",
    86: "Heavy snow showers",

    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://api.open-meteo.com/v1/forecast"
params = {
	"latitude": 49.26,
	"longitude": -123.25,
	"daily": ["sunset", "sunrise"],
	"hourly": "weather_code",
	"timezone": "auto",
	"forecast_days": 1,
}
responses = openmeteo.weather_api(url, params=params)

# Process first location. Add a for-loop for multiple locations or weather models
response = responses[0]

# Process hourly data. The order of variables needs to be the same as requested.
hourly = response.Hourly()
hourly_weather_code = hourly.Variables(0).ValuesAsNumpy()

hourly_data = {"date": pd.date_range(
	start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
	end =  pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = hourly.Interval()),
	inclusive = "left"
)}


hourly_data["weather_code"] = hourly_weather_code

hourly_dataframe = pd.DataFrame(data = hourly_data)

hourly_dataframe["weather_description"] = hourly_dataframe["weather_code"].map(WEATHER_CODE_MAP)

def unix_to_time(unix_ts):
    dt = datetime.datetime.fromtimestamp(unix_ts, tz=datetime.timezone.utc)
    return dt.time()  # returns datetime.time object (HH:MM:SS)

# Process daily data. The order of variables needs to be the same as requested.
daily = response.Daily()
daily_sunset = daily.Variables(0).ValuesInt64AsNumpy()
daily_sunrise = daily.Variables(1).ValuesInt64AsNumpy()

daily_data = {"date": pd.date_range(
	start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
	end =  pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = daily.Interval()),
	inclusive = "left"
)}

daily_data["sunset"] = daily_sunset
daily_data["sunrise"] = daily_sunrise

daily_dataframe = pd.DataFrame(data = daily_data)

# Map the conversion functions to create new readable time columns
daily_dataframe["sunset_time"] = pd.to_datetime(daily_sunset, unit="s").tz_localize("UTC").tz_convert("America/Vancouver")
daily_dataframe["sunrise_time"] = pd.to_datetime(daily_sunrise, unit="s").tz_localize("UTC").tz_convert("America/Vancouver")



def get_current_time() :
    now = datetime.now(pytz.timezone('America/Vancouver'))
    print(now)


def get_current_weather(df):
    now = datetime.now(pytz.timezone('America/Vancouver'))
    filtered = df[df['date'] <= now]
    if filtered.empty:
        return None  # or handle no data case
    current = filtered.iloc[-1]["weather_description"]
    return current
    

def is_within_one_hour_of_sunset(daily_df):
    now = datetime.now(pytz.timezone('America/Vancouver'))  # current time

    # Find today's row in daily_df (match by date ignoring time)
    today_row = daily_df[daily_df['date'].dt.date == now.date()]
    if today_row.empty:
        return False  # No data for today
    
    # Get sunset time for today, convert if needed
    sunset_time = today_row.iloc[0]['sunset_time']

    # Calculate time difference
    diff = abs(now - sunset_time)

    # Return True if within 1 hour (3600 seconds)
    return diff <= timedelta(hours=1)

def is_within_one_hour_of_sunrise(daily_df):
    now = datetime.now(pytz.timezone('America/Vancouver'))  # current time

    # Find today's row in daily_df (match by date ignoring time)
    today_row = daily_df[daily_df['date'].dt.date == now.date()]
    if today_row.empty:
        return False  # No data for today
    
    # Get sunrise time for today, convert if needed
    sunrise_time = today_row.iloc[0]['sunrise_time']

    # Calculate time difference
    diff = abs(now - sunrise_time)

    # Return True if within 1 hour (3600 seconds)
    return diff <= timedelta(hours=1)


# Define 8:00:00 AM as a time object
morning_start = time(6, 0, 0)  # 10:30:00 AM
morning_cutoff = time(12, 0, 0)  # 10:30:00 AM
afternoon_cutoff = time(16, 0, 0)  # 10:00:00 AM
evening_cutoff = time(20, 0, 0)  # 10:00:00 AM

def get_current_time_of_day():
    now = datetime.now(pytz.timezone('America/Vancouver')).time()

    if is_within_one_hour_of_sunrise(daily_dataframe):
        return "Sunrise"
    elif is_within_one_hour_of_sunset(daily_dataframe):
        return "Sunset"
    elif now < morning_start:
        return "Night"
    elif now < morning_cutoff:
        return "Morning"
    elif now < afternoon_cutoff:
        return "Afternoon"
    elif now < evening_cutoff:
        return "Evening"
    else:
        return "Night"


def get_weather_state():
    return {"current_weather" : get_current_weather(hourly_dataframe), 
            "current_time" : get_current_time_of_day()}


