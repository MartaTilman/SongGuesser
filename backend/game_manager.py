import asyncio
import random
import re
import time
import unicodedata
from difflib import SequenceMatcher

from blockchain.blockchain import create_song_commitment
from services.song_cache import SongCache

song_cache = SongCache()


class GameManager:
    def __init__(self, lobby_manager):
        self.lobby_manager = lobby_manager
        self.round_tasks = {}
        self.round_countdown_seconds = 4

    def get_round_duration(self, round_number):
        durations = {
            1: 15,
            2: 12,
            3: 9,
        }
        return durations.get(round_number, 6)

    def get_songs_per_round(self, game, round_number=None):
        target_round = round_number or game.current_round
        configured_counts = getattr(game, "songs_per_round_by_round", None)

        if configured_counts:
            return configured_counts.get(target_round, game.songs_per_round)

        return game.songs_per_round

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
        text = str(value or "").strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if not unicodedata.combining(char))
        text = text.replace("&", " and ")
        text = text.replace("+", " and ")
        text = re.sub(r"[’'`´]", "", text)
        text = re.sub(r"[-_/.,:;!?()\\[\\]{}\"|]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def simplify_artist_text(self, value):
        text = self.normalize_text(value)
        text = re.sub(r"\b(feat|ft|featuring|with|w/)\b.*$", "", text).strip()
        text = re.sub(r"\b(presents|pres|vs|versus)\b.*$", "", text).strip()
        text = re.sub(r"\b(and|x|y)\b", " ", text)

        filtered_tokens = [
            token for token in text.split(" ")
            if token and token not in {
                "the", "a", "an",
                "dj", "mc",
                "official", "audio", "video",
                "lyrics", "lyric", "version",
                "radio", "edit", "mix",
                "remaster", "remastered"
            }
        ]

        return " ".join(filtered_tokens).strip()

    def get_artist_identities(self, value):
        normalized = self.normalize_text(value)
        simplified = self.simplify_artist_text(value)
        identities = {item for item in [normalized, simplified] if item}

        for part in re.split(r"\b(?:and|feat|ft|featuring|with|x|y)\b|,", str(value or "").lower()):
            simplified_part = self.simplify_artist_text(part)
            if simplified_part:
                identities.add(simplified_part)

        return identities

    def simplify_title_text(self, value):
        text = self.normalize_text(value)
        text = re.sub(r"\b(feat|ft|featuring)\b.*$", "", text).strip()

        filtered_tokens = [
            token for token in text.split(" ")
            if token and token not in {
                "the", "a", "an",
                "official", "audio", "video",
                "lyrics", "lyric", "version",
                "radio", "edit", "mix",
                "remaster", "remastered",
                "mono", "stereo"
            }
        ]

        return " ".join(filtered_tokens).strip()

    def token_set(self, value):
        return {token for token in str(value or "").split(" ") if token}

    def text_matches(self, submitted_value, correct_value, mode="default"):
        if mode == "artist":
            submitted_normalized = self.simplify_artist_text(submitted_value)
            correct_normalized = self.simplify_artist_text(correct_value)
        elif mode == "title":
            submitted_normalized = self.simplify_title_text(submitted_value)
            correct_normalized = self.simplify_title_text(correct_value)
        else:
            submitted_normalized = self.normalize_text(submitted_value)
            correct_normalized = self.normalize_text(correct_value)

        if not submitted_normalized or not correct_normalized:
            return False

        if submitted_normalized == correct_normalized:
            return True

        if submitted_normalized in correct_normalized:
            return True

        length_gap = abs(len(submitted_normalized) - len(correct_normalized))
        similarity = SequenceMatcher(None, submitted_normalized, correct_normalized).ratio()

        if len(correct_normalized) >= 5 and length_gap <= 1 and similarity >= 0.88:
            return True

        submitted_tokens = self.token_set(submitted_normalized)
        correct_tokens = self.token_set(correct_normalized)

        if not submitted_tokens or not correct_tokens:
            return False

        if submitted_tokens.issubset(correct_tokens):
            return True

        overlap = len(submitted_tokens & correct_tokens)
        if overlap >= max(1, len(correct_tokens) - 1):
            return True

        fuzzy_token_matches = 0

        for submitted_token in submitted_tokens:
            for correct_token in correct_tokens:
                token_length_gap = abs(len(submitted_token) - len(correct_token))
                token_similarity = SequenceMatcher(None, submitted_token, correct_token).ratio()

                if submitted_token == correct_token:
                    fuzzy_token_matches += 1
                    break

                if len(correct_token) >= 4 and token_length_gap <= 1 and token_similarity >= 0.8:
                    fuzzy_token_matches += 1
                    break

        return fuzzy_token_matches >= max(1, len(correct_tokens) - 1)

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

    def get_min_ready_count(self, game):
        remaining_songs = 0

        for round_number in range(game.current_round, game.total_rounds + 1):
            songs_in_round = self.get_songs_per_round(game, round_number)

            if round_number == game.current_round:
                remaining_songs += max(0, songs_in_round - game.current_song_in_round + 1)
            else:
                remaining_songs += songs_in_round

        remaining_songs = max(
            1,
            remaining_songs
        )

        return min(5, remaining_songs)

    def build_round_payload(self, game, player=None):
        if not game.current_song:
            return None

        clip_duration = self.get_round_duration(game.current_round)
        answer_window = 15

        if not hasattr(game, "year_options") or not game.year_options:
            game.year_options = self.generate_year_options(game.current_song["year"])

        return {
            "type": "round_started",
            "game_number": game.current_game_number,
            "youtube_id": game.current_song["youtube_id"],
            "start_time": game.current_song["start_time"],
            "clip_duration": clip_duration,
            "answer_window": answer_window,
            "countdown_seconds": self.round_countdown_seconds,
            "total_duration": clip_duration + answer_window,
            "decade": game.current_decade,
            "round": game.current_round,
            "song_number": game.current_song_in_round,
            "songs_per_round": self.get_songs_per_round(game),
            "clip_started_at": game.clip_started_at,
            "round_ends_at": game.round_ends_at,
            "server_time": time.time(),
            "year_options": game.year_options,
            "is_host_turn": bool(player and player.name == game.host)
        }

    def build_result_payload(self, result_payload, player_name=None):
        if not result_payload:
            return None

        payload = result_payload.copy()
        awarded_points = result_payload.get("awarded_points") or []

        if player_name:
            payload["awarded_points"] = [
                item for item in awarded_points
                if item.get("name") == player_name
            ]

        return payload

    async def send_result_payloads(self, lobby_id, result_payload):
        game = self.lobby_manager.lobbies.get(lobby_id)
        if not game:
            return

        disconnected = []

        for player in game.players:
            try:
                await player.websocket.send_json(
                    self.build_result_payload(result_payload, player.name)
                )
            except Exception:
                disconnected.append(player)

        for player in disconnected:
            self.lobby_manager.remove_player_connection(lobby_id, player)

    async def start_round(self, lobby_id):
        game = self.lobby_manager.lobbies[lobby_id]

        if not hasattr(game, "used_song_keys"):
            game.used_song_keys = set()

        if game.current_round > game.total_rounds:
            await self.lobby_manager.broadcast(lobby_id, {
                "type": "game_finished",
                "message": "Igra je završena!"
            })
            return

        min_ready_count = self.get_min_ready_count(game)
        decades = song_cache.get_available_decades(min_ready_count=min_ready_count)

        if not decades:
            decades = song_cache.get_available_decades(min_ready_count=1)

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
                last_artist=game.last_artist,
                used_song_keys=game.used_song_keys,
                used_artists=game.used_artists
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
        game.used_song_keys.add(
            f"{self.normalize_text(song.get('artist'))}|{self.normalize_text(song.get('title'))}|{song.get('year')}"
        )
        game.used_artists.update(self.get_artist_identities(song.get("artist")))
        game.last_artist = song["artist"]

        game.current_song = song
        game.current_decade = chosen_decade
        game.finishing_song = False
        game.answers = []
        game.last_result_payload = None

        game.blockchain.add_round_started(
            game_number=game.current_game_number,
            round_number=game.current_round,
            song_number=game.current_song_in_round,
            decade=chosen_decade,
            song_commitment=create_song_commitment(
                lobby_id,
                game.current_game_number,
                game.current_round,
                game.current_song_in_round,
                song
            )
        )

        clip_duration = self.get_round_duration(game.current_round)
        answer_window = 15
        countdown_seconds = self.round_countdown_seconds

        now = time.time()
        game.clip_started_at = now + countdown_seconds
        game.answer_phase_started_at = game.clip_started_at
        game.round_ends_at = game.clip_started_at + clip_duration + answer_window

        game.year_options = self.generate_year_options(song["year"])

        for player in game.players:
            await player.websocket.send_json(self.build_round_payload(game, player))

        if lobby_id in self.round_tasks:
            self.round_tasks[lobby_id].cancel()

        self.round_tasks[lobby_id] = asyncio.create_task(
            self.auto_finish_round(lobby_id, countdown_seconds + clip_duration + answer_window + 1)
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

        if not game.current_song or game.finishing_song:
            return

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

    async def finish_song(self, lobby_id):
        game = self.lobby_manager.lobbies[lobby_id]

        if not game.current_song or game.finishing_song:
            return

        game.finishing_song = True

        try:
            round_task = self.round_tasks.get(lobby_id)
            if round_task is not None:
                if round_task is not asyncio.current_task():
                    round_task.cancel()
                del self.round_tasks[lobby_id]

            correct_title = self.normalize_text(game.current_song["title"])
            correct_artist = self.normalize_text(game.current_song["artist"])
            correct_year = game.current_song["year"]

            max_time = game.round_ends_at - game.clip_started_at

            sorted_answers = sorted(game.answers, key=lambda x: x["time"])
            awarded_points = []
            answered_player_names = set()

            for entry in sorted_answers:
                player = entry["player"]
                answered_player_names.add(player.name)
                submitted_at = entry["time"]

                title_answer = self.normalize_text(entry.get("title_answer"))
                artist_answer = self.normalize_text(entry.get("artist_answer"))

                try:
                    year_answer = int(entry.get("year_answer"))
                except Exception:
                    year_answer = None

                title_correct = self.text_matches(title_answer, correct_title, mode="title")
                artist_correct = self.text_matches(artist_answer, correct_artist, mode="artist")
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

            for player in game.players:
                if player.name in answered_player_names:
                    continue

                awarded_points.append({
                    "name": player.name,
                    "title_answer": "",
                    "artist_answer": "",
                    "year_answer": None,
                    "title_correct": False,
                    "artist_correct": False,
                    "year_correct": False,
                    "gained_points": 0,
                    "total_score": player.score
                })

            leaderboard = [
                {"name": p.name, "avatar": p.avatar, "score": p.score}
                for p in game.players
            ]
            leaderboard.sort(key=lambda x: x["score"], reverse=True)

            game.blockchain.add_song_result(
                game_number=game.current_game_number,
                song_title=game.current_song["title"],
                artist=game.current_song["artist"],
                year=game.current_song.get("year"),
                decade=game.current_decade,
                round_number=game.current_round,
                song_number=game.current_song_in_round,
                awarded_points=awarded_points,
                song_commitment=create_song_commitment(
                    lobby_id,
                    game.current_game_number,
                    game.current_round,
                    game.current_song_in_round,
                    game.current_song
                )
            )

            result_payload = {
                "type": "leaderboard",
                "game_number": game.current_game_number,
                "data": leaderboard,
                "round": game.current_round,
                "song_number": game.current_song_in_round,
                "awarded_points": awarded_points,
                "correct_title": game.current_song["title"],
                "correct_artist": game.current_song["artist"],
                "correct_year": game.current_song.get("year"),
                "correct_decade": game.current_decade
            }
            game.last_result_payload = result_payload

            await self.send_result_payloads(lobby_id, result_payload)

            songs_in_current_round = self.get_songs_per_round(game)

            if game.current_song_in_round < songs_in_current_round:
                game.current_song_in_round += 1
            else:
                game.current_song_in_round = 1
                game.current_round += 1
                game.songs_per_round = self.get_songs_per_round(game)

            game.current_song = None
            game.current_decade = None

            if game.current_round > game.total_rounds:
                game.blockchain.add_game_finished(game.current_game_number, leaderboard)

                await self.lobby_manager.broadcast(lobby_id, {
                    "type": "game_finished",
                    "game_number": game.current_game_number,
                    "leaderboard": leaderboard
                })
            else:
                await self.lobby_manager.broadcast(lobby_id, {
                    "type": "next_song_ready",
                    "next_round": game.current_round,
                    "next_song_number": game.current_song_in_round
                })
        finally:
            game.finishing_song = False
