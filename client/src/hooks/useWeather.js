import { useMemo, useState } from "react";
import {
  MAIN_BACKGROUND,
  getWeatherBackground
} from "../constants/weatherBackgrounds";

function getErrorMessage(error, fallbackMessage) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallbackMessage;
}

export function useWeather() {
  const [weather, setWeather] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const [locationResults, setLocationResults] = useState([]);
  const [isSearchingLocations, setIsSearchingLocations] = useState(false);
  const [locationError, setLocationError] = useState("");

  const backgroundImage = useMemo(() => {
    if (!weather) {
      return MAIN_BACKGROUND;
    }
    return getWeatherBackground(weather.category, weather.is_day);
  }, [weather]);

  const searchLocations = async (query) => {
    const trimmed = (query || "").trim();
    if (trimmed.length < 2) {
      setLocationResults([]);
      setLocationError("");
      return [];
    }

    setIsSearchingLocations(true);
    setLocationError("");

    try {
      const response = await fetch(
        `/api/locations/search?q=${encodeURIComponent(trimmed)}`
      );
      const data = await response.json();

      if (!response.ok || data.status === "error") {
        throw new Error(data?.message ?? `Location search failed (${response.status})`);
      }

      const results = Array.isArray(data.results) ? data.results : [];
      setLocationResults(results);
      return results;
    } catch (searchError) {
      setLocationResults([]);
      setLocationError(getErrorMessage(searchError, "Unable to search locations."));
      return [];
    } finally {
      setIsSearchingLocations(false);
    }
  };

  const loadWeather = async ({ location = null, forecastMode = "now", forceRefresh = false } = {}) => {
    setIsLoading(true);
    setError("");

    try {
      const response = await fetch("/api/weather", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          location,
          forecast_mode: forecastMode,
          force_refresh: forceRefresh
        })
      });

      const data = await response.json();
      if (!response.ok || data.status === "error") {
        throw new Error(data?.message ?? `Weather request failed (${response.status})`);
      }

      const snapshot = data.weather;
      setWeather(snapshot);
      return snapshot;
    } catch (loadError) {
      setWeather(null);
      setError(getErrorMessage(loadError, "Unable to load weather."));
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const clearWeather = () => {
    setWeather(null);
    setError("");
  };

  const setWeatherSnapshot = (snapshot) => {
    setWeather(snapshot);
  };

  return {
    weather,
    isLoading,
    error,
    backgroundImage,
    loadWeather,
    setWeatherSnapshot,
    clearWeather,
    locationResults,
    isSearchingLocations,
    locationError,
    searchLocations
  };
}
