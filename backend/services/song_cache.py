import random
from services.youtube_service import fetch_songs_for_decade


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

    def fill_cache(self):

        print("Checking song cache...")

        for decade in self.cache.keys():

            # puni samo ako dekada ima premalo pjesama
            if len(self.cache[decade]) < 5:

                print(f"Loading songs for {decade}...")

                songs = fetch_songs_for_decade(decade)

                existing_ids = {song["youtube_id"] for song in self.cache[decade]}

                for song in songs:
                    if song["youtube_id"] not in existing_ids:
                        self.cache[decade].append(song)

                print(f"{decade}: {len(self.cache[decade])} songs in cache")

        print("Song cache ready!")

    def get_song(self, decade, used_songs, last_artist):

        available = [
            song for song in self.cache[decade]
            if song["youtube_id"] not in used_songs
            and song["artist"] != last_artist
        ]

        if not available:
            return None

        return random.choice(available)