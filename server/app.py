from flask import Flask, jsonify, request
from flask_cors import CORS
from weather import get_weather_state
from openaiService import getSongParams, makedescription, maketitle
from playlist import make_new_playlist

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from weather_new import get_clean_weather

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route("/api/weather_new")
def weather_new():
    return jsonify(get_clean_weather())

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy'
    })

@app.route('/api/makeplaylistcurrentweather', methods=['GET'])
def makeplaylistcurrentweather():
    weather_data = get_weather_state()
    song_params = getSongParams(weather_data)
    
    # 1. Generate description (this is fine)
    description = makedescription(song_params, weather_data)

    # 2. CALL PLAYLIST FUNCTION AND CAPTURE THE TITLE
    # make_new_playlist returns two things: (link, title)
    spotify_link, title = make_new_playlist(weather_data)

    # 3. Return the captured title
    return jsonify({
        'status': 'playlist made',
        'title': title,           # This now uses the title from Spotify!
        'description': description,
        'link': spotify_link      # (Optional) You can send the link too if you want
    })

@app.route('/api/makeplaylistcustomweather', methods=['POST'])
def makeplaylistcustomweather():
    weather_data = request.get_json()

    if not weather_data:
        return jsonify({'error': 'No weather data provided'}), 400

    # 1. Call the function and capture the TWO return values
    # (No need to calculate song_params or title here anymore!)
    playlist_url, playlist_name = make_new_playlist(weather_data)

    # 2. Return the exact name and URL to the frontend
    return jsonify({
        'status': 'playlist made',
        'title': playlist_name,  # Matches Spotify exactly
        'url': playlist_url      # Useful for opening the playlist
    })

if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=5000)

