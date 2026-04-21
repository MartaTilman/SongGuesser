# Music Blockchain Quiz 🎶

A real-time multiplayer music quiz game with blockchain-backed round history.

## Overview

Music Blockchain Quiz is a web application where players listen to short song clips and try to guess:

- song title
- artist
- release year

The game supports real-time multiplayer sessions through lobby codes, automatic scoring, round-based progression, and a blockchain-style history of results for transparency and review.

## Key Features

- real-time multiplayer gameplay
- automatically generated lobby codes
- round-based music quiz flow
- YouTube clip playback for each round
- guessing song title, artist, and year
- score calculation based on accuracy and speed
- leaderboard after every round
- final winner overview at the end of the game
- blockchain view of round results and game events

## Tech Stack

### Frontend
- Vue 3
- Vite
- Pinia
- Vue Router

### Backend
- FastAPI
- WebSocket

### External Services
- YouTube Data API
- MusicBrainz API
- OpenAI API

### Other
- custom blockchain implementation

## How The Game Works

1. The host creates a new lobby.
2. The system generates a unique lobby code.
3. Other players join the lobby using that code.
4. When the round starts, a short countdown is shown.
5. A song clip is played.
6. Players submit their guesses.
7. After the round ends, correct answers and the leaderboard are displayed.
8. At the end of the game, the final ranking is shown.
9. Round results are stored in the blockchain log.
