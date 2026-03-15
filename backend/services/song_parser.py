import json
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def parse_song_with_regex(youtube_title):

    cleaned = re.sub(r"\(.*?\)", "", youtube_title)
    cleaned = re.sub(r"\[.*?\]", "", cleaned)
    cleaned = cleaned.replace("Official Video", "")
    cleaned = cleaned.replace("OFFICIAL VIDEO", "")
    cleaned = cleaned.replace("Official Music Video", "")
    cleaned = cleaned.strip()

    if "-" in cleaned:
        parts = cleaned.split("-", 1)

        artist = parts[0].strip()
        title = parts[1].strip()

        if artist and title:
            return {
                "artist": artist,
                "title": title
            }

    return None


def parse_song_with_ai(youtube_title):

    prompt = f"""
Extract the artist and song title from this YouTube video title.

Title: {youtube_title}

Return ONLY valid JSON:
{{
  "artist": "...",
  "title": "..."
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    text = response.choices[0].message.content.strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())

    return {
        "artist": "Unknown",
        "title": youtube_title
    }


def parse_song_from_title(youtube_title):

    parsed = parse_song_with_regex(youtube_title)

    if parsed is not None:
        return parsed

    return parse_song_with_ai(youtube_title)