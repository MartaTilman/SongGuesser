from contextlib import asynccontextmanager
import json
import threading
import time

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from blockchain.blockchain import list_saved_blockchains, load_saved_blockchain
from game_manager import GameManager, song_cache
from lobby_manager import LobbyManager
from models.player import Player
from services.metadata_cache import (
    connect_to_database,
    ensure_song_cache_table,
    load_metadata_cache_from_file,
    should_use_database,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        song_cache.load_from_metadata_cache()
        print("Song cache loaded from local metadata cache.")

        background_fill_thread = threading.Thread(
            target=song_cache.fill_cache,
            kwargs={"min_songs_per_decade": 5},
            daemon=True
        )
        background_fill_thread.start()
        print("Song cache background fill started.")
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
    return {
        "status": "backend running",
        "cache_background_fill_running": song_cache.background_fill_running
    }


@app.get("/cache/status")
def get_cache_status():
    if should_use_database():
        try:
            with connect_to_database() as conn:
                ensure_song_cache_table(conn)

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COUNT(*), MAX(updated_at)
                        FROM song_metadata_cache
                        """
                    )
                    song_count, latest_update = cur.fetchone()

            return {
                "using_database": True,
                "database_connected": True,
                "song_count": song_count,
                "latest_update": latest_update.isoformat() if latest_update else None,
                "cache_background_fill_running": song_cache.background_fill_running
            }
        except Exception:
            return {
                "using_database": True,
                "database_connected": False,
                "song_count": None,
                "latest_update": None,
                "cache_background_fill_running": song_cache.background_fill_running
            }

    file_cache = load_metadata_cache_from_file()
    return {
        "using_database": False,
        "database_connected": False,
        "song_count": len(file_cache),
        "latest_update": None,
        "cache_background_fill_running": song_cache.background_fill_running
    }


@app.post("/lobbies")
def create_lobby():
    lobby = lobby_manager.create_lobby()
    return {"lobby_id": lobby.id}


@app.get("/lobbies")
def get_lobbies():
    return list(lobby_manager.lobbies.keys())


@app.get("/lobby/{lobby_id}/players")
def get_players(lobby_id: str):
    lobby = lobby_manager.lobbies.get(lobby_id.upper())

    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")

    return [player.to_dict() for player in lobby.players]


@app.get("/lobby/{lobby_id}/info")
def get_lobby_info(lobby_id: str):
    lobby = lobby_manager.lobbies.get(lobby_id.upper())

    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")

    return {
        "lobby_id": lobby.id,
        "host": lobby.host,
        "players": [player.to_dict() for player in lobby.players],
        "current_round": lobby.current_round,
        "current_game_number": lobby.current_game_number,
        "current_song_in_round": lobby.current_song_in_round,
        "songs_per_round": game_manager.get_songs_per_round(lobby),
        "total_rounds": lobby.total_rounds,
    }


@app.get("/lobby/{lobby_id}/state")
async def get_lobby_state(lobby_id: str, player_name: str = None):
    normalized_lobby_id = lobby_id.upper()
    lobby = lobby_manager.lobbies.get(normalized_lobby_id)

    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")

    if lobby.last_result_payload is not None:
        return {
            "phase": "leaderboard",
            "message": game_manager.build_result_payload(
                lobby.last_result_payload,
                player_name
            )
        }

    if lobby.current_song is not None and time.time() >= lobby.round_ends_at:
        await game_manager.finish_song(normalized_lobby_id)

        if lobby.last_result_payload is not None:
            return {
                "phase": "leaderboard",
                "message": game_manager.build_result_payload(
                    lobby.last_result_payload,
                    player_name
                )
            }

    if lobby.current_song is not None:
        player = next(
            (p for p in lobby.players if p.name == player_name),
            None
        )

        return {
            "phase": "round",
            "message": game_manager.build_round_payload(lobby, player)
        }

    return {
        "phase": "lobby",
        "game_number": lobby.current_game_number,
        "round": lobby.current_round,
        "song_number": lobby.current_song_in_round
    }


@app.get("/lobby/{lobby_id}/blockchain")
def get_blockchain(lobby_id: str):
    lobby = lobby_manager.lobbies.get(lobby_id.upper())

    if lobby:
        return {
            "valid": lobby.blockchain.is_valid(),
            "consensus": "proof_of_work",
            "difficulty": lobby.blockchain.difficulty,
            "chain": lobby.blockchain.to_list()
        }

    saved_chain = load_saved_blockchain(lobby_id)
    if saved_chain is None:
        raise HTTPException(status_code=404, detail="Lobby not found")

    return {
        "valid": saved_chain.get("valid", False),
        "chain": saved_chain.get("chain", [])
    }


@app.get("/lobby/{lobby_id}/blockchain/final-proof")
def get_blockchain_final_proof(lobby_id: str):
    lobby = lobby_manager.lobbies.get(lobby_id.upper())

    if lobby:
        chain = lobby.blockchain.to_list()
    else:
        saved_chain = load_saved_blockchain(lobby_id)
        if saved_chain is None:
            raise HTTPException(status_code=404, detail="Lobby not found")

        chain = saved_chain.get("chain", [])

    for block in reversed(chain):
        data = block.get("data", {})
        if data.get("type") == "game_finished" and data.get("final_proof"):
            return data["final_proof"]

    raise HTTPException(status_code=404, detail="Final proof not found")


@app.get("/blockchain/history")
def get_blockchain_history():
    return {"games": list_saved_blockchains()}


@app.get("/blockchain/history/{lobby_id}")
def get_blockchain_history_entry(lobby_id: str):
    saved_chain = load_saved_blockchain(lobby_id)

    if saved_chain is None:
        raise HTTPException(status_code=404, detail="Saved blockchain not found")

    return saved_chain


@app.websocket("/ws/{lobby_id}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, lobby_id: str, player_name: str):
    await websocket.accept()

    avatar = websocket.query_params.get("avatar", "🎵")
    public_key = None
    join_signature = None

    try:
        raw_public_key = websocket.query_params.get("public_key")
        raw_join_signature = websocket.query_params.get("join_signature")

        if raw_public_key:
            public_key = json.loads(raw_public_key)

        if raw_join_signature:
            join_signature = json.loads(raw_join_signature)
    except json.JSONDecodeError:
        await websocket.send_json({
            "type": "error",
            "message": "Wallet podaci nisu validan JSON."
        })
        await websocket.close()
        return

    player = Player(player_name, websocket, avatar, public_key, join_signature)
    normalized_lobby_id = lobby_id.upper()

    try:
        game = lobby_manager.join_lobby(normalized_lobby_id, player)

        await lobby_manager.broadcast(normalized_lobby_id, {
            "type": "lobby_update",
            "host": game.host,
            "players": [p.to_dict() for p in game.players]
        })

        if game.last_result_payload is not None:
            await websocket.send_json(
                game_manager.build_result_payload(
                    game.last_result_payload,
                    player.name
                )
            )
        elif game.current_song is not None:
            await websocket.send_json(game_manager.build_round_payload(game, player))

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "start_round":
                if player.name == game.host:
                    await game_manager.start_round(normalized_lobby_id)

            elif msg_type == "reset_game":
                if player.name == game.host:
                    game.reset_for_next_game()
                    await lobby_manager.broadcast(normalized_lobby_id, {
                        "type": "lobby_update",
                        "host": game.host,
                        "players": [p.to_dict() for p in game.players],
                        "game_number": game.current_game_number
                    })

            elif msg_type == "answer":
                await game_manager.submit_answer(
                    normalized_lobby_id,
                    player,
                    data.get("title_answer"),
                    data.get("artist_answer"),
                    data.get("year_answer"),
                    data.get("signature")
                )

            elif msg_type == "finish_song":
                if player.name == game.host:
                    await game_manager.finish_song(normalized_lobby_id)

            elif msg_type == "report_player_error":
                youtube_id = data.get("youtube_id")
                if (
                    player.name == game.host
                    and game.current_song
                    and game.current_song.get("youtube_id") == youtube_id
                    and not game.finishing_song
                ):
                    print(
                        f"Player error {data.get('code')} reported for {youtube_id} "
                        f"by host {player.name} — swapping video in same round"
                    )
                    await game_manager.swap_video(normalized_lobby_id, youtube_id)

            elif msg_type == "sync_state":
                if game.last_result_payload is not None:
                    await websocket.send_json(
                        game_manager.build_result_payload(
                            game.last_result_payload,
                            player.name
                        )
                    )
                elif game.current_song is not None and time.time() >= game.round_ends_at:
                    await game_manager.finish_song(normalized_lobby_id)
                elif game.current_song is not None:
                    await websocket.send_json(
                        game_manager.build_round_payload(game, player)
                    )

    except ValueError as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        await websocket.close()

    except WebSocketDisconnect:
        updated_lobby = lobby_manager.remove_player_connection(normalized_lobby_id, player)

        if updated_lobby:
            await lobby_manager.broadcast(normalized_lobby_id, {
                "type": "lobby_update",
                "host": updated_lobby.host,
                "players": [p.to_dict() for p in updated_lobby.players]
            })

        print(f"{player_name} disconnected")

    except Exception as e:
        print(f"WebSocket error for {player_name} in lobby {normalized_lobby_id}: {e}")

        updated_lobby = lobby_manager.remove_player_connection(normalized_lobby_id, player)

        if updated_lobby:
            try:
                await lobby_manager.broadcast(normalized_lobby_id, {
                    "type": "lobby_update",
                    "host": updated_lobby.host,
                    "players": [p.to_dict() for p in updated_lobby.players]
                })
            except Exception as broadcast_error:
                print(f"Broadcast after error failed: {broadcast_error}")
