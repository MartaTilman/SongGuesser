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

    def calculate_kahoot_score(self, elapsed_time, max_time):

        if elapsed_time < 0:
            elapsed_time = 0

        if elapsed_time > max_time:
            elapsed_time = max_time

        # Kahoot stil: točan odgovor daje između 500 i 1000 bodova
        score = int(500 + 500 * (1 - (elapsed_time / max_time)))

        return max(score, 500)

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

        # traži pjesmu koja nije već korištena u ovom lobbyju
        # i da nije isti izvođač kao prošli put
        for decade in decades:

            song = song_cache.get_song(
                decade,
                game.used_songs,
                game.last_artist
            )

            if song is not None:
                chosen_decade = decade
                break

        # ako nema više pjesama
        if song is None:
            for player in game.players:
                await player.websocket.send_json({
                    "type": "error",
                    "message": "Nema više dostupnih pjesama u cacheu."
                })
            return

        # označi pjesmu kao korištenu u ovom lobbyju
        game.used_songs.add(song["youtube_id"])
        game.last_artist = song["artist"]

        game.current_song = song
        game.current_decade = chosen_decade
        game.answers = []

        duration = self.get_round_duration(game.current_round)

        # vrijeme kada završava pjesma i kreće odgovaranje
        game.answer_phase_started_at = time.time() + duration

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

        correct_title = game.current_song["title"]

        # koliko sekundi igrači imaju za upis odgovora nakon pjesme
        answer_window = 10

        # sortiraj odgovore po vremenu
        sorted_answers = sorted(game.answers, key=lambda x: x["time"])

        # ovdje spremamo bodove osvojene baš za ovu pjesmu
        awarded_points = []

        for entry in sorted_answers:

            player = entry["player"]
            answer = entry["answer"]
            submitted_at = entry["time"]

            if isinstance(answer, str):
                user_answer = answer.lower().strip()
            else:
                user_answer = str(answer).lower().strip()

            gained_points = 0
            is_correct = False

            # bodove dobiva samo točan odgovor
            if user_answer in correct_title.lower():

                is_correct = True

                elapsed = submitted_at - game.answer_phase_started_at

                gained_points = self.calculate_kahoot_score(
                    elapsed_time=elapsed,
                    max_time=answer_window
                )

                player.score += gained_points

            awarded_points.append({
                "name": player.name,
                "answer": answer,
                "correct": is_correct,
                "gained_points": gained_points,
                "total_score": player.score
            })

        leaderboard = [
            {"name": p.name, "score": p.score}
            for p in game.players
        ]

        leaderboard.sort(key=lambda x: x["score"], reverse=True)

        # zapis na blockchain za ovu pjesmu
        game.blockchain.add_song_result(
            song_title=game.current_song["title"],
            artist=game.current_song["artist"],
            year=game.current_song.get("year"),
            decade=game.current_decade,
            round_number=game.current_round,
            song_number=game.current_song_in_round,
            awarded_points=awarded_points
        )

        for p in game.players:

            await p.websocket.send_json({
                "type": "leaderboard",
                "data": leaderboard,
                "round": game.current_round,
                "song_number": game.current_song_in_round,
                "awarded_points": awarded_points
            })

        # pomak na sljedeću pjesmu / rundu
        if game.current_song_in_round < game.songs_per_round:
            game.current_song_in_round += 1
        else:
            game.current_song_in_round = 1
            game.current_round += 1

        # ako je igra gotova, spremi finalni leaderboard na blockchain
        if game.current_round > game.total_rounds:

            game.blockchain.add_game_finished(leaderboard)

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