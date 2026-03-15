import uuid
from models.game import Game
from blockchain.blockchain import Blockchain


class Lobby:

    def __init__(self, lobby_id, host):

        self.id = lobby_id
        self.host = host
        self.players = []
        self.answers = []
        self.current_song = None
        self.used_songs = set()
        self.last_artist = None
        self.current_round = 1
        self.current_song_in_round = 1
        self.songs_per_round = 5
        self.total_rounds = 4
        self.blockchain = Blockchain()


class LobbyManager:

    def __init__(self):
        self.lobbies = {}

    def join_lobby(self, lobby_id, player):

        if lobby_id not in self.lobbies:

            lobby = Lobby(lobby_id, player.name)
            self.lobbies[lobby_id] = lobby

        else:

            lobby = self.lobbies[lobby_id]

        lobby.players.append(player)

        lobby.blockchain.add_block({
            "type": "player_join",
            "player": player.name
        })

        return lobby