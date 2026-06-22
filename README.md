# Song Guesser

Song Guesser is a real-time multiplayer music guessing game. Players join a lobby, listen to short song clips, guess the title, artist, and release year, then compete on a live leaderboard.

The app has a retro Windows XP / media player visual style and is responsive for desktop, tablet, and mobile screens.

## Live App

- Frontend: [song-guesser-one.vercel.app](https://song-guesser-one.vercel.app)
- Backend API: [songguesser.onrender.com](https://songguesser.onrender.com)

## Features

- Create or join multiplayer lobbies with a short lobby code
- Real-time gameplay through WebSockets
- Host-controlled round flow
- Guess song title, artist, and release year
- Live scoring and leaderboard screens
- Final podium reveal with sound effects
- YouTube-powered song playback
- Song metadata cache for faster game startup
- Local proof-of-work blockchain audit log for lobby results
- Browser wallet signatures for player joins and submitted answers
- Salted commit-reveal proof for each selected song
- Final game proof with chain hash and Merkle root, ready for public-chain anchoring
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
- MusicBrainz API for song year validation and decade-based song discovery
- Optional OpenAI API support for song metadata parsing and validation

## Project Structure

```text
song-guesser/
  backend/      FastAPI server, game logic, lobby manager, blockchain storage
  contracts/    Solidity contract for public blockchain proof anchoring
  frontend/     Vue/Vite client application
  README.md     Project documentation
```

## Prerequisites

- Node.js 20.19+ or 22.12+
- Python 3.10+
- YouTube Data API key
- OpenAI API key only if `USE_OPENAI=true`

## Environment Variables

Create a `.env` file in the `backend` folder:

```env
YOUTUBE_API_KEY=your_youtube_api_key
USE_OPENAI=false
```

Optional:

```env
OPENAI_API_KEY=your_openai_api_key
YOUTUBE_DISCOVERY_ATTEMPT_BUDGET=40
DATABASE_URL=postgresql://user:password@host:5432/database
BLOCKCHAIN_DIFFICULTY=3
ETH_RPC_URL=https://your-rpc-endpoint
CONTRACT_ADDRESS=0xYourDeployedContractAddress
SUBMITTER_PRIVATE_KEY=0xYourWalletPrivateKey
```

`ETH_RPC_URL`, `CONTRACT_ADDRESS`, and `SUBMITTER_PRIVATE_KEY` are only needed if you want final game proofs anchored on-chain. Without them the game still works and the local blockchain audit log is still kept — anchoring is simply skipped. Anchoring also requires the `web3` Python package (`pip install web3`).

`DATABASE_URL` is optional locally. If it is not set, the backend keeps using
`backend/song_metadata_cache.json`. For deployment, set `DATABASE_URL` to an
online PostgreSQL database URL, for example Render Postgres, Supabase, or Neon.
On first start with an empty database, the backend seeds the database from the
local JSON cache, then stores newly discovered songs in PostgreSQL.

## Blockchain Model

The app keeps a local proof-of-work chain per lobby in `backend/blockchain_storage`.
Each block links to the previous block hash and is mined with `BLOCKCHAIN_DIFFICULTY`.

The game also uses:

- browser-generated RSA-PSS wallets for players,
- signed `join_lobby` and `submit_answer` actions,
- salted song commitments before each round,
- song reveal data after each round,
- a final game proof containing `chain_hash`, `merkle_root`, and `leaderboard_hash`.

After a game finishes, fetch the anchoring payload from:

```text
GET /lobby/{lobby_id}/blockchain/final-proof
```

The Solidity contract in `contracts/SongGuesserAnchor.sol` can anchor that final
proof on a public EVM chain such as Polygon, Base, Arbitrum, or a Sepolia testnet.
Deploying and submitting the proof requires your own RPC URL and wallet key.

For the deployed frontend, set these Vercel environment variables:

```env
VITE_API_URL=https://songguesser.onrender.com
VITE_WS_URL=wss://songguesser.onrender.com
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

## Game Structure

A full game is 3 rounds with 16 songs total (5 in round 1, 5 in round 2, 6 in round 3). Each round plays shorter clips to increase the difficulty:

- Round 1 — 15-second clips
- Round 2 — 12-second clips
- Round 3 — 9-second clips

After each clip there is a 15-second answer window. Submitting the correct answer faster earns more points (300–1000 per correct field). After all songs a final podium reveals the top three players.

## How To Play

1. Open the frontend in the browser.
2. Enter a player name and choose an avatar.
3. Create a lobby or join an existing lobby with a lobby code.
4. The host starts the game.
5. Listen to the clip and submit guesses for title, artist, and year before the timer runs out.
6. Check the leaderboard after each song.
7. Play through all 3 rounds and see the final podium.

## Build

```bash
cd frontend
npm run build
```

The production build is generated in `frontend/dist`.

## Notes

- Locally, the frontend falls back to `http://127.0.0.1:8000` and `ws://127.0.0.1:8000`.
- In production, the frontend uses the Render backend through `VITE_API_URL` and `VITE_WS_URL`.
- The backend warms up the song cache when it starts, so the first run can take longer if the cache needs new songs.
