import { useState } from "react";
import "./App.css";

// ======= IMPORT ASSETS =======
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

// ======= WEATHER → IMAGE MAP =======
const weatherImages = {
  clear: { day: clearDay, night: clearNight },
  "partly cloudy": { day: partlyCloudyDay, night: partlyCloudyNight },
  "mainly clear": { day: partlyCloudyDay, night: partlyCloudyNight },
  overcast: { day: overcastDay, night: overcastNight },
  fog: { day: fog, night: fog },
  rain: { day: rainDay, night: rainNight },
  snow: { day: snowDay, night: snowNight },
  thunderstorm: { day: thunderDay, night: thunderNight }
};

// =============================
//            APP
// =============================
function App() {
  const [weather, setWeather] = useState(null);
  const [spotifyLink, setSpotifyLink] = useState("");
  const [playlistGenerated, setPlaylistGenerated] = useState(false);
  const [playlistTitle, setPlaylistTitle] = useState("");

  // MAIN PAGE BACKGROUND
  if (!weather) {
    document.body.style.backgroundImage = `url(${mainBackground})`;
  }

  // ======= LOAD WEATHER =======
  async function loadWeather() {
    const res = await fetch("/api/weather_new"); 
    const data = await res.json();
    setWeather(data);

    const timeOfDay = data.is_day === 1 ? "day" : "night";
    const bgImage = weatherImages[data.category][timeOfDay];
    document.body.style.backgroundImage = `url(${bgImage})`;
  }

  // ======= GENERATE PLAYLIST (backend call) =======
  async function generatePlaylist() {
    try {
      const res = await fetch("/api/makeplaylistcurrentweather");
      const data = await res.json();
  
      console.log("Playlist generated:", data);
  
      // save title from backend
      setPlaylistTitle(data.title);
  
      setPlaylistGenerated(true);  // reveal the right bubble
    } catch (err) {
      console.error("Playlist error:", err);
      alert("Error generating playlist.");
    }
  }
  

  return (
    <div className="app">

      {/* MAIN SCREEN BEFORE WEATHER */}
      {!weather && (
        <div className="main-screen">
          <h1 className="initial-title">SkySync</h1>

          <button id="loadBtn" onClick={loadWeather}>
            Load Weather
          </button>
        </div>
      )}

      {/* WEATHER + PLAYLIST AREA */}
      {weather && (
        <div className={`page-layout ${playlistGenerated ? "shifted" : ""}`}>

          {/* LEFT BUBBLE — WEATHER */}
          <div className="weather-bubble">
            <h1 className="bubble-title">Current Weather</h1>

            <p>📅 Date: {weather.date}</p>
            <p>🕒 Time: {weather.time}</p>
            <p>🌡 Temperature: {weather.temperature}°C</p>
            <p>⛅ Condition: {weather.condition}</p>
            <p>🌅 Sunrise: {weather.sunrise}</p>
            <p>🌇 Sunset: {weather.sunset}</p>
          </div>

          {/* RIGHT BUBBLE — PLAYLIST */}
          {playlistGenerated && (
  <div className="playlist-bubble">

    {/* BIG TITLE (same size as Current Weather) */}
    <h1 className="bubble-title">Title: {playlistTitle}</h1>

    {/* Subtitle */}
    <h2 className="playlist-ready-subtitle">Playlist Ready</h2>

    <p>Your personalized playlist is generated!</p>

    <button className="spotify-open-btn">
      Open Playlist
    </button>
  </div>
)}


        </div>
      )}

      {/* SPOTIFY INPUT BELOW WEATHER (before playlist appears) */}
      {weather && !playlistGenerated && (
  <div className="generate-section">
    <button className="generate-weather-btn" onClick={generatePlaylist}>
      🎵 Generate Playlist Based on Weather
    </button>
  </div>
)}

    </div>
  );
}

export default App;
