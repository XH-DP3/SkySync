import logging

from flask import Flask, jsonify, request
from flask_cors import CORS

from playlist import generate_playlist_bundle, make_new_playlist
from weather_new import get_clean_weather, get_weather_state, search_locations

app = Flask(__name__)
CORS(app)
app.logger.setLevel(logging.INFO)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


@app.route("/api/locations/search", methods=["GET"])
def location_search():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return jsonify({"status": "ok", "results": []})

    try:
        results = search_locations(query, count=8)
        return jsonify({"status": "ok", "results": results})
    except Exception as error:
        app.logger.exception("Location search failed.")
        return (
            jsonify({"status": "error", "message": f"Location search failed: {error}"}),
            502
        )


@app.route("/api/weather", methods=["POST"])
def weather_snapshot():
    payload = request.get_json(silent=True) or {}
    location = payload.get("location")
    forecast_mode = payload.get("forecast_mode", "now")
    force_refresh = bool(payload.get("force_refresh", False))

    try:
        weather = get_clean_weather(
            location_payload=location,
            forecast_mode=forecast_mode,
            use_cache=not force_refresh
        )
        return jsonify({"status": "ok", "weather": weather})
    except Exception as error:
        app.logger.exception("Failed to fetch weather snapshot.")
        return (
            jsonify({"status": "error", "message": f"Unable to load weather: {error}"}),
            502
        )


@app.route("/api/playlists/generate", methods=["POST"])
def generate_playlist():
    payload = request.get_json(silent=True) or {}

    location = payload.get("location")
    forecast_mode = payload.get("forecast_mode", "now")
    preferences = payload.get("preferences") or {}
    action = payload.get("action", "preview")
    regenerate = bool(payload.get("regenerate", False))
    preview_track_ids = payload.get("preview_track_ids") or []
    seed_playlist_id = payload.get("seed_playlist_id")
    force_refresh = bool(payload.get("force_refresh", False))

    try:
        weather_payload = get_weather_state(
            location_payload=location,
            forecast_mode=forecast_mode,
            use_cache=not force_refresh
        )
        weather_snapshot = weather_payload["weather_snapshot"]
        weather_state = {
            "current_weather": weather_payload["current_weather"],
            "current_time": weather_payload["current_time"]
        }

        playlist_bundle = generate_playlist_bundle(
            weather_state=weather_state,
            preferences=preferences,
            action=action,
            regenerate=regenerate,
            preview_track_ids=preview_track_ids,
            seed_playlist_id=seed_playlist_id,
            force_refresh=force_refresh
        )

        return jsonify(
            {
                "status": "ok",
                "weather": weather_snapshot,
                **playlist_bundle
            }
        )
    except Exception as error:
        app.logger.exception("Playlist generation failed.")
        return (
            jsonify({"status": "error", "message": f"Failed to generate playlist: {error}"}),
            500
        )


# Backward-compatible endpoints
@app.route("/api/weather_new", methods=["GET"])
def weather_new():
    try:
        return jsonify(get_clean_weather())
    except Exception as error:
        app.logger.exception("Failed to fetch weather data.")
        return (
            jsonify({"status": "error", "message": f"Unable to load weather: {error}"}),
            502
        )


@app.route("/api/makeplaylistcurrentweather", methods=["POST"])
def makeplaylistcurrentweather():
    payload = request.get_json(silent=True) or {}
    auto_play = bool(payload.get("auto_play", False))

    try:
        weather_payload = get_weather_state()
        weather_state = {
            "current_weather": weather_payload["current_weather"],
            "current_time": weather_payload["current_time"]
        }
        spotify_link, title = make_new_playlist(weather_state, auto_play=auto_play)
        return jsonify(
            {
                "status": "playlist made",
                "title": title,
                "description": "Playlist generated from your current weather.",
                "link": spotify_link
            }
        )
    except Exception as error:
        app.logger.exception("Failed to create playlist for current weather.")
        return (
            jsonify({"status": "error", "message": f"Failed to generate playlist: {error}"}),
            500
        )


@app.route("/api/makeplaylistcustomweather", methods=["POST"])
def makeplaylistcustomweather():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"status": "error", "message": "No weather data provided."}), 400

    auto_play = bool(payload.get("auto_play", False))
    weather_data = payload.get("weather", payload)

    try:
        playlist_link, playlist_name = make_new_playlist(weather_data, auto_play=auto_play)
        return jsonify(
            {
                "status": "playlist made",
                "title": playlist_name,
                "description": "Playlist generated from custom weather.",
                "link": playlist_link
            }
        )
    except Exception as error:
        app.logger.exception("Failed to create playlist for custom weather.")
        return (
            jsonify({"status": "error", "message": f"Failed to generate playlist: {error}"}),
            500
        )


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
