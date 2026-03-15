import os
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_song_year_from_musicbrainz(artist, title):

    url = "https://musicbrainz.org/ws/2/recording/"
    params = {
        "query": f'artist:"{artist}" recording:"{title}"',
        "fmt": "json",
        "limit": 5
    }

    headers = {
        "User-Agent": "song-guesser/1.0 (student project)"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()

        if "recordings" not in data:
            return None

        for rec in data["recordings"]:
            if "first-release-date" in rec:
                year = rec["first-release-date"][:4]
                if year.isdigit():
                    return int(year)

    except Exception:
        return None

    return None


def get_song_year_with_ai(artist, title):

    prompt = f"""
What year was this song originally released?

Artist: {artist}
Song: {title}

Return ONLY the year as a number.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        text = response.choices[0].message.content.strip()

        if text.isdigit():
            return int(text)

    except Exception:
        return None

    return None


def get_song_year(artist, title):

    year = get_song_year_from_musicbrainz(artist, title)

    if year is not None:
        return year

    return get_song_year_with_ai(artist, title)


def year_to_decade(year):

    if year is None:
        return None

    if 1950 <= year <= 1959:
        return "50s"
    if 1960 <= year <= 1969:
        return "60s"
    if 1970 <= year <= 1979:
        return "70s"
    if 1980 <= year <= 1989:
        return "80s"
    if 1990 <= year <= 1999:
        return "90s"
    if 2000 <= year <= 2009:
        return "2000s"
    if 2010 <= year <= 2019:
        return "2010s"
    if 2020 <= year <= 2029:
        return "2020s"

    return None