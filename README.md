# Song Guesser

Song Guesser is a real-time multiplayer music guessing game. Players join a lobby, listen to short song clips, guess the title, artist, and release year, then compete on a live leaderboard.

The app has a retro Windows XP / media player visual style and is responsive for desktop, tablet, and mobile screens.

## Features

- Create or join multiplayer lobbies with a short lobby code
- Real-time gameplay through WebSockets
- Host-controlled round flow
- Guess song title, artist, and release year
- Live scoring and leaderboard screens
- Final podium reveal with sound effects
- YouTube-powered song playback
- Song metadata cache for faster game startup
- Blockchain-style game history storage for lobby results
- Responsive UI for smaller screens

## Tech Stack

**Frontend**

- Vue 3
- Vite
- Pinia
- Vue Router
- Axios

**Backend**

- Python
- FastAPI
- WebSockets
- YouTube Data API
- OpenAI API for song metadata parsing and validation

## Project Structure

```text
song-guesser/
  backend/      FastAPI server, game logic, lobby manager, blockchain storage
  frontend/     Vue/Vite client application
  README.md     Project documentation
```

## Prerequisites

- Node.js 20.19+ or 22.12+
- Python 3.10+
- YouTube Data API key
- OpenAI API key, unless `USE_OPENAI=false`

## Environment Variables

Create a `.env` file in the `backend` folder:

```env
YOUTUBE_API_KEY=your_youtube_api_key
OPENAI_API_KEY=your_openai_api_key
USE_OPENAI=true
```

Optional:

```env
YOUTUBE_DISCOVERY_ATTEMPT_BUDGET=40
```

## Run Locally

### 1. Start the backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend runs on:

```text
http://127.0.0.1:8000
```

### 2. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on:

```text
http://localhost:5173
```

## How To Play

1. Open the frontend in the browser.
2. Enter a player name and choose an avatar.
3. Create a lobby or join an existing lobby with a lobby code.
4. The host starts the game.
5. Listen to the clip and submit guesses for title, artist, and year.
6. Check the leaderboard after each song.
7. Play through all rounds and reveal the final winner.

## Build

```bash
cd frontend
npm run build
```

The production build is generated in `frontend/dist`.

## Notes

- The frontend currently expects the backend at `http://127.0.0.1:8000`.
- WebSocket connections use the same backend host and port.
- The backend warms up the song cache when it starts, so the first run can take longer if the cache needs new songs.
