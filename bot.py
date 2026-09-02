import os
import json
import html
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import feedparser
import requests


BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@cricbuzzscom")

# Sirf recent cricket news
RSS_URLS = [
    "https://news.google.com/rss/search?q=cricket%20when%3A1d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=India%20cricket%20when%3A1d&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=cricket%20breaking%20news%20when%3A1d&hl=en-IN&gl=IN&ceid=IN:en",
]

STATE_FILE = Path("posted.json")

# Ek run me maximum 2 news
MAX_POSTS_PER_RUN = 2

# In type ki posts nahi chahiye
BLOCKED_WORDS = [
    "scorecard",
    "full scorecard",
    "match result",
    "result:",
    "results:",
    "highlights:",
    "watch highlights",
    "points table",
    "schedule:",
    "fixture:",
    "fixtures:",
    "squad:",
    "stats:",
    "live scorecard",
]

# Cricket related news hi accept hogi
CRICKET_KEYWORDS = [
    "cricket",
    "test",
    "odi",
    "t20",
    "t20i",
    "ipl",
    "asia cup",
    "world cup",
    "wpl",
    "bbl",
    "psl",
    "icc",
    "bcci",
    "women cricket",
    "india cricket",
]


def load_posted():
    if not STATE_FILE.exists():
        return set()

    try:
        data = json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )
        return set(data)
    except Exception:
        return set()


def save_posted(items):
    # Sirf last 200 news IDs save rakhenge
    latest = list(items)[-200:]

    STATE_FILE.write_text(
        json.dumps(
            latest,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def get_item_id(entry):
    raw = (
        entry.get("id")
        or entry.get("link")
        or entry.get("title", "")
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def get_publish_time(entry):
    value = (
        entry.get("published_parsed")
        or entry.get("updated_parsed")
    )

    if not value:
        return None

    try:
        return datetime(
            *value[:6],
            tzinfo=timezone.utc
        )
    except Exception:
        return None


def is_current_cricket_news(entry):
    title = entry.get("title", "").strip()
    link = entry.get("link", "").strip()

    combined_text = (
        title + " " + link
    ).lower()

    # Scorecard/result/schedule ko reject karo
    for word in BLOCKED_WORDS:
        if word in combined_text:
            return False

    # Cricket related hona chahiye
    cricket_found = False

    for keyword in CRICKET_KEYWORDS:
        if keyword in combined_text:
            cricket_found = True
            break

    if not cricket_found:
        return False

    # Published time check
    published = get_publish_time(entry)

    if published is None:
        return False

    now = datetime.now(timezone.utc)

    age = now - published

    # Sirf last 24 hours ki news
    if age < timedelta(minutes=-10):
        return False

    if age > timedelta(hours=24):
        return False

    return True


def send_to_telegram(title, link, source):
    safe_title = html.escape(
        title.strip()
    )

    safe_source = html.escape(
        source.strip()
        if source
        else "Cricket News"
    )

    safe_link = html.escape(
        link.strip(),
        quote=True
    )

    message = (
        f"🏏 <b>{safe_title}</b>\n\n"
        f"📰 {safe_source}\n\n"
        f"🔗 <a href=\"{safe_link}\">"
        f"Read Full News"
        f"</a>\n\n"
        f"📲 @Cricbuzzscom"
    )

    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        telegram_url,
        data={
            "chat_id": CHANNEL_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(result)


def main():

    posted = load_posted()

    candidates = []

    seen_this_run = set()

    # RSS sources check
    for rss_url in RSS_URLS:

        feed = feedparser.parse(
            rss_url
        )

        for entry in feed.entries[:20]:

            item_id = get_item_id(entry)

            # Duplicate skip
            if item_id in posted:
                continue

            if item_id in seen_this_run:
                continue

            # Current cricket news check
            if not is_current_cricket_news(entry):
                continue

            title = entry.get(
                "title",
                ""
            ).strip()

            link = entry.get(
                "link",
                ""
            ).strip()

            source_data = entry.get(
                "source",
                {}
            )

            source = source_data.get(
                "title",
                ""
            ).strip()

            if not title or not link:
                continue

            published = get_publish_time(
                entry
            )

            candidates.append(
                (
                    item_id,
                    title,
                    link,
                    source,
                    published
                )
            )

            seen_this_run.add(
                item_id
            )

    # Latest news first
    candidates.sort(
        key=lambda item: item[4],
        reverse=True
    )

    # Maximum 2 news
    candidates = candidates[
        :MAX_POSTS_PER_RUN
    ]

    # Telegram par post
    for (
        item_id,
        title,
        link,
        source,
        published
    ) in candidates:

        send_to_telegram(
            title,
            link,
            source
        )

        posted.add(
            item_id
        )

    # Posted news save
    save_posted(
        posted
    )

    print(
        f"Posted {len(candidates)} "
        f"current cricket news item(s)."
    )


if __name__ == "__main__":
    main()
