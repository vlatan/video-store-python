from curses.ascii import isupper
from operator import isub
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from wtforms.validators import ValidationError
from app.models import DeletedPost


def video_banned(video_id):
    return DeletedPost.query.filter_by(video_id=video_id).first()


def validate_video(response):
    if response["status"]["privacyStatus"] == "private":
        raise ValidationError("This video is not public.")

    rating = response["contentDetails"].get("contentRating")
    if rating and rating.get("ytRating") == "ytAgeRestricted":
        raise ValidationError("This video is age-restricted.")

    if not response["status"]["embeddable"]:
        raise ValidationError("This video is not embeddable.")

    if response["contentDetails"].get("regionRestriction"):
        raise ValidationError("This video is region-restricted.")

    text_language = response["snippet"].get("defaultLanguage")
    if text_language and not text_language.startswith("en"):
        msg = "This video's title and/or description is not in English."
        raise ValidationError(msg)

    broadcast = response["snippet"].get("liveBroadcastContent")
    if broadcast and broadcast != "none":
        raise ValidationError("This video is not fully broadcasted.")

    duration = convertDuration(response["contentDetails"]["duration"])
    if duration.seconds < 1800:
        raise ValidationError("This video is too short. Minimum length 30 minutes.")

    return True


def normalize_title(title: str) -> str:
    # specific to SLICE source
    title = title.split(" I SLICE ")[0]
    # remove content after //
    title = title.split(" // ")[0]
    # remove content after pipe symbol
    title = title.split(" | ")[0]
    # remove bracketed content
    title = re.sub(r"[\(\[].*?[\)\]]", "", title).strip()
    # remove extra spaces
    title = re.sub(" +", " ", title)

    # split title into words
    words = title.split()

    if words[-1].lower() == "documentary":
        del words[-1]

    # common prepositions
    preps = [
        "at",
        "by",
        "for",
        "in",
        "of",
        "off",
        "the",
        "and",
        "or",
        "nor",
        "a",
        "an",
        "on",
        "out",
        "to",
        "up",
        "as",
        "but",
        "per",
        "via",
        "vs",
        "vs.",
    ]

    # punctuations
    puncts = [":", ".", "!", "?", "-", "—", "–", "//", "--", "|"]

    for i, word in enumerate(words):

        # remove quatation marks at start/end if any and store them
        first_char, last_char = "", ""

        if word[0] in ['"', "'"]:
            first_char, word = word[0], word[1:]

        if word[-1] in ['"', "'"]:
            last_char, word = word[-1], word[:-1]

        # the word is a preposition but not after a punctuation
        if i != 0 and word.lower() in preps and words[i - 1][-1] not in puncts:
            words[i] = first_char + word.lower() + last_char

        # the words is alreay capitalized or an acronym
        elif word[0].isupper():
            words[i] = first_char + word + last_char

        else:  # capitalize any other word
            words[i] = first_char + word.capitalize() + last_char

    return " ".join(words)


def normalize_tags(tags, used):
    duplicate, result = {"documentary", "documentaries"}, ""
    for word in " ".join(tags).split():
        lower_word = word.lower()
        if lower_word not in duplicate and lower_word not in used:
            duplicate.add(lower_word)
            result += word + " "
    return result.strip()


def fetch_video_data(response, playlist_id=None):
    # normalize title
    title = normalize_title(response["snippet"]["title"])

    # remove urls from the description
    if description := response["snippet"].get("description"):
        description = re.sub(r"http\S+", "", description)

    # convert to string and normalize tags
    if tags := response["snippet"].get("tags"):
        used = title.lower() + description.lower()
        tags = normalize_tags(tags, used)

    # convert upload date into Python datetime object
    upload_date = response["snippet"]["publishedAt"]
    upload_date = datetime.strptime(upload_date, "%Y-%m-%dT%H:%M:%SZ")

    return {
        "video_id": response["id"],
        "playlist_id": playlist_id,
        "title": title,
        "thumbnails": response["snippet"]["thumbnails"],
        "description": description,
        "tags": tags,
        "duration": response["contentDetails"]["duration"],
        "upload_date": upload_date,
    }


def parse_video(url):
    parsed = urlparse(url)
    if parsed.hostname and parsed.hostname == "youtu.be":
        return parsed.path[1:]
    elif parsed.hostname and "youtube.com" in parsed.hostname:
        if parsed.path == "/watch":
            if query := parse_qs(parsed.query).get("v"):
                return query[0]
        elif parsed.path[:7] == "/embed/":
            return parsed.path.split("/")[2]
    raise ValidationError("Unable to parse the URL.")


class convertDuration:
    def __init__(self, iso_duration):
        self.iso = iso_duration

    def _compile(self):
        hours = re.compile(r"(\d+)H").search(self.iso)
        minutes = re.compile(r"(\d+)M").search(self.iso)
        seconds = re.compile(r"(\d+)S").search(self.iso)

        h = int(hours.group(1)) if hours else 0
        m = int(minutes.group(1)) if minutes else 0
        s = int(seconds.group(1)) if seconds else 0

        return {"h": h, "m": m, "s": s}

    @property
    def seconds(self):
        d = self._compile()
        return (d["h"] * 3600) + (d["m"] * 60) + d["s"]

    @property
    def human(self):
        d = self._compile()
        h = f"{d['h']:02d}:" if d["h"] else ""
        m, s = f"{d['m']:02d}", f":{d['s']:02d}"
        return h + m + s
