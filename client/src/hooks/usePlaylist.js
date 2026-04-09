import { useEffect, useMemo, useState } from "react";

const PLAYLIST_STORAGE_KEY = "skysync.playlistState";

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
    sourceSummary: data.source_summary ?? "",
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

function buildPreviewSnapshot(playlist) {
  if (!playlist) {
    return null;
  }

  return {
    title: playlist.title ?? "",
    description: playlist.description ?? "",
    trackIds: Array.isArray(playlist.previewTracks)
      ? playlist.previewTracks.map((track) => track.id).filter(Boolean)
      : []
  };
}

function loadPlaylistState() {
  try {
    const raw = sessionStorage.getItem(PLAYLIST_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function savePlaylistState(payload) {
  try {
    sessionStorage.setItem(PLAYLIST_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // ignore sessionStorage write errors
  }
}

export function usePlaylist() {
  const persistedState = loadPlaylistState();
  const [playlist, setPlaylist] = useState(persistedState?.playlist ?? null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastRequest, setLastRequest] = useState(persistedState?.lastRequest ?? null);

  useEffect(() => {
    savePlaylistState({
      playlist,
      lastRequest
    });
  }, [lastRequest, playlist]);

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
    previewTitle = "",
    previewDescription = "",
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
        preview_title: previewTitle,
        preview_description: previewDescription,
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
      const previewIds = normalized.previewTracks.map((track) => track.id).filter(Boolean);
      setPlaylist(normalized);
      setLastRequest({
        location,
        forecastMode,
        preferences,
        previewTrackIds: previewIds
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

    const previewSnapshot = buildPreviewSnapshot(playlist);

    return runGeneration({
      location: lastRequest.location,
      forecastMode: lastRequest.forecastMode,
      preferences: lastRequest.preferences,
      action: "create",
      regenerate: false,
      previewTrackIds: previewSnapshot?.trackIds ?? [],
      previewTitle: previewSnapshot?.title ?? "",
      previewDescription: previewSnapshot?.description ?? "",
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
