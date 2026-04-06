import { useEffect, useMemo, useRef, useState } from "react";
import HistoryPanel from "./components/HistoryPanel";
import PlaylistCard from "./components/PlaylistCard";
import SharedPlaylistCard from "./components/SharedPlaylistCard";
import TrackPreviewCard from "./components/TrackPreviewCard";
import WeatherCard from "./components/WeatherCard";
import "./App.css";
import { usePlaylist } from "./hooks/usePlaylist";
import { useWeather } from "./hooks/useWeather";

const HISTORY_STORAGE_KEY = "skysync.history";
const MAX_HISTORY_ITEMS = 25;

const FORECAST_OPTIONS = [
  { value: "now", label: "Now" },
  { value: "tonight", label: "Tonight" },
  { value: "tomorrow_morning", label: "Tomorrow Morning" }
];

const DEFAULT_GENRE_OPTIONS = [
  "pop",
  "indie",
  "lofi",
  "rock",
  "hip hop",
  "electronic",
  "jazz",
  "r&b",
  "classical",
  "ambient",
  "house",
  "folk"
];

function loadHistoryFromStorage() {
  try {
    const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveHistoryToStorage(items) {
  try {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(items));
  } catch {
    // ignore localStorage write errors
  }
}

function encodeSharePayload(payload) {
  const json = JSON.stringify(payload);
  const bytes = new TextEncoder().encode(json);
  let binary = "";
  bytes.forEach((value) => {
    binary += String.fromCharCode(value);
  });
  return btoa(binary);
}

function decodeSharePayload(encoded) {
  const binary = atob(encoded);
  const bytes = Uint8Array.from(binary, (value) => value.charCodeAt(0));
  const json = new TextDecoder().decode(bytes);
  return JSON.parse(json);
}

function toForecastLabel(value) {
  const found = FORECAST_OPTIONS.find((option) => option.value === value);
  return found ? found.label : "Now";
}

function toLocationLabel(weather) {
  const location = weather?.location;
  if (!location) {
    return "Unknown Location";
  }
  return [location.name, location.admin1, location.country].filter(Boolean).join(", ");
}

function buildPreferencePayload(audioOverrides, options) {
  return {
    valence: audioOverrides.valence.enabled ? Number(audioOverrides.valence.value) : null,
    danceability: audioOverrides.danceability.enabled
      ? Number(audioOverrides.danceability.value)
      : null,
    energy: audioOverrides.energy.enabled ? Number(audioOverrides.energy.value) : null,
    genres: options.genres,
    exclude_explicit: options.excludeExplicit,
    personalize: options.personalize,
    auto_play: options.autoPlay
  };
}

function App() {
  const {
    weather,
    isLoading: isWeatherLoading,
    error: weatherError,
    backgroundImage,
    loadWeather,
    setWeatherSnapshot,
    locationResults,
    isSearchingLocations,
    locationError,
    searchLocations
  } = useWeather();

  const {
    playlist,
    isLoading: isPlaylistLoading,
    error: playlistError,
    availableGenres,
    runGeneration,
    regeneratePreview,
    createFromLatestPreview,
    clearPlaylist
  } = usePlaylist();

  const [locationQuery, setLocationQuery] = useState("Vancouver");
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [forecastMode, setForecastMode] = useState("now");
  const [uiMessage, setUiMessage] = useState("");
  const [shareUrl, setShareUrl] = useState("");
  const [sharedItem, setSharedItem] = useState(null);
  const [historyItems, setHistoryItems] = useState(loadHistoryFromStorage);

  const [audioOverrides, setAudioOverrides] = useState({
    valence: { enabled: false, value: 0.5 },
    danceability: { enabled: false, value: 0.5 },
    energy: { enabled: false, value: 0.5 }
  });

  const [playlistOptions, setPlaylistOptions] = useState({
    genres: [],
    excludeExplicit: false,
    personalize: true,
    autoPlay: false
  });

  const searchTimerRef = useRef(null);
  const lastSavedHistoryKeyRef = useRef("");

  const isBusy = isWeatherLoading || isPlaylistLoading;
  const locationLabel = toLocationLabel(weather);

  const genreChoices = useMemo(() => {
    const merged = [
      ...playlistOptions.genres,
      ...availableGenres.slice(0, 20),
      ...DEFAULT_GENRE_OPTIONS
    ];
    return [...new Set(merged)].slice(0, 20);
  }, [availableGenres, playlistOptions.genres]);

  useEffect(() => {
    document.body.style.backgroundImage = `url(${backgroundImage})`;
  }, [backgroundImage]);

  useEffect(() => {
    saveHistoryToStorage(historyItems);
  }, [historyItems]);

  useEffect(() => {
    const sharedParam = new URLSearchParams(window.location.search).get("shared");
    if (!sharedParam) {
      return;
    }
    try {
      const parsed = decodeSharePayload(sharedParam);
      setSharedItem(parsed);
    } catch {
      setSharedItem(null);
    }
  }, []);

  useEffect(() => {
    if (!playlist || playlist.action !== "create" || !playlist.link || !weather) {
      return;
    }

    const locationText = toLocationLabel(weather);
    const modeText = toForecastLabel(weather.forecast_mode);
    const key = `${playlist.link}|${playlist.title}|${weather.date}|${weather.time}`;
    if (key === lastSavedHistoryKeyRef.current) {
      return;
    }
    lastSavedHistoryKeyRef.current = key;

    const historyEntry = {
      id: key,
      title: playlist.title,
      link: playlist.link,
      whenLabel: new Date().toLocaleString(),
      locationLabel: locationText,
      modeLabel: modeText
    };

    setHistoryItems((current) => [historyEntry, ...current].slice(0, MAX_HISTORY_ITEMS));

    const sharePayload = {
      title: playlist.title,
      description: playlist.description,
      link: playlist.link,
      locationLabel: locationText,
      modeLabel: modeText
    };
    const encoded = encodeSharePayload(sharePayload);
    const nextShareUrl = `${window.location.origin}${window.location.pathname}?shared=${encodeURIComponent(
      encoded
    )}`;
    setShareUrl(nextShareUrl);
  }, [playlist, weather]);

  const resolveLocationPayload = () => {
    if (selectedLocation) {
      return selectedLocation;
    }

    const query = locationQuery.trim();
    if (!query) {
      return null;
    }

    return { query };
  };

  const handleLocationInput = (nextValue) => {
    setLocationQuery(nextValue);
    setSelectedLocation(null);
    setUiMessage("");

    if (searchTimerRef.current) {
      clearTimeout(searchTimerRef.current);
    }
    searchTimerRef.current = setTimeout(() => {
      searchLocations(nextValue);
    }, 260);
  };

  const handleSelectLocation = (location) => {
    setSelectedLocation(location);
    setLocationQuery(location.label || location.name || "");
    searchLocations("");
    setUiMessage("");
  };

  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      setUiMessage("Geolocation is not available in this browser.");
      return;
    }

    setUiMessage("Getting your current location...");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "auto";
        const location = {
          name: "Current Location",
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          timezone
        };
        setSelectedLocation(location);
        setLocationQuery("Current Location");
        searchLocations("");
        setUiMessage("Current location ready.");
      },
      (error) => {
        setUiMessage(`Unable to get current location (${error.code}).`);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
      }
    );
  };

  const handleLoadWeather = async (forceRefresh = false) => {
    const snapshot = await loadWeather({
      location: resolveLocationPayload(),
      forecastMode,
      forceRefresh
    });

    if (snapshot) {
      clearPlaylist();
      setShareUrl("");
      setUiMessage("Weather loaded. Tune your playlist settings and preview.");
    }
  };

  const handlePreviewPlaylist = async ({ regenerate = false } = {}) => {
    setShareUrl("");
    const preferencePayload = buildPreferencePayload(audioOverrides, playlistOptions);
    const generationResult = await runGeneration({
      location: resolveLocationPayload(),
      forecastMode,
      preferences: preferencePayload,
      action: "preview",
      regenerate,
      forceRefresh: false
    });

    if (generationResult?.weather) {
      setWeatherSnapshot(generationResult.weather);
    }
  };

  const handleRegeneratePreview = async () => {
    setShareUrl("");
    const result = await regeneratePreview();
    if (result?.weather) {
      setWeatherSnapshot(result.weather);
    }
  };

  const handleCreatePlaylist = async () => {
    const result = await createFromLatestPreview();
    if (result?.weather) {
      setWeatherSnapshot(result.weather);
    }
  };

  const toggleGenre = (genre) => {
    setPlaylistOptions((current) => {
      const exists = current.genres.includes(genre);
      return {
        ...current,
        genres: exists
          ? current.genres.filter((item) => item !== genre)
          : [...current.genres, genre]
      };
    });
  };

  const updateAudioOverrideEnabled = (field, enabled) => {
    setAudioOverrides((current) => ({
      ...current,
      [field]: {
        ...current[field],
        enabled
      }
    }));
  };

  const updateAudioOverrideValue = (field, value) => {
    setAudioOverrides((current) => ({
      ...current,
      [field]: {
        ...current[field],
        value: Number(value)
      }
    }));
  };

  const openPlaylistUrl = (url) => {
    if (!url) {
      return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const handleCopyShareUrl = async () => {
    if (!shareUrl) {
      return;
    }
    try {
      await navigator.clipboard.writeText(shareUrl);
      setUiMessage("Share link copied.");
    } catch {
      setUiMessage("Unable to copy share link.");
    }
  };

  return (
    <div className="app">
      <h1 className="initial-title">SkySync</h1>

      <SharedPlaylistCard sharedItem={sharedItem} />

      <div className="setup-grid">
        <div className="setup-bubble">
          <h2 className="bubble-subtitle">Weather Setup</h2>
          <label className="field-label" htmlFor="location-input">
            City Search
          </label>
          <input
            id="location-input"
            className="text-input"
            value={locationQuery}
            onChange={(event) => handleLocationInput(event.target.value)}
            placeholder="Type city name..."
          />

          <div className="small-button-row">
            <button type="button" className="tiny-link-btn" onClick={handleUseCurrentLocation}>
              Use Current Location
            </button>
            <button
              type="button"
              className="tiny-link-btn"
              onClick={() => handleLoadWeather(true)}
              disabled={isBusy}
            >
              Refresh Weather
            </button>
          </div>

          {isSearchingLocations && <p className="inline-note">Searching locations...</p>}
          {locationResults.length > 0 && (
            <ul className="suggestion-list">
              {locationResults.slice(0, 6).map((item) => (
                <li key={`${item.latitude}-${item.longitude}`}>
                  <button
                    type="button"
                    className="suggestion-btn"
                    onClick={() => handleSelectLocation(item)}
                  >
                    {item.label}
                  </button>
                </li>
              ))}
            </ul>
          )}

          <label className="field-label" htmlFor="forecast-mode">
            Forecast Mode
          </label>
          <select
            id="forecast-mode"
            className="text-input"
            value={forecastMode}
            onChange={(event) => setForecastMode(event.target.value)}
          >
            {FORECAST_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>

          <button
            className="load-weather-btn"
            onClick={() => handleLoadWeather(false)}
            disabled={isBusy}
            type="button"
          >
            {isWeatherLoading ? "Loading Weather..." : "Load Weather"}
          </button>

          {locationError && <p className="error-text">{locationError}</p>}
          {weatherError && (
            <div className="error-with-action">
              <p className="error-text">{weatherError}</p>
              <button
                type="button"
                className="tiny-link-btn"
                onClick={() => handleLoadWeather(true)}
              >
                Retry Weather
              </button>
            </div>
          )}
        </div>

        <div className="setup-bubble">
          <h2 className="bubble-subtitle">Playlist Controls</h2>
          <p className="inline-note">Override AI audio features if you want a specific vibe.</p>

          {[
            ["valence", "Mood (Valence)"],
            ["danceability", "Danceability"],
            ["energy", "Energy"]
          ].map(([fieldKey, label]) => (
            <div className="slider-group" key={fieldKey}>
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={audioOverrides[fieldKey].enabled}
                  onChange={(event) =>
                    updateAudioOverrideEnabled(fieldKey, event.target.checked)
                  }
                />
                {label}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                disabled={!audioOverrides[fieldKey].enabled}
                value={audioOverrides[fieldKey].value}
                onChange={(event) => updateAudioOverrideValue(fieldKey, event.target.value)}
              />
              <span className="slider-value">
                {audioOverrides[fieldKey].enabled
                  ? audioOverrides[fieldKey].value.toFixed(2)
                  : "AI"}
              </span>
            </div>
          ))}

          <p className="field-label">Genre Filters</p>
          <div className="genre-grid">
            {genreChoices.map((genre) => (
              <label key={genre} className="genre-chip">
                <input
                  type="checkbox"
                  checked={playlistOptions.genres.includes(genre)}
                  onChange={() => toggleGenre(genre)}
                />
                {genre}
              </label>
            ))}
          </div>

          <div className="toggle-grid">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={playlistOptions.excludeExplicit}
                onChange={(event) =>
                  setPlaylistOptions((current) => ({
                    ...current,
                    excludeExplicit: event.target.checked
                  }))
                }
              />
              Exclude Explicit
            </label>
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={playlistOptions.personalize}
                onChange={(event) =>
                  setPlaylistOptions((current) => ({
                    ...current,
                    personalize: event.target.checked
                  }))
                }
              />
              Personalize from Spotify
            </label>
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={playlistOptions.autoPlay}
                onChange={(event) =>
                  setPlaylistOptions((current) => ({
                    ...current,
                    autoPlay: event.target.checked
                  }))
                }
              />
              Auto-Play on Device
            </label>
          </div>

          <div className="action-row">
            <button
              className="spotify-generate-btn"
              onClick={() => handlePreviewPlaylist({ regenerate: false })}
              disabled={isBusy || !weather}
              type="button"
            >
              {isPlaylistLoading ? "Working..." : "Preview Playlist"}
            </button>
            <button
              className="tiny-link-btn"
              onClick={handleRegeneratePreview}
              disabled={isBusy || !playlist || playlist.action === "create"}
              type="button"
            >
              Regenerate
            </button>
            <button
              className="tiny-link-btn"
              onClick={handleCreatePlaylist}
              disabled={isBusy || !playlist}
              type="button"
            >
              Create Playlist
            </button>
          </div>

          {isPlaylistLoading && (
            <div className="loading-text">Building recommendations and syncing Spotify...</div>
          )}

          {playlistError && (
            <div className="error-with-action">
              <p className="error-text">{playlistError}</p>
              <button
                type="button"
                className="tiny-link-btn"
                onClick={() => handlePreviewPlaylist({ regenerate: true })}
              >
                Retry Playlist
              </button>
            </div>
          )}
        </div>
      </div>

      {uiMessage && <p className="inline-note">{uiMessage}</p>}

      {weather && (
        <div className="page-layout">
          <WeatherCard weather={weather} />
          {playlist ? (
            <PlaylistCard
              playlist={playlist}
              shareUrl={shareUrl}
              onCopyShareUrl={handleCopyShareUrl}
            />
          ) : (
            <div className="playlist-bubble">
              <h2 className="bubble-subtitle">Ready to Generate</h2>
              <p className="ready-text">
                Weather loaded for {locationLabel}. Adjust controls and click Preview Playlist.
              </p>
            </div>
          )}
        </div>
      )}

      {playlist?.previewTracks?.length > 0 && (
        <div className="preview-section">
          <TrackPreviewCard tracks={playlist.previewTracks} />
        </div>
      )}

      <div className="history-section">
        <HistoryPanel items={historyItems} onOpenPlaylist={openPlaylistUrl} />
      </div>
    </div>
  );
}

export default App;
