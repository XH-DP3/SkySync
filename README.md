# SkySync

SkySync is a full-stack app that creates weather-aware Spotify playlists with preview, personalization, filtering, and sharing.

## Highlights

- Location-aware weather (city search + current geolocation)
- Forecast modes: `Now`, `Tonight`, `Tomorrow Morning`
- Playlist controls for mood (`valence`), `danceability`, and `energy`
- Genre filters, explicit-content toggle, and Spotify personalization bias
- Two-step generation flow: track preview first, then playlist creation
- Regenerate support for new variants with the same setup
- Playlist history and shareable links/cards
- Unified backend endpoint for playlist generation
- Weather/audio/catalog/profile caching for faster repeated requests

## Project Structure

```text
SkySync/
├── client/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── constants/
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
└── server/
    ├── app.py
    ├── weather_new.py
    ├── playlist.py
    ├── reccobeats_util.py
    ├── spotifystuff.py
    ├── openaiService.py
    └── requirements.txt
```

## Prerequisites

- Node.js 18+
- Python 3.10+
- A Spotify developer app
- An OpenAI API key

## Environment Variables

Create a `.env` file in `server/`:

```bash
OPENAI_API_KEY=your_openai_key
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_SEED_PLAYLIST_ID=optional_seed_playlist_id
OPENAI_AUDIO_FEATURES_MODEL=gpt-4o-2024-08-06
OPENAI_TEXT_MODEL=gpt-5
```

## Run Locally

### Backend

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Backend runs on `http://127.0.0.1:5000`.

### Frontend

```bash
cd client
npm install
npm run dev
```

Frontend runs on `http://127.0.0.1:3000`.

## API Endpoints

- `GET /api/health`
- `GET /api/locations/search?q=<city>`
- `POST /api/weather`
- `POST /api/playlists/generate`

Backward compatibility:

- `GET /api/weather_new`
- `POST /api/makeplaylistcurrentweather`
- `POST /api/makeplaylistcustomweather`

## Unified Playlist API

### `POST /api/playlists/generate`

Request body example:

```json
{
  "location": {
    "query": "Vancouver"
  },
  "forecast_mode": "tonight",
  "preferences": {
    "valence": 0.62,
    "danceability": null,
    "energy": 0.58,
    "genres": ["indie", "lofi"],
    "exclude_explicit": true,
    "personalize": true,
    "auto_play": false
  },
  "action": "preview",
  "regenerate": false,
  "preview_track_ids": []
}
```

- `action = "preview"` returns preview tracks only.
- `action = "create"` creates a Spotify playlist and returns a link.

## Notes

- Playlist creation is a side effect and is exposed via `POST`.
- Geolocation support depends on browser permission.
- Spotify personalization depends on valid Spotify auth + available top data.
