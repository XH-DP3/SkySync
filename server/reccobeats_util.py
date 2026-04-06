import time

import requests

from spotifystuff import DEFAULT_SEED_PLAYLIST_ID, get_all_track_ids

RECCOBEATS_AUDIO_FEATURES_URL = "https://api.reccobeats.com/v1/audio-features"
RECCOBEATS_BATCH_SIZE = 40
REQUEST_TIMEOUT_SECONDS = 15
AUDIO_FEATURES_CACHE_TTL_SECONDS = 60 * 30

_audio_features_cache = {}


def _chunk(values, chunk_size):
    for index in range(0, len(values), chunk_size):
        yield values[index:index + chunk_size]


def _is_cache_valid(cache_entry):
    if not cache_entry:
        return False
    return (time.time() - cache_entry["timestamp"]) < AUDIO_FEATURES_CACHE_TTL_SECONDS


def _fetch_audio_features(track_ids):
    features_map = {}

    for chunk in _chunk(track_ids, RECCOBEATS_BATCH_SIZE):
        response = requests.get(
            RECCOBEATS_AUDIO_FEATURES_URL,
            headers={"Accept": "application/json"},
            params={"ids": ",".join(chunk)},
            timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        payload = response.json()
        content = payload.get("content", [])

        for original_id, feature in zip(chunk, content):
            features_map[original_id] = {
                "ori_id": original_id,
                "id": feature.get("id"),
                "valence": feature.get("valence"),
                "danceability": feature.get("danceability"),
                "energy": feature.get("energy")
            }

    return features_map


def get_audio_features_for_track_ids(track_ids, force_refresh=False):
    normalized_ids = [track_id for track_id in track_ids if track_id]
    if not normalized_ids:
        return {}

    missing_ids = []
    for track_id in normalized_ids:
        cache_entry = _audio_features_cache.get(track_id)
        if force_refresh or not _is_cache_valid(cache_entry):
            missing_ids.append(track_id)

    if missing_ids:
        fetched_map = _fetch_audio_features(missing_ids)
        now = time.time()
        for track_id, feature in fetched_map.items():
            _audio_features_cache[track_id] = {
                "timestamp": now,
                "feature": feature
            }

    result = {}
    for track_id in normalized_ids:
        cache_entry = _audio_features_cache.get(track_id)
        if cache_entry and cache_entry.get("feature"):
            result[track_id] = dict(cache_entry["feature"])

    return result


def get_all_audio_features(force_refresh=False, track_ids=None):
    resolved_track_ids = track_ids or get_all_track_ids(DEFAULT_SEED_PLAYLIST_ID)
    features_map = get_audio_features_for_track_ids(
        resolved_track_ids,
        force_refresh=force_refresh
    )
    return [features_map[track_id] for track_id in resolved_track_ids if track_id in features_map]


def in_range_float(min_value, max_value, value):
    if value is None:
        return False
    return min_value <= value <= max_value


def filter_tracks_by_audio_ft(values, track_ids=None):
    valence = getattr(values, "valence", None)
    danceability = getattr(values, "danceability", None)
    energy = getattr(values, "energy", None)
    if valence is None or danceability is None or energy is None:
        return []

    features = get_all_audio_features(track_ids=track_ids)
    return [
        track
        for track in features
        if (
            in_range_float(valence - 0.1, valence + 0.1, track["valence"])
            and in_range_float(
                danceability - 0.2, danceability + 0.2, track["danceability"]
            )
            and in_range_float(energy - 0.5, energy + 0.5, track["energy"])
        )
    ]
