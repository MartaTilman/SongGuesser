import random
import time
from services.song_cache import SongCache

song_cache = SongCache()
song_cache.fill_cache()


class GameManager:

    def __init__(self, lobby_manager):

        self.lobby_manager = lobby_manager

    def get_round_duration(self, round_number):

        durations = {
            1: 15,
            2: 10,
            3: 5,
            4: 3
        }

        return durations.get(round_number, 3)

    async def start_round(self, lobby_id):

        game = self.lobby_manager.lobbies[lobby_id]

        # ako je igra gotova
        if game.current_round > game.total_rounds:
            for player in game.players:
                await player.websocket.send_json({
                    "type": "game_finished",
                    "message": "Igra je završena!"
                })
            return

        decades = ["50s", "60s", "70s", "80s", "90s", "2000s", "2010s", "2020s"]
        random.shuffle(decades)

        song = None
        chosen_decade = None

        for decade in decades:

            song = song_cache.get_song(
                decade,
                game.used_songs,
                game.last_artist
            )

            if song is not None:
                chosen_decade = decade
                break

        if song is None:
            for player in game.players:
                await player.websocket.send_json({
                    "type": "error",
                    "message": "Nema više dostupnih pjesama u cacheu."
                })
            return

        game.used_songs.add(song["youtube_id"])
        game.last_artist = song["artist"]

        game.current_song = song
        game.answers = []
        game.current_decade = chosen_decade
        duration = self.get_round_duration(game.current_round)

        for player in game.players:

            if player.name == game.host:

                await player.websocket.send_json({
                    "type": "play_song",
                    "youtube_id": song["youtube_id"],
                    "start_time": song["start_time"],
                    "duration": duration,
                    "decade": chosen_decade,
                    "round": game.current_round,
                    "song_number": game.current_song_in_round,
                    "songs_per_round": game.songs_per_round
                })

            else:

                await player.websocket.send_json({
                    "type": "waiting_for_song",
                    "decade": chosen_decade,
                    "round": game.current_round,
                    "song_number": game.current_song_in_round,
                    "songs_per_round": game.songs_per_round,
                    "duration": duration
                })

    async def submit_answer(self, lobby_id, player, answer):

        game = self.lobby_manager.lobbies[lobby_id]

        game.answers.append({
            "player": player,
            "answer": answer,
            "time": time.time()
        })

    async def finish_song(self, lobby_id):

        game = self.lobby_manager.lobbies[lobby_id]

        correct = game.current_song["title"]

        sorted_answers = sorted(game.answers, key=lambda x: x["time"])

        position = 0

        for entry in sorted_answers:

            player = entry["player"]
            answer = entry["answer"]

            # ako answer dolazi kao string
            if isinstance(answer, str):
                user_answer = answer.lower()
            else:
                user_answer = str(answer).lower()

            if user_answer in correct.lower():

                score = max(10 - position, 1)
                player.score += score

            position += 1

        leaderboard = [
            {"name": p.name, "score": p.score}
            for p in game.players
        ]

        leaderboard.sort(key=lambda x: x["score"], reverse=True)

        game.blockchain.add_block({
            "type": "round_result",
            "song": game.current_song["title"],
            "artist": game.current_song["artist"],
            "round": game.current_round,
            "song_number": game.current_song_in_round,
            "players": [
                {"name": p.name, "score": p.score}
                for p in game.players
            ],
            "timestamp": time.time()
        })

        for p in game.players:

            await p.websocket.send_json({
                "type": "leaderboard",
                "data": leaderboard,
                "round": game.current_round,
                "song_number": game.current_song_in_round
            })

        # pomak na sljedeću pjesmu / rundu
        if game.current_song_in_round < game.songs_per_round:
            game.current_song_in_round += 1
        else:
            game.current_song_in_round = 1
            game.current_round += 1

        # obavijesti frontend što dalje
        if game.current_round > game.total_rounds:
            for p in game.players:
                await p.websocket.send_json({
                    "type": "game_finished",
                    "leaderboard": leaderboard
                })
        else:
            for p in game.players:
                await p.websocket.send_json({
                    "type": "next_song_ready",
                    "next_round": game.current_round,
                    "next_song_number": game.current_song_in_round
                })