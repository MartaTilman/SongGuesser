from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from lobby_manager import LobbyManager
from game_manager import GameManager
from models.player import Player

app = FastAPI()

lobby_manager = LobbyManager()
game_manager = GameManager(lobby_manager)


@app.get("/")
def root():
    return {"status": "backend running"}
@app.get("/test-song")
def test_song():

    from services.song_cache import SongCache

    cache = SongCache()
    cache.fill_cache()

    return cache.get_song("90s")
@app.get("/lobby/{lobby_id}/blockchain")
def get_blockchain(lobby_id):

    lobby = lobby_manager.lobbies.get(lobby_id)

    if not lobby:
        return {"error": "Lobby not found"}

    return [block.__dict__ for block in lobby.blockchain.chain]

@app.websocket("/ws/{lobby_id}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, lobby_id: str, player_name: str):

    await websocket.accept()

    player = Player(player_name, websocket, "default")

    game = lobby_manager.join_lobby(lobby_id, player)

    try:

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
                    data.get("answer")
                )

            elif msg_type == "finish_song":

                if player.name == game.host:
                    await game_manager.finish_song(lobby_id)

    except WebSocketDisconnect:

        print(player_name, "disconnected")