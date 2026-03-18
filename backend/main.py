from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from lobby_manager import LobbyManager
from game_manager import GameManager, song_cache
from models.player import Player


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        song_cache.fill_cache(min_songs_per_decade=5)
    except Exception as e:
        print(f"Song cache loading failed: {e}")

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

lobby_manager = LobbyManager()
game_manager = GameManager(lobby_manager)


@app.get("/")
def root():
    return {"status": "backend running"}


@app.get("/lobbies")
def get_lobbies():
    return list(lobby_manager.lobbies.keys())


@app.get("/lobby/{lobby_id}/players")
def get_players(lobby_id: str):
    lobby = lobby_manager.lobbies.get(lobby_id)

    if not lobby:
        return {"error": "Lobby not found"}

    return [player.to_dict() for player in lobby.players]


@app.get("/lobby/{lobby_id}/info")
def get_lobby_info(lobby_id: str):
    lobby = lobby_manager.lobbies.get(lobby_id)

    if not lobby:
        return {"error": "Lobby not found"}

    return {
        "lobby_id": lobby.id,
        "host": lobby.host,
        "players": [player.to_dict() for player in lobby.players],
        "current_round": lobby.current_round,
        "current_song_in_round": lobby.current_song_in_round,
        "songs_per_round": lobby.songs_per_round,
        "total_rounds": lobby.total_rounds,
    }


@app.get("/lobby/{lobby_id}/blockchain")
def get_blockchain(lobby_id: str):
    lobby = lobby_manager.lobbies.get(lobby_id)

    if not lobby:
        return {"error": "Lobby not found"}

    return {
        "valid": lobby.blockchain.is_valid(),
        "chain": lobby.blockchain.to_list()
    }


@app.websocket("/ws/{lobby_id}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, lobby_id: str, player_name: str):
    await websocket.accept()

    avatar = websocket.query_params.get("avatar", "🎵")
    player = Player(player_name, websocket, avatar)

    try:
        game = lobby_manager.join_lobby(lobby_id, player)

        await lobby_manager.broadcast(lobby_id, {
            "type": "lobby_update",
            "host": game.host,
            "players": [p.to_dict() for p in game.players]
        })

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "start_round":
                if player.name == game.host:
                    await game_manager.start_round(lobby_id)

            elif msg_type == "answer":
                 await game_manager.submit_answer(
                    lobby_id,
                    player,
                    data.get("title_answer"),
                    data.get("artist_answer"),
                    data.get("year_answer")
    )

            elif msg_type == "finish_song":
                if player.name == game.host:
                    await game_manager.finish_song(lobby_id)

    except ValueError as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        await websocket.close()

    except WebSocketDisconnect:
        updated_lobby = lobby_manager.remove_player(lobby_id, player_name)

        if updated_lobby:
            await lobby_manager.broadcast(lobby_id, {
                "type": "lobby_update",
                "host": updated_lobby.host,
                "players": [p.to_dict() for p in updated_lobby.players]
            })

        print(f"{player_name} disconnected")

    except Exception as e:
        print(f"WebSocket error for {player_name} in lobby {lobby_id}: {e}")

        updated_lobby = lobby_manager.remove_player(lobby_id, player_name)

        if updated_lobby:
            try:
                await lobby_manager.broadcast(lobby_id, {
                    "type": "lobby_update",
                    "host": updated_lobby.host,
                    "players": [p.to_dict() for p in updated_lobby.players]
                })
            except Exception as broadcast_error:
                print(f"Broadcast after error failed: {broadcast_error}")