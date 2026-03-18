import asyncio
import random
import time

from services.song_cache import SongCache

song_cache = SongCache()


class GameManager:
    def __init__(self, lobby_manager):
        self.lobby_manager = lobby_manager
        self.round_tasks = {}

    def get_round_duration(self, round_number):
        durations = {
            1: 15,
            2: 10,
            3: 5,
            4: 3
        }
        return durations.get(round_number, 3)

    def generate_year_options(self, correct_year):
        candidates = [
            correct_year - 1,
            correct_year + 1,
            correct_year - 2,
            correct_year + 2,
            correct_year - 3,
            correct_year + 3,
            correct_year - 5,
            correct_year + 5,
        ]

        valid_candidates = [
            year for year in candidates
            if 1950 <= year <= 2026 and year != correct_year
        ]

        random.shuffle(valid_candidates)

        options = [correct_year]
        options.extend(valid_candidates[:3])

        options = list(set(options))
        while len(options) < 4:
            fallback = correct_year + random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
            if 1950 <= fallback <= 2026 and fallback not in options:
                options.append(fallback)

        random.shuffle(options)
        return options

    def normalize_text(self, value):
        return str(value or "").strip().lower()

    def calculate_points(self, submitted_at, answer_phase_started_at, max_time, is_correct):
        if not is_correct:
            return 0

        elapsed_time = submitted_at - answer_phase_started_at

        if elapsed_time < 0:
            elapsed_time = 0

        if elapsed_time > max_time:
            elapsed_time = max_time

        score = int(300 + 700 * (1 - (elapsed_time / max_time)))
        return max(score, 300)

    async def start_round(self, lobby_id):
        game = self.lobby_manager.lobbies[lobby_id]

        if game.current_round > game.total_rounds:
            await self.lobby_manager.broadcast(lobby_id, {
                "type": "game_finished",
                "message": "Igra je završena!"
            })
            return

        decades = song_cache.get_available_decades(min_ready_count=5)

        if not decades:
            await self.lobby_manager.broadcast(lobby_id, {
                "type": "error",
                "message": "Nema dovoljno validiranih pjesama za početak igre."
            })
            return

        random.shuffle(decades)

        song = None
        chosen_decade = None

        for decade in decades:
            found_song = song_cache.get_song(
                decade=decade,
                used_songs=game.used_songs,
                last_artist=game.last_artist
            )

            if found_song is not None:
                song = found_song
                chosen_decade = decade
                print(
                    "ROUND DEBUG | "
                    f"youtube_id={found_song.get('youtube_id')} | "
                    f"title={found_song.get('title')} | "
                    f"artist={found_song.get('artist')} | "
                    f"year={found_song.get('year')} | "
                    f"start_time={found_song.get('start_time')}"
                )
                break

        if song is None:
            await self.lobby_manager.broadcast(lobby_id, {
                "type": "error",
                "message": "Nema dovoljno validiranih pjesama u cacheu."
            })
            return

        game.used_songs.add(song["youtube_id"])
        game.last_artist = song["artist"]

        game.current_song = song
        game.current_decade = chosen_decade
        game.answers = []

        clip_duration = self.get_round_duration(game.current_round)
        answer_window = 15

        now = time.time()
        game.clip_started_at = now
        game.answer_phase_started_at = now
        game.round_ends_at = now + clip_duration + answer_window

        year_options = self.generate_year_options(song["year"])

        payload = {
            "type": "round_started",
            "youtube_id": song["youtube_id"],
            "start_time": song["start_time"],
            "clip_duration": clip_duration,
            "answer_window": answer_window,
            "total_duration": clip_duration + answer_window,
            "decade": chosen_decade,
            "round": game.current_round,
            "song_number": game.current_song_in_round,
            "songs_per_round": game.songs_per_round,
            "clip_started_at": game.clip_started_at,
            "round_ends_at": game.round_ends_at,
            "year_options": year_options,
            "is_host_turn": False
        }

        for player in game.players:
            player_payload = payload.copy()
            player_payload["is_host_turn"] = player.name == game.host
            await player.websocket.send_json(player_payload)

        if lobby_id in self.round_tasks:
            self.round_tasks[lobby_id].cancel()

        self.round_tasks[lobby_id] = asyncio.create_task(
            self.auto_finish_round(lobby_id, clip_duration + answer_window)
        )

    async def auto_finish_round(self, lobby_id, delay):
        try:
            await asyncio.sleep(delay)

            if lobby_id in self.lobby_manager.lobbies:
                await self.finish_song(lobby_id)
        except asyncio.CancelledError:
            pass

    async def submit_answer(self, lobby_id, player, title_answer, artist_answer, year_answer):
        game = self.lobby_manager.lobbies[lobby_id]

        already_answered = any(entry["player"].name == player.name for entry in game.answers)
        if already_answered:
            return

        game.answers.append({
            "player": player,
            "title_answer": title_answer or "",
            "artist_answer": artist_answer or "",
            "year_answer": year_answer,
            "time": time.time()
        })

        if len(game.answers) >= len(game.players):
            await self.finish_song(lobby_id)

    async def finish_song(self, lobby_id):
        game = self.lobby_manager.lobbies[lobby_id]

        if not game.current_song:
            return

        if lobby_id in self.round_tasks:
            self.round_tasks[lobby_id].cancel()
            del self.round_tasks[lobby_id]

        correct_title = self.normalize_text(game.current_song["title"])
        correct_artist = self.normalize_text(game.current_song["artist"])
        correct_year = game.current_song["year"]

        max_time = game.round_ends_at - game.clip_started_at

        sorted_answers = sorted(game.answers, key=lambda x: x["time"])
        awarded_points = []

        for entry in sorted_answers:
            player = entry["player"]
            submitted_at = entry["time"]

            title_answer = self.normalize_text(entry.get("title_answer"))
            artist_answer = self.normalize_text(entry.get("artist_answer"))

            try:
                year_answer = int(entry.get("year_answer"))
            except Exception:
                year_answer = None

            title_correct = bool(title_answer) and title_answer in correct_title
            artist_correct = bool(artist_answer) and artist_answer in correct_artist
            year_correct = year_answer == correct_year

            title_points = self.calculate_points(
                submitted_at, game.answer_phase_started_at, max_time, title_correct
            )
            artist_points = self.calculate_points(
                submitted_at, game.answer_phase_started_at, max_time, artist_correct
            )
            year_points = self.calculate_points(
                submitted_at, game.answer_phase_started_at, max_time, year_correct
            )

            gained_points = title_points + artist_points + year_points
            player.score += gained_points

            awarded_points.append({
                "name": player.name,
                "title_answer": entry.get("title_answer"),
                "artist_answer": entry.get("artist_answer"),
                "year_answer": entry.get("year_answer"),
                "title_correct": title_correct,
                "artist_correct": artist_correct,
                "year_correct": year_correct,
                "gained_points": gained_points,
                "total_score": player.score
            })

        leaderboard = [
            {"name": p.name, "avatar": p.avatar, "score": p.score}
            for p in game.players
        ]
        leaderboard.sort(key=lambda x: x["score"], reverse=True)

        game.blockchain.add_song_result(
            song_title=game.current_song["title"],
            artist=game.current_song["artist"],
            year=game.current_song.get("year"),
            decade=game.current_decade,
            round_number=game.current_round,
            song_number=game.current_song_in_round,
            awarded_points=awarded_points
        )

        await self.lobby_manager.broadcast(lobby_id, {
            "type": "leaderboard",
            "data": leaderboard,
            "round": game.current_round,
            "song_number": game.current_song_in_round,
            "awarded_points": awarded_points,
            "correct_title": game.current_song["title"],
            "correct_artist": game.current_song["artist"],
            "correct_year": game.current_song.get("year"),
            "correct_decade": game.current_decade
        })

        if game.current_song_in_round < game.songs_per_round:
            game.current_song_in_round += 1
        else:
            game.current_song_in_round = 1
            game.current_round += 1

        if game.current_round > game.total_rounds:
            game.blockchain.add_game_finished(leaderboard)

            await self.lobby_manager.broadcast(lobby_id, {
                "type": "game_finished",
                "leaderboard": leaderboard
            })
        else:
            await self.lobby_manager.broadcast(lobby_id, {
                "type": "next_song_ready",
                "next_round": game.current_round,
                "next_song_number": game.current_song_in_round
            })