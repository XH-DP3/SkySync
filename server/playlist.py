import random
import time

from spotipy.exceptions import SpotifyException

from openaiService import (
    apply_audio_overrides,
    expand_genre_queries,
    getSongParams,
    makedescription,
    maketitle,
    to_audio_feature_dict,
    to_audio_features
)
from reccobeats_util import get_audio_features_for_track_ids
from spotifystuff import (
    DEFAULT_SEED_PLAYLIST_ID,
    enrich_catalog_with_genres,
    get_genre_counts_for_catalog,
    get_spotify_client,
    get_track_catalog,
    get_user_taste_profile,
    search_tracks_for_genres
)

MAX_TRACKS_PER_PLAYLIST = 50
PREVIEW_TRACK_COUNT = 10
MIN_FILTERED_TRACKS = 10


def _normalize_genres(genres):
    normalized = []
    for genre in genres or []:
        cleaned = str(genre).strip().lower()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _resolve_preferences(preferences=None):
    preferences = preferences or {}
    return {
        "energy": preferences.get("energy"),
        "danceability": preferences.get("danceability"),
        "valence": preferences.get("valence"),
        "genres": _normalize_genres(preferences.get("genres", [])),
        "exclude_explicit": bool(preferences.get("exclude_explicit", False)),
        "personalize": bool(preferences.get("personalize", False)),
        "auto_play": bool(preferences.get("auto_play", False))
    }


def _load_source_catalog(seed_playlist_id, force_refresh=False):
    base_catalog = get_track_catalog(seed_playlist_id, force_refresh=force_refresh)
    return (
        base_catalog,
        {
            "type": "seed_playlist",
            "label": "Picked from the shared discovery catalog."
        },
        []
    )


def _build_catalog_with_features(seed_playlist_id, force_refresh=False):
    base_catalog, source_info, source_warnings = _load_source_catalog(
        seed_playlist_id,
        force_refresh=force_refresh
    )
    combined = _enrich_catalog_for_ranking(base_catalog, force_refresh=force_refresh)

    return combined, source_info, source_warnings


def _enrich_catalog_for_ranking(catalog, force_refresh=False):
    catalog_with_genres = enrich_catalog_with_genres(catalog)
    track_ids = [track["id"] for track in catalog_with_genres if track.get("id")]
    features_map = get_audio_features_for_track_ids(track_ids, force_refresh=force_refresh)

    combined = []
    for track in catalog_with_genres:
        feature = features_map.get(track["id"])
        if not feature:
            continue

        merged = dict(track)
        merged["audio_features"] = {
            "valence": feature.get("valence") or 0.0,
            "danceability": feature.get("danceability") or 0.0,
            "energy": feature.get("energy") or 0.0
        }
        combined.append(merged)

    return combined


def _matches_genres(track, selected_genres):
    if not selected_genres:
        return True

    track_genres = [genre.lower() for genre in track.get("genres", [])]
    for selected in selected_genres:
        for genre in track_genres:
            if selected in genre:
                return True
    return False


def _apply_hard_filters(catalog, preferences):
    selected_genres = preferences["genres"]
    exclude_explicit = preferences["exclude_explicit"]

    filtered = []
    for track in catalog:
        if exclude_explicit and track.get("explicit"):
            continue
        if not _matches_genres(track, selected_genres):
            continue
        filtered.append(track)

    return filtered


def _dedupe_catalog_tracks(*catalogs):
    deduped = {}
    for catalog in catalogs:
        for track in catalog or []:
            track_id = track.get("id")
            if track_id and track_id not in deduped:
                deduped[track_id] = track
    return list(deduped.values())


def _fill_minimum_tracks(filtered_catalog, fallback_catalog, minimum_count):
    if len(filtered_catalog) >= minimum_count:
        return filtered_catalog, False

    existing_ids = {track.get("id") for track in filtered_catalog if track.get("id")}
    expanded_catalog = list(filtered_catalog)

    for track in fallback_catalog:
        track_id = track.get("id")
        if not track_id or track_id in existing_ids:
            continue
        expanded_catalog.append(track)
        existing_ids.add(track_id)
        if len(expanded_catalog) >= minimum_count:
            return expanded_catalog, True

    return expanded_catalog, len(expanded_catalog) > len(filtered_catalog)


def _supplement_catalog_for_genres(filtered_catalog, preferences, force_refresh=False):
    selected_genres = preferences["genres"]
    if not selected_genres or len(filtered_catalog) >= MIN_FILTERED_TRACKS:
        return filtered_catalog, []

    warnings = []
    search_genres = list(selected_genres)
    related_genres = expand_genre_queries(selected_genres)
    for genre in related_genres:
        if genre not in search_genres:
            search_genres.append(genre)

    supplemental_catalog = search_tracks_for_genres(search_genres, limit_per_genre=12)
    if not supplemental_catalog:
        return filtered_catalog, warnings

    supplemental_catalog = _enrich_catalog_for_ranking(
        supplemental_catalog,
        force_refresh=force_refresh
    )
    supplemental_preferences = dict(preferences)
    supplemental_preferences["genres"] = search_genres
    supplemental_catalog = _apply_hard_filters(supplemental_catalog, supplemental_preferences)
    merged_catalog = _dedupe_catalog_tracks(filtered_catalog, supplemental_catalog)

    if len(merged_catalog) > len(filtered_catalog):
        warnings.append(
            "Added extra tracks from Spotify search to fill the requested genre selection."
        )

    if related_genres:
        warnings.append(
            f"Expanded genre matching with related styles: {', '.join(related_genres[:3])}."
        )

    return merged_catalog, warnings


def _score_track(track, target_features, preferences, taste_profile):
    audio = track["audio_features"]
    valence_diff = abs(audio["valence"] - target_features.valence)
    danceability_diff = abs(audio["danceability"] - target_features.danceability)
    energy_diff = abs(audio["energy"] - target_features.energy)

    feature_score = 1.0 - (
        0.42 * valence_diff +
        0.29 * danceability_diff +
        0.29 * energy_diff
    )

    score = max(0.0, feature_score)

    if preferences["genres"] and _matches_genres(track, preferences["genres"]):
        score += 0.06

    popularity = float(track.get("popularity") or 0)
    score += min(0.08, popularity / 1000.0)

    if preferences["personalize"] and taste_profile:
        track_id = track.get("id")
        artist_ids = set(track.get("artist_ids", []))
        top_tracks = set(taste_profile.get("top_track_ids", []))
        top_artists = set(taste_profile.get("top_artist_ids", []))

        if track_id in top_tracks:
            score += 0.22

        if artist_ids.intersection(top_artists):
            score += 0.14

    return score


def _rank_tracks(catalog, target_features, preferences, taste_profile, regenerate=False):
    ranked = []
    for track in catalog:
        score = _score_track(track, target_features, preferences, taste_profile)
        ranked.append((score, track))

    ranked.sort(key=lambda item: item[0], reverse=True)
    ranked_tracks = [track for _, track in ranked]

    if regenerate and ranked_tracks:
        seed = int(time.time() * 1000)
        rng = random.Random(seed)
        top_window = ranked_tracks[: max(MAX_TRACKS_PER_PLAYLIST * 3, 80)]
        rng.shuffle(top_window)
        ranked_tracks = top_window + ranked_tracks[len(top_window):]

    return ranked_tracks


def _as_preview_track(track):
    return {
        "id": track.get("id"),
        "name": track.get("name"),
        "artists": track.get("artist_names", []),
        "album": track.get("album_name", ""),
        "explicit": bool(track.get("explicit", False)),
        "genres": track.get("genres", []),
        "spotify_url": track.get("spotify_url", ""),
        "image_url": track.get("image_url", "")
    }


def _pick_track_ids_for_playlist(ranked_tracks, preview_track_ids=None):
    id_to_track = {track["id"]: track for track in ranked_tracks if track.get("id")}

    selected_ids = []
    for track_id in preview_track_ids or []:
        if track_id in id_to_track and track_id not in selected_ids:
            selected_ids.append(track_id)

    if selected_ids:
        return selected_ids[:MAX_TRACKS_PER_PLAYLIST]

    for track in ranked_tracks:
        track_id = track.get("id")
        if not track_id or track_id in selected_ids:
            continue

        selected_ids.append(track_id)
        if len(selected_ids) >= MAX_TRACKS_PER_PLAYLIST:
            break

    return selected_ids[:MAX_TRACKS_PER_PLAYLIST]


def _preview_tracks_from_ids(ranked_tracks, preview_track_ids=None):
    if not preview_track_ids:
        return None

    id_to_track = {track["id"]: track for track in ranked_tracks if track.get("id")}
    preview_tracks = []
    for track_id in preview_track_ids:
        track = id_to_track.get(track_id)
        if track:
            preview_tracks.append(_as_preview_track(track))

    return preview_tracks or None


def playback(playlist_id):
    spotify_client = get_spotify_client(user_required=True)
    try:
        devices = spotify_client.devices().get("devices", [])
        if not devices:
            return False

        device_id = devices[0]["id"]
        playlist_uri = f"spotify:playlist:{playlist_id}"
        spotify_client.start_playback(device_id=device_id, context_uri=playlist_uri)
        return True
    except SpotifyException:
        return False


def _create_playlist_on_spotify(track_ids, playlist_name, auto_play=False):
    if not track_ids:
        raise RuntimeError("No tracks selected for playlist creation.")

    spotify_client = get_spotify_client(user_required=True)
    user = spotify_client.current_user()

    new_playlist = spotify_client.user_playlist_create(
        user["id"],
        playlist_name,
        public=False
    )

    playlist_id = new_playlist["id"]
    track_uris = [f"spotify:track:{track_id}" for track_id in track_ids]
    spotify_client.playlist_add_items(playlist_id, track_uris)

    if auto_play:
        playback(playlist_id)

    spotify_link = ((new_playlist.get("external_urls") or {}).get("spotify") or "").strip()
    if spotify_link:
        return spotify_link

    return f"https://open.spotify.com/playlist/{playlist_id}"


def generate_playlist_bundle(
    weather_state,
    preferences=None,
    action="preview",
    regenerate=False,
    preview_track_ids=None,
    preview_title=None,
    preview_description=None,
    seed_playlist_id=None,
    force_refresh=False
):
    resolved_preferences = _resolve_preferences(preferences)
    resolved_action = action if action in {"preview", "create"} else "preview"
    resolved_seed_playlist_id = seed_playlist_id or DEFAULT_SEED_PLAYLIST_ID

    base_song_params = getSongParams(weather_state)
    song_params = apply_audio_overrides(base_song_params, resolved_preferences)
    resolved_song_params = to_audio_features(song_params)

    catalog, source_info, source_warnings = _build_catalog_with_features(
        resolved_seed_playlist_id,
        force_refresh=force_refresh
    )

    if not catalog:
        raise RuntimeError("No track catalog available. Check your Spotify seed playlist.")

    filtered_catalog = _apply_hard_filters(catalog, resolved_preferences)
    warnings = list(source_warnings)

    supplemented_catalog, supplement_warnings = _supplement_catalog_for_genres(
        filtered_catalog,
        resolved_preferences,
        force_refresh=force_refresh
    )
    filtered_catalog = supplemented_catalog
    warnings.extend(supplement_warnings)

    if not filtered_catalog:
        filtered_catalog = catalog
        warnings.append("No tracks matched all filters. Showing best matches from full catalog.")
    elif len(filtered_catalog) < MIN_FILTERED_TRACKS:
        filtered_catalog, relaxed_filters = _fill_minimum_tracks(
            filtered_catalog,
            catalog,
            MIN_FILTERED_TRACKS
        )
        if relaxed_filters:
            warnings.append(
                "Not enough genre matches were available, so additional best-fit tracks were added to reach 10 songs."
            )

    taste_profile = None
    if resolved_preferences["personalize"]:
        taste_profile = get_user_taste_profile()

    ranked_tracks = _rank_tracks(
        filtered_catalog,
        resolved_song_params,
        resolved_preferences,
        taste_profile,
        regenerate=regenerate
    )

    if not ranked_tracks:
        raise RuntimeError("Unable to rank tracks for playlist generation.")

    preview_tracks = _preview_tracks_from_ids(ranked_tracks, preview_track_ids=preview_track_ids)
    if preview_tracks is None:
        preview_tracks = [_as_preview_track(track) for track in ranked_tracks[:PREVIEW_TRACK_COUNT]]
    chosen_track_ids = _pick_track_ids_for_playlist(ranked_tracks, preview_track_ids=preview_track_ids)

    title = (preview_title or "").strip()
    if not title:
        title = maketitle(resolved_song_params, weather_state, options=resolved_preferences)

    description = (preview_description or "").strip()
    if not description:
        description = makedescription(resolved_song_params, weather_state, options=resolved_preferences)

    playlist_link = ""
    if resolved_action == "create":
        playlist_link = _create_playlist_on_spotify(
            chosen_track_ids,
            title,
            auto_play=resolved_preferences["auto_play"]
        )

    available_genres = list(get_genre_counts_for_catalog(catalog).keys())[:40]

    return {
        "status": "ok",
        "action": resolved_action,
        "title": title,
        "description": description,
        "link": playlist_link,
        "song_params": to_audio_feature_dict(resolved_song_params),
        "preview_tracks": preview_tracks,
        "selected_track_ids": chosen_track_ids,
        "preferences": resolved_preferences,
        "available_genres": available_genres,
        "source_summary": source_info["label"],
        "warnings": warnings
    }


def make_new_playlist(weather_state, song_params=None, auto_play=False):
    # Backward-compatible wrapper used by older endpoints.
    preferences = {
        "auto_play": auto_play,
        "energy": getattr(song_params, "energy", None) if song_params else None,
        "danceability": getattr(song_params, "danceability", None) if song_params else None,
        "valence": getattr(song_params, "valence", None) if song_params else None
    }

    payload = generate_playlist_bundle(
        weather_state=weather_state,
        preferences=preferences,
        action="create"
    )
    return payload["link"], payload["title"]
