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
const SETUP_STORAGE_KEY = "skysync.setup";
const SPOTIFY_AUTO_CONNECT_KEY = "skysync.spotifyAutoConnect";
const PENDING_CREATE_KEY = "skysync.pendingCreate";
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

function loadSetupFromStorage() {
  try {
    const raw = sessionStorage.getItem(SETUP_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveSetupToStorage(payload) {
  try {
    sessionStorage.setItem(SETUP_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // ignore sessionStorage write errors
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
  const [spotifyAuth, setSpotifyAuth] = useState({
    isLoading: true,
    connected: false,
    user: null
  });

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
  const canUseSpotifyAccountFeatures = spotifyAuth.connected;

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
    const restoredSetup = loadSetupFromStorage();
    const sharedParam = new URLSearchParams(window.location.search).get("shared");
    const spotifyParam = new URLSearchParams(window.location.search).get("spotify");

    if (restoredSetup) {
      if (typeof restoredSetup.locationQuery === "string") {
        setLocationQuery(restoredSetup.locationQuery);
      }
      if (restoredSetup.selectedLocation) {
        setSelectedLocation(restoredSetup.selectedLocation);
      }
      if (typeof restoredSetup.forecastMode === "string") {
        setForecastMode(restoredSetup.forecastMode);
      }
      if (restoredSetup.weather) {
        setWeatherSnapshot(restoredSetup.weather);
      }
      if (restoredSetup.audioOverrides) {
        setAudioOverrides(restoredSetup.audioOverrides);
      }
      if (restoredSetup.playlistOptions) {
        setPlaylistOptions(restoredSetup.playlistOptions);
      }
    }

    if (!sharedParam) {
      setSharedItem(null);
    } else {
      try {
        const parsed = decodeSharePayload(sharedParam);
        setSharedItem(parsed);
      } catch {
        setSharedItem(null);
      }
    }

    if (spotifyParam === "connected") {
      setUiMessage("Spotify connected. Account-specific features are ready.");
    } else if (spotifyParam === "error") {
      setUiMessage("Spotify connection failed. Please try again.");
    } else if (spotifyParam === "missing_code") {
      setUiMessage("Spotify did not return an authorization code.");
    }

    if (spotifyParam) {
      const nextUrl = new URL(window.location.href);
      nextUrl.searchParams.delete("spotify");
      window.history.replaceState({}, "", nextUrl.toString());
    }
  }, []);

  useEffect(() => {
    saveSetupToStorage({
      locationQuery,
      selectedLocation,
      forecastMode,
      weather,
      audioOverrides,
      playlistOptions
    });
  }, [
    audioOverrides,
    forecastMode,
    locationQuery,
    playlistOptions,
    selectedLocation,
    weather
  ]);

  useEffect(() => {
    let ignore = false;

    const loadSpotifyStatus = async () => {
      try {
        const response = await fetch("/api/spotify/status");
        const data = await response.json();
        if (ignore) {
          return;
        }

        setSpotifyAuth({
          isLoading: false,
          connected: Boolean(data.connected),
          user: data.user ?? null
        });

        const spotifyParam = new URLSearchParams(window.location.search).get("spotify");
        const hasAutoConnected = sessionStorage.getItem(SPOTIFY_AUTO_CONNECT_KEY) === "done";
        if (!data.connected && !spotifyParam && !hasAutoConnected) {
          sessionStorage.setItem(SPOTIFY_AUTO_CONNECT_KEY, "done");
          setTimeout(() => {
            handleConnectSpotify({ silent: true });
          }, 120);
        }
      } catch {
        if (!ignore) {
          setSpotifyAuth({
            isLoading: false,
            connected: false,
            user: null
          });
        }
      }
    };

    loadSpotifyStatus();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    const pendingCreate = sessionStorage.getItem(PENDING_CREATE_KEY) === "true";
    if (!spotifyAuth.connected || !playlist || !pendingCreate || isPlaylistLoading) {
      return;
    }

    sessionStorage.removeItem(PENDING_CREATE_KEY);
    handleCreatePlaylist();
  }, [isPlaylistLoading, playlist, spotifyAuth.connected]);

  useEffect(() => {
    if (canUseSpotifyAccountFeatures) {
      return;
    }

    setPlaylistOptions((current) => {
      if (!current.personalize && !current.autoPlay) {
        return current;
      }

      return {
        ...current,
        personalize: false,
        autoPlay: false
      };
    });
  }, [canUseSpotifyAccountFeatures]);

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
    if (!canUseSpotifyAccountFeatures) {
      sessionStorage.setItem(PENDING_CREATE_KEY, "true");
      setUiMessage("Connect Spotify to save this playlist to your account.");
      handleConnectSpotify();
      return;
    }

    sessionStorage.removeItem(PENDING_CREATE_KEY);
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

  const handleConnectSpotify = async ({ silent = false } = {}) => {
    if (!silent) {
      setUiMessage("Opening Spotify sign-in...");
    }

    try {
      const response = await fetch("/api/spotify/auth-url");
      const data = await response.json();
      if (!response.ok || data.status === "error" || !data.authorize_url) {
        throw new Error(data?.message ?? "Unable to start Spotify login.");
      }
      window.location.href = data.authorize_url;
    } catch (error) {
      setUiMessage(error instanceof Error ? error.message : "Unable to start Spotify login.");
    }
  };

  const handleDisconnectSpotify = async () => {
    try {
      await fetch("/api/spotify/logout", {
        method: "POST"
      });
    } finally {
      setSpotifyAuth({
        isLoading: false,
        connected: false,
        user: null
      });
      setPlaylistOptions((current) => ({
        ...current,
        personalize: false,
        autoPlay: false
      }));
      setUiMessage("Spotify disconnected.");
    }
  };

  return (
    <div className="app">
      <h1 className="initial-title">SkySync</h1>

      <SharedPlaylistCard sharedItem={sharedItem} />

      <div className="setup-grid">
        <div className="setup-bubble">
          <h2 className="bubble-subtitle">Weather Setup</h2>
          <div className="control-surface">
            <p className="section-kicker">Inputs</p>
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
          </div>

          <div className="button-surface">
            <p className="section-kicker">Actions</p>
            <div className="small-button-row">
              <button type="button" className="tiny-link-btn action-btn" onClick={handleUseCurrentLocation}>
                Use Current Location
              </button>
              <button
                type="button"
                className="tiny-link-btn action-btn"
                onClick={() => handleLoadWeather(true)}
                disabled={isBusy}
              >
                Refresh Weather
              </button>
              <button
                className="load-weather-btn action-btn"
                onClick={() => handleLoadWeather(false)}
                disabled={isBusy}
                type="button"
              >
                {isWeatherLoading ? "Loading Weather..." : "Load Weather"}
              </button>
            </div>
          </div>

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
          <div className="error-with-action">
            <p className="inline-note">
              {spotifyAuth.isLoading
                ? "Checking Spotify connection..."
                : spotifyAuth.connected
                  ? `Connected as ${spotifyAuth.user?.display_name ?? "Spotify User"}.`
                  : "Preview works without Spotify login. Connect Spotify to personalize, auto-play, or create playlists in your own account."}
            </p>
            {spotifyAuth.connected ? (
              <button
                type="button"
                className="tiny-link-btn action-btn"
                onClick={handleDisconnectSpotify}
                disabled={isBusy}
              >
                Disconnect Spotify
              </button>
            ) : (
              <button
                type="button"
                className="tiny-link-btn action-btn"
                onClick={handleConnectSpotify}
                disabled={isBusy || spotifyAuth.isLoading}
              >
                Connect Spotify
              </button>
            )}
          </div>

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
                disabled={!canUseSpotifyAccountFeatures}
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
                disabled={!canUseSpotifyAccountFeatures}
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
