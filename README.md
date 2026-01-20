# HackCamp - React + Flask Project

A full-stack web application with React frontend (Vite) and Python Flask backend.

Video Demonstration (Done by the event): https://youtu.be/BxqBU9g5j1k?si=KMWORhu0bPtMIqpr

## Project Structure

```
HackCamp/
├── client/          # React frontend (Vite)
│   ├── src/        # React source files
│   ├── public/     # Static assets
│   └── package.json
└── server/          # Flask backend
    ├── app.py      # Main Flask application
    └── requirements.txt
```

## Prerequisites

- Node.js (v16 or higher) and npm
- Python 3.8 or higher
- pip (Python package manager)

## Setup Instructions

### Backend Setup (Flask)

1. Navigate to the server directory:
   ```bash
   cd server
   ```

2. Create a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   ```

3. Activate the virtual environment:
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the Flask server:
   ```bash
   python app.py
   ```

   The backend will run on `http://localhost:5000`

### Frontend Setup (React)

1. Navigate to the client directory:
   ```bash
   cd client
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

   The frontend will run on `http://localhost:3000`

## Development

- **Frontend**: The Vite dev server supports hot module replacement (HMR) for instant updates
- **Backend**: Flask runs in debug mode with auto-reload enabled
- **API Proxy**: The Vite config includes a proxy that forwards `/api/*` requests to the Flask backend

## Available Scripts

### Frontend (client/)
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Backend (server/)
- `python app.py` - Run Flask development server

## API Endpoints

- `GET /api/hello` - Returns a greeting message
- `GET /api/health` - Health check endpoint

## Notes

- CORS is enabled on the Flask backend to allow requests from the React frontend
- The frontend is configured to proxy API requests to the backend during development
- Make sure both servers are running for the full-stack functionality

