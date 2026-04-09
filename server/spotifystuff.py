import os
import secrets
import time
from collections import defaultdict

import spotipy
from dotenv import load_dotenv
from flask import has_request_context, session
from spotipy.cache_handler import CacheHandler
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

load_dotenv()

SPOTIFY_SCOPE = (
    "user-top-read playlist-read-private playlist-read-collaborative user-read-private "
    "playlist-modify-public playlist-modify-private "
    "user-modify-playback-state user-read-playback-state"
)
SPOTIFY_REDIRECT_URI = os.getenv(
    "SPOTIFY_REDIRECT_URI",
    "http://localhost:5000/api/spotify/callback"
)
DEFAULT_SEED_PLAYLIST_ID = (os.getenv("SPOTIFY_SEED_PLAYLIST_ID") or "").strip()
CATALOG_CACHE_TTL_SECONDS = 60 * 15
PROFILE_CACHE_TTL_SECONDS = 60 * 5
SPOTIFY_TOKEN_SESSION_KEY = "spotify_token_info"
SPOTIFY_STATE_SESSION_KEY = "spotify_oauth_state"

_spotify_app_client = None
_playlist_catalog_cache = {}
_user_playlist_catalog_cache = {}
_artist_genres_cache = {}
_user_account_cache = {}
_user_taste_cache = {}


class FlaskSessionCacheHandler(CacheHandler):
    def get_cached_token(self):
        if not has_request_context():
            return None
        return session.get(SPOTIFY_TOKEN_SESSION_KEY)

    def save_token_to_cache(self, token_info):
        if has_request_context():
            session[SPOTIFY_TOKEN_SESSION_KEY] = token_info


def _get_now():
    return time.time()


def _is_cache_valid(entry, ttl_seconds):
    if not entry:
        return False
    return (_get_now() - entry["timestamp"]) < ttl_seconds


def _get_spotify_credentials():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET.")
    return client_id, client_secret


def get_spotify_app_client():
    global _spotify_app_client
    if _spotify_app_client is not None:
        return _spotify_app_client

    client_id, client_secret = _get_spotify_credentials()
    auth_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret
    )
    _spotify_app_client = spotipy.Spotify(auth_manager=auth_manager)
    return _spotify_app_client


def get_spotify_oauth():
    client_id, client_secret = _get_spotify_credentials()
    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE,
        cache_handler=FlaskSessionCacheHandler(),
        show_dialog=True
    )


def get_spotify_auth_url():
    if not has_request_context():
        raise RuntimeError("Spotify auth requires an active request context.")

    oauth = get_spotify_oauth()
    state = secrets.token_urlsafe(16)
    session[SPOTIFY_STATE_SESSION_KEY] = state
    return oauth.get_authorize_url(state=state)


def complete_spotify_auth(code, state=None):
    if not has_request_context():
        raise RuntimeError("Spotify auth requires an active request context.")

    expected_state = session.get(SPOTIFY_STATE_SESSION_KEY)
    if expected_state and state and state != expected_state:
        raise RuntimeError("Spotify authorization state mismatch.")

    oauth = get_spotify_oauth()
    oauth.get_access_token(code=code, check_cache=False)
    session.pop(SPOTIFY_STATE_SESSION_KEY, None)
    return get_current_spotify_user(force_refresh=True)


def clear_spotify_auth():
    if not has_request_context():
        return
    session.pop(SPOTIFY_TOKEN_SESSION_KEY, None)
    session.pop(SPOTIFY_STATE_SESSION_KEY, None)


def get_current_spotify_user(force_refresh=False):
    spotify_client = get_spotify_client(user_required=True)
    cache_key = _get_user_cache_key()
    cache_entry = _user_account_cache.get(cache_key)
    if not force_refresh and _is_cache_valid(cache_entry, PROFILE_CACHE_TTL_SECONDS):
        return dict(cache_entry["profile"])

    user = spotify_client.current_user()
    profile = {
        "id": user.get("id"),
        "display_name": user.get("display_name") or user.get("id") or "Spotify User",
        "product": user.get("product") or "",
        "country": user.get("country") or ""
    }
    _user_account_cache[cache_key] = {
        "timestamp": _get_now(),
        "profile": profile
    }
    return dict(profile)


def get_spotify_auth_status():
    try:
        profile = get_current_spotify_user()
        return {
            "connected": True,
            "user": profile
        }
    except Exception:
        return {
            "connected": False,
            "user": None
        }


def has_spotify_user_connection():
    if not has_request_context():
        return False
    try:
        oauth = get_spotify_oauth()
        token_info = oauth.validate_token(oauth.cache_handler.get_cached_token())
        return bool(token_info)
    except Exception:
        return False


def _get_user_cache_key():
    token_info = session.get(SPOTIFY_TOKEN_SESSION_KEY) if has_request_context() else None
    if not token_info:
        return None
    return token_info.get("refresh_token") or token_info.get("access_token") or "spotify-user"


def get_spotify_client(user_required=False):
    if not user_required:
        return get_spotify_app_client()

    if not has_request_context():
        raise RuntimeError("Spotify user access requires an active request context.")

    oauth = get_spotify_oauth()
    token_info = oauth.validate_token(oauth.cache_handler.get_cached_token())
    if not token_info:
        raise RuntimeError("Connect your Spotify account to use this feature.")

    return spotipy.Spotify(auth=token_info["access_token"])


def get_all_track_ids(playlist_id=None):
    resolved_playlist_id = playlist_id or DEFAULT_SEED_PLAYLIST_ID
    if not resolved_playlist_id:
        raise RuntimeError("Set SPOTIFY_SEED_PLAYLIST_ID before generating playlists.")

    spotify_client = get_spotify_client()
    all_track_ids = []
    limit = 100
    offset = 0

    while True:
        response = spotify_client.playlist_items(resolved_playlist_id, limit=limit, offset=offset)
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


def _playlist_track_to_catalog_item(track):
    if not track or not track.get("id"):
        return None

    artists = track.get("artists", [])
    album = track.get("album") or {}
    album_images = album.get("images") or []
    return {
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


def search_tracks_for_genres(genres, limit_per_genre=10):
    spotify_client = get_spotify_client()
    deduped_tracks = {}

    for genre in genres or []:
        cleaned_genre = str(genre).strip()
        if not cleaned_genre:
            continue

        queries = [f'genre:"{cleaned_genre}"', cleaned_genre]
        for query in queries:
            try:
                response = spotify_client.search(q=query, type="track", limit=limit_per_genre)
            except Exception:
                continue

            items = ((response.get("tracks") or {}).get("items")) or []
            for track in items:
                catalog_item = _playlist_track_to_catalog_item(track)
                if catalog_item:
                    deduped_tracks.setdefault(catalog_item["id"], catalog_item)

            if items:
                break

    return list(deduped_tracks.values())


def _fetch_user_playlist_catalog():
    spotify_client = get_spotify_client(user_required=True)
    playlists = []
    limit = 50
    offset = 0

    while True:
        response = spotify_client.current_user_playlists(limit=limit, offset=offset)
        items = response.get("items", [])
        if not items:
            break
        playlists.extend(items)
        if len(items) < limit:
            break
        offset += limit

    deduped_tracks = {}
    playlist_count = 0
    for playlist in playlists:
        playlist_id = playlist.get("id")
        total_tracks = (playlist.get("tracks") or {}).get("total", 0)
        if not playlist_id or total_tracks <= 0:
            continue

        playlist_count += 1
        track_offset = 0
        while True:
            response = spotify_client.playlist_items(
                playlist_id,
                limit=100,
                offset=track_offset,
                fields="items(track(id,name,explicit,uri,external_urls,popularity,album(name,images),artists(id,name))),next"
            )
            items = response.get("items", [])
            if not items:
                break

            for item in items:
                track = _playlist_track_to_catalog_item(item.get("track"))
                if not track:
                    continue
                deduped_tracks.setdefault(track["id"], track)

            if len(items) < 100:
                break
            track_offset += 100

    return {
        "catalog": list(deduped_tracks.values()),
        "playlist_count": playlist_count
    }


def get_track_catalog(playlist_id=None, force_refresh=False):
    resolved_playlist_id = playlist_id or DEFAULT_SEED_PLAYLIST_ID
    if not resolved_playlist_id:
        raise RuntimeError("Set SPOTIFY_SEED_PLAYLIST_ID before generating playlists.")

    cache_key = resolved_playlist_id
    cache_entry = _playlist_catalog_cache.get(cache_key)
    if not force_refresh and _is_cache_valid(cache_entry, CATALOG_CACHE_TTL_SECONDS):
        return [dict(item) for item in cache_entry["catalog"]]

    catalog = _fetch_playlist_catalog(resolved_playlist_id)
    _playlist_catalog_cache[cache_key] = {
        "timestamp": _get_now(),
        "catalog": catalog
    }
    return [dict(item) for item in catalog]


def get_user_track_catalog(force_refresh=False):
    cache_key = _get_user_cache_key()
    if not cache_key:
        raise RuntimeError("Connect your Spotify account to use your playlists.")

    cache_entry = _user_playlist_catalog_cache.get(cache_key)
    if not force_refresh and _is_cache_valid(cache_entry, CATALOG_CACHE_TTL_SECONDS):
        return {
            "catalog": [dict(item) for item in cache_entry["catalog"]],
            "playlist_count": cache_entry["playlist_count"]
        }

    payload = _fetch_user_playlist_catalog()
    catalog = payload["catalog"]
    playlist_count = payload["playlist_count"]
    if not catalog:
        raise RuntimeError("No playable tracks were found in this Spotify account's playlists.")

    _user_playlist_catalog_cache[cache_key] = {
        "timestamp": _get_now(),
        "catalog": catalog,
        "playlist_count": playlist_count
    }
    return {
        "catalog": [dict(item) for item in catalog],
        "playlist_count": playlist_count
    }


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
    cache_key = _get_user_cache_key()
    cache_entry = _user_taste_cache.get(cache_key)
    if not force_refresh and cache_key and _is_cache_valid(cache_entry, PROFILE_CACHE_TTL_SECONDS):
        cached_profile = dict(cache_entry["profile"])
        return {
            "top_artist_ids": cached_profile.get("top_artist_ids", []),
            "top_track_ids": cached_profile.get("top_track_ids", [])
        }

    spotify_client = get_spotify_client(user_required=True)

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

    if cache_key:
        _user_taste_cache[cache_key] = {
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
