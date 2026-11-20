"""Tech headlines from public RSS/Atom feeds (headline + link + source only). Parsing is size-capped."""
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from . import net

FEEDS = [("The Verge", "https://www.theverge.com/rss/index.xml"),
         ("TechCrunch", "https://techcrunch.com/feed/"),
         ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
         ("Gadgets 360", "https://www.gadgets360.com/rss/news")]


def _ts(text):
    if not text:
        return None
    try:
        return parsedate_to_datetime(text).timestamp()
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat(text.strip().replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def parse_feed(text, source):
    root = ET.fromstring(text[:1_500_000])
    out = []
    for node in root.iter():
        if _local(node.tag) not in ("item", "entry"):
            continue
        f = {_local(c.tag): c for c in node}
        title = (f["title"].text or "").strip() if "title" in f else ""
        link = ""
        if "link" in f:
            link = (f["link"].get("href") or f["link"].text or "").strip()
        when = _ts((f.get("pubDate") if "pubDate" in f else f.get("published") if "published" in f else f.get("updated")).text
                   if any(k in f for k in ("pubDate", "published", "updated")) else None)
        if title and link.startswith("https://"):
            out.append({"title": " ".join(title.split()), "link": link, "ts": when, "source": source})
    return out


def fetch_news(feeds=FEEDS, limit=8, getter=net.get_text):
    items, errors = [], []
    for name, url in feeds:
        try:
            items += parse_feed(getter(url), name)[:6]
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}")
    items.sort(key=lambda i: i["ts"] or 0, reverse=True)
    seen, unique = set(), []
    for i in items:
        if i["title"].lower() not in seen:
            seen.add(i["title"].lower())
            unique.append(i)
    return unique[:limit], errors


def ago(ts, now=None):
    if ts is None:
        return ""
    s = int((now or time.time()) - ts)
    if s < 90:
        return "just now"
    if s < 3600:
        return f"{s // 60} min ago"
    if s < 86400:
        return f"{s // 3600} h ago"
    return f"{s // 86400} d ago"
