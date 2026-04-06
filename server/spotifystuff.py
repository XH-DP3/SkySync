import os
import time
from collections import defaultdict

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_SCOPE = (
    "user-top-read playlist-read-private user-read-private "
    "playlist-modify-public playlist-modify-private "
    "user-modify-playback-state user-read-playback-state"
)
SPOTIFY_CACHE_PATH = ".cache"
DEFAULT_SEED_PLAYLIST_ID = os.getenv("SPOTIFY_SEED_PLAYLIST_ID", "4k4kTCxwnV9sgE0whd3Gg2")
CATALOG_CACHE_TTL_SECONDS = 60 * 15
PROFILE_CACHE_TTL_SECONDS = 60 * 5

_spotify_client = None
_playlist_catalog_cache = {}
_artist_genres_cache = {}
_user_profile_cache = None


def _get_now():
    return time.time()


def _is_cache_valid(entry, ttl_seconds):
    if not entry:
        return False
    return (_get_now() - entry["timestamp"]) < ttl_seconds


def get_spotify_client():
    global _spotify_client
    if _spotify_client is not None:
        return _spotify_client

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET.")

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE,
        cache_path=SPOTIFY_CACHE_PATH
    )
    _spotify_client = spotipy.Spotify(auth_manager=auth_manager)
    return _spotify_client


def get_all_track_ids(playlist_id=DEFAULT_SEED_PLAYLIST_ID):
    if not playlist_id:
        raise RuntimeError("A seed playlist id is required to fetch tracks.")

    spotify_client = get_spotify_client()
    all_track_ids = []
    limit = 100
    offset = 0

    while True:
        response = spotify_client.playlist_items(playlist_id, limit=limit, offset=offset)
        items = response.get("items", [])
        if not items:
            break

        for item in items:
            track = item.get("track")
            track_id = track.get("id") if track else None
            if track_id:
                all_track_ids.append(track_id)

        if len(items) < limit:
            break
        offset += limit

    return all_track_ids


def _fetch_playlist_catalog(playlist_id):
    spotify_client = get_spotify_client()
    limit = 100
    offset = 0
    catalog = []

    while True:
        response = spotify_client.playlist_items(
            playlist_id,
            limit=limit,
            offset=offset,
            fields="items(track(id,name,explicit,uri,external_urls,popularity,album(name,images),artists(id,name))),next"
        )
        items = response.get("items", [])
        if not items:
            break

        for item in items:
            track = item.get("track")
            if not track or not track.get("id"):
                continue

            artists = track.get("artists", [])
            album = track.get("album") or {}
            album_images = album.get("images") or []

            catalog.append(
                {
                    "id": track["id"],
                    "name": track.get("name") or "Unknown Track",
                    "uri": track.get("uri") or f"spotify:track:{track['id']}",
                    "spotify_url": (track.get("external_urls") or {}).get("spotify", ""),
                    "explicit": bool(track.get("explicit", False)),
                    "popularity": track.get("popularity") or 0,
                    "album_name": album.get("name") or "",
                    "image_url": album_images[0].get("url") if album_images else "",
                    "artist_ids": [artist.get("id") for artist in artists if artist.get("id")],
                    "artist_names": [artist.get("name") for artist in artists if artist.get("name")]
                }
            )

        if len(items) < limit:
            break
        offset += limit

    return catalog


def get_track_catalog(playlist_id=DEFAULT_SEED_PLAYLIST_ID, force_refresh=False):
    cache_key = playlist_id or "default"
    cache_entry = _playlist_catalog_cache.get(cache_key)
    if not force_refresh and _is_cache_valid(cache_entry, CATALOG_CACHE_TTL_SECONDS):
        return [dict(item) for item in cache_entry["catalog"]]

    catalog = _fetch_playlist_catalog(playlist_id)
    _playlist_catalog_cache[cache_key] = {
        "timestamp": _get_now(),
        "catalog": catalog
    }
    return [dict(item) for item in catalog]


def _chunk(values, chunk_size):
    for index in range(0, len(values), chunk_size):
        yield values[index:index + chunk_size]


def get_artist_genres(artist_ids):
    spotify_client = get_spotify_client()
    unique_ids = [artist_id for artist_id in set(artist_ids) if artist_id]
    if not unique_ids:
        return {}

    missing_ids = [artist_id for artist_id in unique_ids if artist_id not in _artist_genres_cache]
    for chunk in _chunk(missing_ids, 50):
        payload = spotify_client.artists(chunk)
        for artist in payload.get("artists", []):
            if artist and artist.get("id"):
                _artist_genres_cache[artist["id"]] = artist.get("genres") or []

    return {artist_id: _artist_genres_cache.get(artist_id, []) for artist_id in unique_ids}


def enrich_catalog_with_genres(catalog):
    artist_ids = []
    for track in catalog:
        artist_ids.extend(track.get("artist_ids", []))

    artist_genres_map = get_artist_genres(artist_ids)
    enriched = []

    for track in catalog:
        track_genres = set()
        for artist_id in track.get("artist_ids", []):
            for genre in artist_genres_map.get(artist_id, []):
                track_genres.add(genre.lower())

        track_copy = dict(track)
        track_copy["genres"] = sorted(track_genres)
        enriched.append(track_copy)

    return enriched


def get_user_taste_profile(force_refresh=False):
    global _user_profile_cache
    if not force_refresh and _is_cache_valid(_user_profile_cache, PROFILE_CACHE_TTL_SECONDS):
        return dict(_user_profile_cache["profile"])

    spotify_client = get_spotify_client()

    top_artist_ids = set()
    top_track_ids = set()

    try:
        top_artists = spotify_client.current_user_top_artists(limit=25, time_range="medium_term")
        for artist in top_artists.get("items", []):
            artist_id = artist.get("id")
            if artist_id:
                top_artist_ids.add(artist_id)
    except Exception:
        top_artist_ids = set()

    try:
        top_tracks = spotify_client.current_user_top_tracks(limit=50, time_range="medium_term")
        for track in top_tracks.get("items", []):
            track_id = track.get("id")
            if track_id:
                top_track_ids.add(track_id)
    except Exception:
        top_track_ids = set()

    profile = {
        "top_artist_ids": sorted(top_artist_ids),
        "top_track_ids": sorted(top_track_ids)
    }

    _user_profile_cache = {
        "timestamp": _get_now(),
        "profile": profile
    }
    return dict(profile)


def get_genre_counts_for_catalog(catalog):
    counts = defaultdict(int)
    for track in catalog:
        for genre in track.get("genres", []):
            counts[genre] += 1
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))
