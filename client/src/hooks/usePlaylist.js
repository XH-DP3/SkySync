import { useMemo, useState } from "react";

function getErrorMessage(error, fallbackMessage) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallbackMessage;
}

function normalizePlaylistPayload(data) {
  return {
    title: data.title ?? "SkySync Mix",
    description: data.description ?? "",
    link: data.link ?? "",
    action: data.action ?? "preview",
    previewTracks: Array.isArray(data.preview_tracks) ? data.preview_tracks : [],
    selectedTrackIds: Array.isArray(data.selected_track_ids)
      ? data.selected_track_ids
      : [],
    songParams: data.song_params ?? null,
    warnings: Array.isArray(data.warnings) ? data.warnings : [],
    availableGenres: Array.isArray(data.available_genres) ? data.available_genres : []
  };
}

export function usePlaylist() {
  const [playlist, setPlaylist] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastRequest, setLastRequest] = useState(null);

  const availableGenres = useMemo(() => {
    if (!playlist) {
      return [];
    }
    return playlist.availableGenres;
  }, [playlist]);

  const runGeneration = async ({
    location = null,
    forecastMode = "now",
    preferences = {},
    action = "preview",
    regenerate = false,
    previewTrackIds = [],
    forceRefresh = false
  } = {}) => {
    setIsLoading(true);
    setError("");

    try {
      const requestPayload = {
        location,
        forecast_mode: forecastMode,
        preferences,
        action,
        regenerate,
        preview_track_ids: previewTrackIds,
        force_refresh: forceRefresh
      };

      const response = await fetch("/api/playlists/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(requestPayload)
      });

      const data = await response.json();
      if (!response.ok || data.status === "error") {
        throw new Error(
          data?.message ?? data?.error ?? `Playlist request failed (${response.status})`
        );
      }

      const normalized = normalizePlaylistPayload(data);
      setPlaylist(normalized);
      setLastRequest({
        location,
        forecastMode,
        preferences,
        previewTrackIds: normalized.selectedTrackIds
      });

      return {
        playlist: normalized,
        weather: data.weather ?? null
      };
    } catch (runError) {
      setPlaylist(null);
      setError(getErrorMessage(runError, "Unable to generate playlist."));
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const regeneratePreview = async () => {
    if (!lastRequest) {
      return null;
    }

    return runGeneration({
      location: lastRequest.location,
      forecastMode: lastRequest.forecastMode,
      preferences: lastRequest.preferences,
      action: "preview",
      regenerate: true,
      previewTrackIds: [],
      forceRefresh: false
    });
  };

  const createFromLatestPreview = async () => {
    if (!lastRequest || !playlist) {
      return null;
    }

    return runGeneration({
      location: lastRequest.location,
      forecastMode: lastRequest.forecastMode,
      preferences: lastRequest.preferences,
      action: "create",
      regenerate: false,
      previewTrackIds: playlist.selectedTrackIds,
      forceRefresh: false
    });
  };

  const clearPlaylist = () => {
    setPlaylist(null);
    setError("");
    setLastRequest(null);
  };

  return {
    playlist,
    isLoading,
    error,
    availableGenres,
    runGeneration,
    regeneratePreview,
    createFromLatestPreview,
    clearPlaylist
  };
}
