"""Загружает и парсит страницу статьи."""
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote

BASE = "https://stat.uz"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StatBot/1.0)"}

# Полное совпадение с этим текстом (без учёта регистра) означает, что мы
# выцепили не заголовок статьи, а название комитета из шапки/подвала сайта.
# Такой "заголовок" никогда не должен попадать в данные.
BAD_TITLE = "национальный комитет республики узбекистан по статистике"


def parse(url: str) -> dict:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"[parser] Ошибка: {e}")
        return {}

    soup = BeautifulSoup(r.text, "lxml")

    # Блок с телом статьи ищем в первую очередь: заголовок надёжнее всего
    # искать внутри него, а не по всей странице (в шапке и подвале сайта
    # тоже есть свои <h2>, включая "Национальный комитет Республики
    # Узбекистан по статистике" в подвале — его легко случайно принять за
    # заголовок при поиске по всему документу).
    content = (
        soup.find("div", class_="item-page")
        or soup.find("article")
        or soup.find("div", id="content")
    )

    # Основной источник заголовка — тег <title> страницы: на практике он
    # всегда содержит чистый заголовок статьи без служебных суффиксов вида
    # " | stat.uz".
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        t = title_tag.get_text(strip=True)
        # На случай появления суффикса " | stat.uz" или похожего —
        # отрезаем всё после первого " | ".
        t = t.split(" | ")[0].strip()
        if t and t.strip().lower() != BAD_TITLE:
            title = t

    # Фолбэк: ищем <h2> только внутри блока статьи (не по всей странице),
    # чтобы не зацепить статичные заголовки шапки/подвала.
    if not title and content:
        for h2 in content.find_all("h2"):
            t = h2.get_text(strip=True)
            if t and t.strip().lower() != BAD_TITLE:
                title = t
                break

    # Защита: даже если что-то пошло не так выше, никогда не отдаём
    # название комитета в качестве заголовка статьи.
    if title.strip().lower() == BAD_TITLE:
        title = ""

    # Дата
    date = ""
    for tag in soup.find_all(string=re.compile(r"\d{2}\s+\w+\s+\d{4}")):
        m = re.search(r"(\d{2}\s+\w+\s+\d{4})", tag)
        if m:
            date = m.group(1)
            break

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
