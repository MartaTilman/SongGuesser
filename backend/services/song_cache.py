import random

from services.metadata_cache import load_metadata_cache
from services.song_discovery import discover_songs_for_decade


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
        self.youtube_quota_exceeded = False

    def load_from_metadata_cache(self):
        metadata_cache = load_metadata_cache()

        for decade in self.cache.keys():
            self.cache[decade] = []

        for song in metadata_cache.values():
            decade = song.get("decade")
            if decade in self.cache:
                self.cache[decade].append(song)

    def fill_cache(self, min_songs_per_decade=5):
        print("Checking song cache...")

        self.load_from_metadata_cache()

        for decade in self.cache.keys():
            current_count = len(self.cache[decade])

            if current_count >= min_songs_per_decade:
                print(f"{decade}: already has {current_count} songs")
                continue

            if self.youtube_quota_exceeded:
                print(f"{decade}: skipping discovery because YouTube quota is exceeded")
                continue

            print(f"Loading songs for {decade}... current={current_count}, target={min_songs_per_decade}")

            try:
                discovered = discover_songs_for_decade(
                    decade=decade,
                    target_count=min_songs_per_decade,
                    max_results_per_query=10
                )
                self.cache[decade] = discovered
                print(f"{decade}: total {len(self.cache[decade])} songs in cache")

            except Exception as e:
                error_text = str(e).lower()

                if "quota" in error_text or "quotaexceeded" in error_text:
                    self.youtube_quota_exceeded = True
                    print("YouTube quota exceeded. Stopping further discovery attempts.")
                else:
                    print(f"Discovery failed for {decade}: {e}")

        print("Song cache ready!")

    def refill_decade_if_needed(self, decade, min_count=5):
        current_count = len(self.cache.get(decade, []))

        if current_count >= min_count:
            return

        if self.youtube_quota_exceeded:
            return

        print(f"Refilling decade {decade} because only {current_count} songs are available...")

        try:
            discovered = discover_songs_for_decade(
                decade=decade,
                target_count=max(min_count, 5),
                max_results_per_query=10
            )
            self.cache[decade] = discovered

        except Exception as e:
            error_text = str(e).lower()

            if "quota" in error_text or "quotaexceeded" in error_text:
                self.youtube_quota_exceeded = True
                print("YouTube quota exceeded during refill. Further discovery disabled.")
            else:
                print(f"Refill failed for {decade}: {e}")

    def get_available_decades(self, min_ready_count=5):
        ready = []

        for decade, songs in self.cache.items():
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

    def get_song(self, decade, used_songs, last_artist):
        if decade not in self.cache:
            return None

        self.refill_decade_if_needed(decade, min_count=5)

        available = [
            song for song in self.cache[decade]
            if song.get("youtube_id") not in used_songs
            and song.get("artist") != last_artist
            and song.get("year") is not None
            and song.get("title")
            and song.get("artist")
        ]

        if not available:
            available = [
                song for song in self.cache[decade]
                if song.get("youtube_id") not in used_songs
                and song.get("year") is not None
                and song.get("title")
                and song.get("artist")
            ]

        if not available:
            return None

        return random.choice(available)