"""Парсит список новостей stat.uz."""
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://stat.uz"
NEWS_URL = "https://stat.uz/ru/press-tsentr/novosti-goskomstata"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StatBot/1.0)"}


def fetch_news_list(pages: int = 2) -> list[dict]:
    articles = []
    for page in range(pages):
        url = NEWS_URL + (f"?start={page * 18}" if page > 0 else "")
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"[scraper] Ошибка: {e}")
            continue

        soup = BeautifulSoup(r.text, "lxml")
        for h2 in soup.select("h2 a[href*='/novosti-goskomstata/']"):
            href = h2.get("href", "")
            if not href:
                continue
            full_url = BASE + href if href.startswith("/") else href
            m = re.search(r"/(\d+)-", href)
            article_id = m.group(1) if m else href.split("/")[-1]
            title = h2.get_text(strip=True)

            date_pub = ""
            parent = h2.find_parent()
            if parent:
                dm = re.search(r"(\d{2}\s+\w+\s+\d{4})", parent.get_text())
                if dm:
                    date_pub = dm.group(1)

            articles.append({
                "id": article_id,
                "url": full_url,
                "title": title,
                "date": date_pub,
            })
    return articles
