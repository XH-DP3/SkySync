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


// ======= WEATHER CATEGORY → IMAGE MAPPING (MUST BE ABOVE App()) =======
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


  // ======= SET MAIN SCREEN BACKGROUND =======
  if (!weather) {
    document.body.style.backgroundImage = `url(${mainBackground})`;
  }

  // ======= LOAD WEATHER FROM BACKEND =======
  async function loadWeather() {
    const res = await fetch("/api/weather_new");
    const data = await res.json();

    setWeather(data);

    // choose correct background
    const timeOfDay = data.is_day === 1 ? "day" : "night";
    const bgImage = weatherImages[data.category][timeOfDay];

    document.body.style.backgroundImage = `url(${bgImage})`;
  }

  async function generatePlaylist() {
    const res = await fetch("/api/make_playlist", { method: "POST" });
    const data = await res.json();
  
    if (data.status === "success") {
       setPlaylistGenerated(true);   // <-- This triggers the UI shift
    }
  }  


  return (
    <div className="app">
  
      {/* ============================
          MAIN SCREEN BEFORE WEATHER
      ============================== */}
      {!weather && (
        <div className="main-screen">
          <h1 className="initial-title">SkySync</h1>
  
          <button id="loadBtn" onClick={loadWeather}>
            Load Weather
          </button>
        </div>
      )}
  
      {/* ====================================
           AFTER LOADING WEATHER → FLEX LAYOUT
      ===================================== */}
      {weather && (
        <div className={`page-layout ${playlistGenerated ? "shifted" : ""}`}>
  
          {/* -------- LEFT: WEATHER BUBBLE -------- */}
          <div className="weather-bubble">
            <h1 className="bubble-title">Current Weather</h1>
  
            <p>📅 Date: {weather.date}</p>
            <p>🕒 Time: {weather.time}</p>
            <p>🌡 Temperature: {weather.temperature}°C</p>
            <p>⛅ Condition: {weather.condition}</p>
            <p>🌅 Sunrise: {weather.sunrise}</p>
            <p>🌇 Sunset: {weather.sunset}</p>
          </div>
  
          {/* -------- RIGHT: PLAYLIST BUBBLE (only after Generate) -------- */}
          {playlistGenerated && (
            <div className="playlist-bubble">
              <h1 className="bubble-title">Playlist Ready</h1>
              <p>Your personalized playlist is generated!</p>
              <p>Open it directly in Spotify.</p>
  
              <button className="spotify-open-btn">
                Open Playlist
              </button>
            </div>
          )}
  
        </div>
      )}
  
      {/* ========================================
          SPOTIFY INPUT (below weather bubble)
      ========================================= */}
      {weather && !playlistGenerated && (
        <div className="spotify-section">
          <input
            type="text"
            className="spotify-input"
            placeholder="Paste your Spotify link..."
            value={spotifyLink}
            onChange={(e) => setSpotifyLink(e.target.value)}
          />
  
          <button
            className="spotify-generate-btn"
            onClick={() => setPlaylistGenerated(true)}
          >
            Generate
          </button>
        </div>
      )}
  
    </div>
  );
  
}

export default App;