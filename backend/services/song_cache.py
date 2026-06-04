import os
import random
import re
import threading
import unicodedata

from services.metadata_cache import load_metadata_cache, save_metadata_cache
from services.song_discovery import discover_songs_for_decade
from services.youtube_service import find_replacement_video_for_song, is_video_embeddable


DEFAULT_DISCOVERY_ATTEMPT_BUDGET = 8


class SongCache:
    def __init__(self):
        self.cache = {
            "50s": [],
            "60s": [],
            "70s": [],
            "80s": [],
            "90s": [],
            "2000s": [],
            "2010s": [],
            "2020s": []
        }
        self.decade_priority = {
            "2020s": 0,
            "2010s": 1,
            "2000s": 2,
            "90s": 3,
            "80s": 4,
            "70s": 5,
            "60s": 6,
            "50s": 7
        }
        self.youtube_quota_exceeded = False
        self.cache_lock = threading.RLock()
        self.background_fill_running = False

    def generate_start_time(self, duration_seconds):
        duration_seconds = int(duration_seconds or 180)

        if duration_seconds <= 90:
            return max(0, duration_seconds // 3)

        latest_start = max(20, duration_seconds - 35)
        earliest_start = min(45, latest_start)
        middle_start = int(duration_seconds * 0.45)
        middle_end = int(duration_seconds * 0.65)

        start_min = max(earliest_start, min(middle_start, latest_start))
        start_max = max(start_min, min(middle_end, latest_start))

        return random.randint(start_min, start_max)

    def load_from_metadata_cache(self):
        metadata_cache = load_metadata_cache()

        with self.cache_lock:
            for decade in self.cache.keys():
                self.cache[decade] = []

            for song in metadata_cache.values():
                decade = song.get("decade")
                if decade in self.cache:
                    self.cache[decade].append(song)

    def get_decades_sorted_by_priority(self):
        with self.cache_lock:
            return sorted(
                self.cache.keys(),
                key=lambda decade: (
                    len(self.cache[decade]),
                    self.decade_priority.get(decade, 999)
                )
            )

    def get_discovery_attempt_budget(self, discovery_attempt_budget=None):
        if discovery_attempt_budget is not None:
            return max(0, int(discovery_attempt_budget))

        raw_budget = os.getenv("YOUTUBE_DISCOVERY_ATTEMPT_BUDGET")
        if raw_budget:
            try:
                return max(0, int(raw_budget))
            except ValueError:
                print(
                    "Invalid YOUTUBE_DISCOVERY_ATTEMPT_BUDGET value. "
                    f"Using default={DEFAULT_DISCOVERY_ATTEMPT_BUDGET}"
                )

        return DEFAULT_DISCOVERY_ATTEMPT_BUDGET

    def fill_cache(
        self,
        min_songs_per_decade=5,
        discovery_attempt_budget=None,
        max_results_per_query=12
    ):
        if self.background_fill_running:
            print("Song cache fill already running in background.")
            return

        attempt_budget = self.get_discovery_attempt_budget(discovery_attempt_budget)
        if attempt_budget <= 0:
            print("Song cache fill skipped because discovery attempt budget is 0.")
            return

        self.background_fill_running = True
        print(f"Checking song cache... discovery_attempt_budget={attempt_budget}")
        try:
            self.load_from_metadata_cache()
            attempts_used = 0

            while attempts_used < attempt_budget and not self.youtube_quota_exceeded:
                priority_decades = self.get_decades_sorted_by_priority()

                print(
                    "Priority order: "
                    + ", ".join(
                        f"{decade}({len(self.cache[decade])})"
                        for decade in priority_decades
                    )
                )

                added_this_cycle = False

                for decade in priority_decades:
                    if attempts_used >= attempt_budget:
                        print("Discovery attempt budget reached. Stopping background fill.")
                        break

                    if self.youtube_quota_exceeded:
                        print(f"{decade}: skipping discovery because YouTube quota is exceeded")
                        break

                    with self.cache_lock:
                        current_count = len(self.cache[decade])

                    target_count = current_count + 1

                    print(
                        f"Loading songs for {decade}... "
                        f"current={current_count}, target={target_count}, "
                        f"attempt={attempts_used + 1}/{attempt_budget}"
                    )

                    try:
                        attempts_used += 1
                        discovered = discover_songs_for_decade(
                            decade=decade,
                            target_count=target_count,
                            max_results_per_query=max_results_per_query
                        )
                        with self.cache_lock:
                            self.cache[decade] = discovered

                        new_count = len(discovered)
                        if new_count > current_count:
                            added_this_cycle = True

                        print(f"{decade}: total {new_count} songs in cache")

                    except Exception as e:
                        error_text = str(e).lower()

                        if "quota" in error_text or "quotaexceeded" in error_text:
                            self.youtube_quota_exceeded = True
                            print("YouTube quota exceeded. Stopping further discovery attempts.")
                            break
                        else:
                            print(f"Discovery failed for {decade}: {e}")

                if not added_this_cycle:
                    print("No new songs added in this pass. Stopping background fill.")
                    break

            print("Song cache ready!")
        finally:
            self.background_fill_running = False

    def refill_decade_if_needed(self, decade, min_count=5):
        with self.cache_lock:
            current_count = len(self.cache.get(decade, []))

        if current_count >= min_count:
            return

        if self.youtube_quota_exceeded:
            print(f"Skipping refill for {decade} because YouTube quota is exceeded")
            return

        if self.background_fill_running:
            print(f"Skipping immediate refill for {decade} because background fill is running")
            return

        print(f"Refilling decade {decade} because only {current_count} songs are available...")

        try:
            discovered = discover_songs_for_decade(
                decade=decade,
                target_count=max(min_count, 5),
                max_results_per_query=12
            )
            with self.cache_lock:
                self.cache[decade] = discovered
            print(f"{decade}: total {len(self.cache[decade])} songs after refill")
        except Exception as e:
            error_text = str(e).lower()

            if "quota" in error_text or "quotaexceeded" in error_text:
                self.youtube_quota_exceeded = True
                print("YouTube quota exceeded during refill. Further discovery disabled.")
            else:
                print(f"Refill failed for {decade}: {e}")

    def get_available_decades(self, min_ready_count=5):
        ready = []

        with self.cache_lock:
            cache_snapshot = {
                decade: list(songs)
                for decade, songs in self.cache.items()
            }

        for decade, songs in cache_snapshot.items():
            valid_count = len([
                song for song in songs
                if song.get("youtube_id")
                and song.get("artist")
                and song.get("title")
                and song.get("year") is not None
            ])

            if valid_count >= min_ready_count:
                ready.append(decade)

        return ready

    def replace_song_video(self, song, replacement):
        old_youtube_id = song.get("youtube_id")
        new_youtube_id = replacement.get("youtube_id")

        if not old_youtube_id or not new_youtube_id:
            return False

        song["youtube_id"] = new_youtube_id
        song["channel_title"] = replacement.get("channel_title")
        song["view_count"] = replacement.get("view_count", 0)
        song["duration_seconds"] = replacement.get("duration_seconds", 0)
        song["published_at"] = replacement.get("published_at")
        song["source_query"] = replacement.get("source_query", "replacement_search")
        song["start_time"] = self.generate_start_time(replacement.get("duration_seconds", 180))

        cache = load_metadata_cache()

        if old_youtube_id in cache:
            cached_song = cache.pop(old_youtube_id)
            cached_song.update(song)
            cache[new_youtube_id] = cached_song
        else:
            cache[new_youtube_id] = song.copy()

        save_metadata_cache(cache, allow_deletions=True)
        return True

    def ensure_song_embeddable(self, song, decade):
        youtube_id = song.get("youtube_id")

        if not youtube_id:
            return False

        try:
            if is_video_embeddable(youtube_id):
                return True

            replacement = find_replacement_video_for_song(
                artist=song.get("artist", ""),
                title=song.get("title", ""),
                decade=decade,
                exclude_ids={youtube_id}
            )

            if replacement is None:
                print(
                    "No embeddable replacement found | "
                    f"artist={song.get('artist')} | title={song.get('title')}"
                )
                return False

            replaced = self.replace_song_video(song, replacement)

            if replaced:
                print(
                    "Replaced blocked embed video | "
                    f"old={youtube_id} | new={replacement.get('youtube_id')} | "
                    f"title={song.get('title')} | artist={song.get('artist')}"
                )

            return replaced

        except Exception as e:
            error_text = str(e).lower()

            if "quota" in error_text or "quotaexceeded" in error_text:
                self.youtube_quota_exceeded = True
                print("YouTube quota exceeded while checking embeddable replacement.")
            else:
                print(f"Embeddable replacement failed: {e}")

            return False

    def song_identity(self, song):
        artist = str(song.get("artist", "")).strip().lower()
        title = str(song.get("title", "")).strip().lower()
        year = song.get("year")
        return f"{artist}|{title}|{year}"

    def normalize_artist_text(self, value):
        text = str(value or "").strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(char for char in text if not unicodedata.combining(char))
        text = text.replace("&", " and ")
        text = text.replace("+", " and ")
        text = re.sub(r"[â€™'`Â´]", "", text)
        text = re.sub(r"[-_/.,:;!?()\\[\\]{}\"|]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def artist_identities(self, value):
        normalized = self.normalize_artist_text(value)
        identities = {normalized} if normalized else set()

        for part in re.split(r"\b(?:and|feat|ft|featuring|with|x|y)\b|,", str(value or "").lower()):
            cleaned = self.normalize_artist_text(part)
            if cleaned:
                identities.add(cleaned)

        return identities

    def artist_was_used(self, song, used_artists):
        return bool(self.artist_identities(song.get("artist")) & used_artists)

    def get_song(
        self,
        decade,
        used_songs,
        last_artist,
        used_song_keys=None,
        used_artists=None
    ):
        if decade not in self.cache:
            return None

        used_song_keys = used_song_keys or set()
        used_artists = used_artists or set()

        with self.cache_lock:
            songs_for_decade = list(self.cache[decade])

        available = [
            song for song in songs_for_decade
            if song.get("youtube_id") not in used_songs
            and song.get("artist") != last_artist
            and not self.artist_was_used(song, used_artists)
            and song.get("year") is not None
            and song.get("title")
            and song.get("artist")
            and self.song_identity(song) not in used_song_keys
        ]

        if not available:
            available = [
                song for song in songs_for_decade
                if song.get("youtube_id") not in used_songs
                and not self.artist_was_used(song, used_artists)
                and song.get("year") is not None
                and song.get("title")
                and song.get("artist")
                and self.song_identity(song) not in used_song_keys
            ]

        if not available:
            return None

        random.shuffle(available)

        return available[0]
