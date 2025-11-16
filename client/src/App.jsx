import { useState } from "react";
import "./App.css";

import clearDay from "./assets/clear_day.png";
import clearNight from "./assets/clear_night.png";

import partlyCloudyDay from "./assets/partly_cloudy_day.png";
import partlyCloudyNight from "./assets/partly_cloudy_night.png";

import overcastDay from "./assets/overcast_day.png";
import overcastNight from "./assets/overcast_night.png";

import fog from "./assets/fog.png";

import rainDay from "./assets/rain_day.gif";
import rainNight from "./assets/rain_night.gif";

import snowDay from "./assets/snow_day.gif";
import snowNight from "./assets/snow_night.gif";

import thunderDay from "./assets/thunder_day.gif";
import thunderNight from "./assets/thunder_night.gif";

import mainBackground from "./assets/main_background.png";



function App() {
  const [weather, setWeather] = useState(null);

  if (!weather) {
    document.body.style.backgroundImage = `url(${mainBackground})`;
  }

  async function loadWeather() {
    const latitude = 49.2827;
    const longitude = -123.1207;

    const url =
      `https://api.open-meteo.com/v1/forecast?latitude=${latitude}` +
      `&longitude=${longitude}&current_weather=true&daily=sunrise,sunset&timezone=auto`;

    const res = await fetch(url);
    const data = await res.json();

    const w = data.current_weather;
    const sunriseRaw = data.daily.sunrise[0];
    const sunsetRaw = data.daily.sunset[0];
    const today = sunriseRaw.split("T")[0];

    const currentTime = new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit"
      });
      

    const sunriseTime = formatTime(sunriseRaw);
    const sunsetTime = formatTime(sunsetRaw);

    const condition = weatherCodeToText(w.weathercode);

    // this is the added code
    const category = weatherCodeToCategory(w.weathercode);
const timeOfDay = w.is_day === 1 ? "day" : "night";
const bgImage = weatherImages[category][timeOfDay];

document.body.style.backgroundImage = `url(${bgImage})`;


setWeather({
    date: today,
    time: currentTime,   // 👈 ADD THIS
    temperature: w.temperature,
    condition,
    sunrise: sunriseTime,
    sunset: sunsetTime,
    is_day: w.is_day,
  });
  

    // Switch background
    document.body.classList.toggle("day", w.is_day === 1);
    document.body.classList.toggle("night", w.is_day !== 1);
  }

  function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function weatherCodeToText(code) {
    const map = {
      0: "Clear sky",
      1: "Clear sky",
      2: "Partly cloudy",
      3: "Overcast",
      45: "Fog",
      48: "Fog",
      51: "Rain",
      53: "Rain",
      55: "Rain",
      56: "Rain",
      61: "Rain",
      63: "Rain",
      65: "Rain",
      67: "Rain",
      71: "Snow",
      73: "Snow",
      75: "Snow",
      77: "Snow",
      80: "Rain",
      81: "Rain",
      82: "Rain",
      85: "Snow",
      86: "Snow",
      95: "Thunderstorm",
      96: "Thunderstorm",
      99: "Thunderstorm"
    };
    return map[code] || "Unknown";
  }

  return (
    <div className="app">
  
  {weather && (
  <div className="weather-bubble">

    <h1 className="bubble-title">Current Weather</h1>

    <p>📅 Date: {weather.date}</p>
    <p>🕒 Time: {weather.time}</p>
    <p>🌡 Temperature: {weather.temperature}°C</p>
    <p>⛅ Condition: {weather.condition}</p>
    <p>🌅 Sunrise: {weather.sunrise}</p>
    <p>🌇 Sunset: {weather.sunset}</p>


  </div>
)}

  
      {!weather && (
        <h1 className="initial-title">SkySync</h1>
      )}
  
      <button id="loadBtn" onClick={loadWeather}>Load Weather</button>

      {weather && (
  <div className="spotify-section">
    <input
      type="text"
      placeholder="Paste your Spotify link..."
      className="spotify-input"
    />
    <button className="spotify-generate-btn">Generate</button>
  </div>
)}


    </div>
  );
  
}

const weatherImages = {
    clear: {
      day: clearDay,
      night: clearNight
    },
    "partly cloudy": {
      day: partlyCloudyDay,
      night: partlyCloudyNight
    },
    "mainly clear": {
      day: partlyCloudyDay, // reuse partly cloudy
      night: partlyCloudyNight
    },
    overcast: {
      day: overcastDay,
      night: overcastNight
    },
    fog: {
      day: fog,
      night: fog
    },
    rain: {
      day: rainDay,
      night: rainNight
    },
    snow: {
      day: snowDay,
      night: snowNight
    },
    thunderstorm: {
      day: thunderDay,
      night: thunderNight
    }
  };

  function weatherCodeToCategory(code) {
    if ([0].includes(code)) return "clear";
    if ([1, 2].includes(code)) return "partly cloudy";
    if ([3].includes(code)) return "overcast";
    if ([45, 48].includes(code)) return "fog";
    if ([51, 53, 55, 61, 63, 65, 80].includes(code)) return "rain";
    if ([71].includes(code)) return "snow";
    if ([95].includes(code)) return "thunderstorm";
    return "clear"; // fallback
  }
  
  
export default App;
