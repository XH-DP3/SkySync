import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()
client = OpenAI()

AUDIO_FEATURES_MODEL = os.getenv("OPENAI_AUDIO_FEATURES_MODEL", "gpt-4o-2024-08-06")
TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-5")

SONG_PARAMETER_SYSTEM_PROMPT = (
    "You generate playlist audio features from weather context. "
    "Return JSON with keys valence, danceability, and energy. "
    "Each value must be a float from 0.0 to 1.0."
)


class AudioFeatures(BaseModel):
    valence: float
    danceability: float
    energy: float


class PlaylistOptions(BaseModel):
    genres: list[str] = []
    exclude_explicit: bool = False
    personalize: bool = False


class GenreExpansion(BaseModel):
    genres: list[str] = []


def _clamp(value):
    return max(0.0, min(1.0, float(value)))


def _normalize_text(value):
    return " ".join((value or "").strip().split())


def _context_text(song_params, weather_data, options=None):
    options = options or {}
    genre_text = ", ".join(options.get("genres", [])) or "any genre"
    explicit_text = "exclude explicit tracks" if options.get("exclude_explicit") else "allow explicit tracks"
    personalize_text = (
        "personalized to the listener's Spotify taste"
        if options.get("personalize")
        else "not personalized"
    )

    return (
        f"Song parameters: {song_params}. "
        f"Weather data: {weather_data}. "
        f"Genre preference: {genre_text}. "
        f"Explicit setting: {explicit_text}. "
        f"Personalization: {personalize_text}. "
        "Audio features definitions: "
        "danceability measures rhythmic suitability for dancing, "
        "energy measures intensity and activity, "
        "valence measures positivity."
    )


def to_audio_features(values):
    if isinstance(values, AudioFeatures):
        return values

    def _read(field_name, fallback):
        if hasattr(values, field_name):
            return getattr(values, field_name)
        if isinstance(values, dict):
            return values.get(field_name, fallback)
        return fallback

    return AudioFeatures(
        valence=_clamp(_read("valence", 0.5)),
        danceability=_clamp(_read("danceability", 0.5)),
        energy=_clamp(_read("energy", 0.5))
    )


def getSongParams(weather_data):
    completion = client.beta.chat.completions.parse(
        model=AUDIO_FEATURES_MODEL,
        messages=[
            {"role": "system", "content": SONG_PARAMETER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Weather context: {weather_data}"}
        ],
        response_format=AudioFeatures
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("Unable to parse audio features from model response.")

    return AudioFeatures(
        valence=_clamp(parsed.valence),
        danceability=_clamp(parsed.danceability),
        energy=_clamp(parsed.energy)
    )


def apply_audio_overrides(song_params, overrides=None):
    if not overrides:
        return song_params

    base = to_audio_features(song_params)

    def _resolve_override(field_name, default_value):
        value = overrides.get(field_name)
        if value is None or value == "":
            return default_value
        return _clamp(value)

    return AudioFeatures(
        valence=_resolve_override("valence", base.valence),
        danceability=_resolve_override("danceability", base.danceability),
        energy=_resolve_override("energy", base.energy)
    )


def to_audio_feature_dict(song_params):
    resolved = to_audio_features(song_params)
    return {
        "valence": round(resolved.valence, 3),
        "danceability": round(resolved.danceability, 3),
        "energy": round(resolved.energy, 3)
    }


def maketitle(song_params, weather_data, options=None):
    prompt = (
        f"{_context_text(song_params, weather_data, options)} "
        "Create a playlist title with 1-3 words. "
        "Return only the title text."
    )
    response = client.responses.create(model=TEXT_MODEL, input=prompt)
    title = _normalize_text(response.output_text)
    return title if title else "SkySync Mix"


def makedescription(song_params, weather_data, options=None):
    prompt = (
        f"{_context_text(song_params, weather_data, options)} "
        "Write exactly one sentence for the playlist description. "
        "Return only the description text."
    )
    response = client.responses.create(model=TEXT_MODEL, input=prompt)
    description = _normalize_text(response.output_text)
    return description if description else "A weather-matched playlist for your current vibe."


def expand_genre_queries(genres):
    normalized = []
    for genre in genres or []:
        cleaned = _normalize_text(str(genre)).lower()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)

    if not normalized:
        return []

    prompt = (
        "Given these music genres, suggest up to 5 related Spotify-searchable genre phrases "
        "that would help find more tracks when the catalog is too small. "
        "Keep the suggestions close to the original genres, avoid duplicates, and prefer broad, real genre names. "
        f"Genres: {normalized}"
    )

    try:
        completion = client.beta.chat.completions.parse(
            model=AUDIO_FEATURES_MODEL,
            messages=[
                {"role": "system", "content": "Return JSON with one key, genres, as an array of short strings."},
                {"role": "user", "content": prompt}
            ],
            response_format=GenreExpansion
        )
        parsed = completion.choices[0].message.parsed
    except Exception:
        return []

    if parsed is None:
        return []

    expanded = []
    for genre in parsed.genres:
        cleaned = _normalize_text(str(genre)).lower()
        if cleaned and cleaned not in normalized and cleaned not in expanded:
            expanded.append(cleaned)

    return expanded[:5]
