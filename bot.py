import os
import json
import html
import hashlib
from pathlib import Path

import feedparser
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@cricbuzzscom")

RSS_URLS = [
    "https://news.google.com/rss/search?q=cricket&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=India%20cricket&hl=en-IN&gl=IN&ceid=IN:en",
]

STATE_FILE = Path("posted.json")
MAX_POSTS_PER_RUN = 3


def load_posted():
    if not STATE_FILE.exists():
        return set()
    try:
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    except Exception:
        return set()


def save_posted(items):
    # Keep only the newest 100 IDs so the file stays small.
    STATE_FILE.write_text(
        json.dumps(list(items)[-100:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def item_id(entry):
    raw = entry.get("id") or entry.get("link") or entry.get("title", "")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def send_telegram(title, link, source):
    safe_title = html.escape(title.strip())
    safe_source = html.escape(source.strip() if source else "Cricket News")
    safe_link = html.escape(link.strip(), quote=True)

    text = (
        f"🏏 <b>{safe_title}</b>\n\n"
        f"📰 Source: {safe_source}\n\n"
        f"🔗 <a href=\"{safe_link}\">Read full news</a>\n\n"
        f"📲 @Cricbuzzscom"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data)


def main():
    posted = load_posted()
    new_ids = []
    candidates = []

    for rss_url in RSS_URLS:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:10]:
            link = entry.get("link", "").strip()
            title = entry.get("title", "").strip()
            if not title or not link:
                continue

            uid = item_id(entry)
            if uid in posted or uid in new_ids:
                continue

            source = entry.get("source", {}).get("title", "")
            candidates.append((uid, title, link, source))
            new_ids.append(uid)

    # Oldest first, up to the per-run limit.
    candidates = candidates[:MAX_POSTS_PER_RUN]

    for uid, title, link, source in candidates:
        send_telegram(title, link, source)
        posted.add(uid)

    save_posted(posted)
    print(f"Posted {len(candidates)} new cricket news item(s).")


if __name__ == "__main__":
    main()
