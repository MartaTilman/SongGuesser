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


@app.get("/lobbies")
def get_lobbies():
    return list(lobby_manager.lobbies.keys())


@app.get("/lobby/{lobby_id}/players")
def get_players(lobby_id):

    lobby = lobby_manager.lobbies.get(lobby_id)

    if not lobby:
        return {"error": "Lobby not found"}

    return [player.name for player in lobby.players]

@app.get("/lobby/{lobby_id}/info")
def get_lobby_info(lobby_id):

    lobby = lobby_manager.lobbies.get(lobby_id)

    if not lobby:
        return {"error": "Lobby not found"}

    return {
        "lobby_id": lobby.id,
        "host": lobby.host,
        "players": [player.name for player in lobby.players],
        "current_round": lobby.current_round,
        "current_song_in_round": lobby.current_song_in_round
    }

@app.get("/lobby/{lobby_id}/blockchain")
def get_blockchain(lobby_id):

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

    player = Player(player_name, websocket, "default")

    game = lobby_manager.join_lobby(lobby_id, player)

    # dodatni auth zapis na blockchain
    game.blockchain.add_auth_event(player.name, "join_lobby")

    try:

        while True:

            data = await websocket.receive_json()

            msg_type = data.get("type")

            # host pokreće sljedeću pjesmu / rundu
            if msg_type == "start_round":

                if player.name == game.host:
                    await game_manager.start_round(lobby_id)

            # igrač šalje odgovor
            elif msg_type == "answer":

                await game_manager.submit_answer(
                    lobby_id,
                    player,
                    data.get("answer")
                )

            # host završava trenutnu pjesmu i računa bodove
            elif msg_type == "finish_song":

                if player.name == game.host:
                    await game_manager.finish_song(lobby_id)

    except WebSocketDisconnect:

        print(f"{player_name} disconnected")