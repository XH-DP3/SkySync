from flask import Flask, jsonify
from flask_cors import CORS

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes



@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({
        'message': 'Hello from Flask backend!'
    })

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy'
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)

