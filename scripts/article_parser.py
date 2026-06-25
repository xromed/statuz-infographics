"""Загружает и парсит страницу статьи."""
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote

BASE = "https://stat.uz"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StatBot/1.0)"}


def parse(url: str) -> dict:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"[parser] Ошибка: {e}")
        return {}

    soup = BeautifulSoup(r.text, "lxml")

    # Заголовок
    h2 = soup.find("h2")
    title = h2.get_text(strip=True) if h2 else ""

    # Дата
    date = ""
    for tag in soup.find_all(string=re.compile(r"\d{2}\s+\w+\s+\d{4}")):
        m = re.search(r"(\d{2}\s+\w+\s+\d{4})", tag)
        if m:
            date = m.group(1)
            break

    content = (
        soup.find("div", class_="item-page")
        or soup.find("article")
        or soup.find("div", id="content")
    )

    body_text, pdf_urls, tables = "", [], []

    if content:
        for iframe in content.find_all("iframe"):
            src = iframe.get("src", "")
            if "viewer.html" in src and "file=" in src:
                pdf_url = unquote(src.split("file=")[-1])
                if pdf_url.endswith(".pdf"):
                    pdf_urls.append(pdf_url)

        for a in content.find_all("a", href=True):
            if a["href"].endswith(".pdf"):
                full = BASE + a["href"] if a["href"].startswith("/") else a["href"]
                if full not in pdf_urls:
                    pdf_urls.append(full)

        for table in content.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)

        for tag in content(["script", "style", "iframe"]):
            tag.decompose()
        body_text = content.get_text("\n", strip=True)[:4000]

    return {
        "title": title,
        "date": date,
        "body_text": body_text,
        "pdf_urls": pdf_urls,
        "tables": tables,
    }
