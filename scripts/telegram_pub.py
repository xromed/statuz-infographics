"""Публикует пост в Telegram канал."""
import os
import requests

def post(article: dict, analysis: dict, page_url: str, img_local_path: str = None):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    channel = os.environ.get("TELEGRAM_CHANNEL_ID", "")
    if not token or not channel:
        print("[tg] Не настроен")
        return

    trend_icon = {"up": "📈", "down": "📉", "neutral": "➡️"}
    lines = [
        f"📊 <b>{analysis.get('headline', article['title'])}</b>",
        f"",
        f"🏷 <i>{analysis.get('category', 'Статистика')}</i>",
    ]
    if analysis.get("main_value"):
        lines.append(f"")
        lines.append(f"<b>{analysis['main_value']} {analysis.get('main_unit','')}</b>")

    for s in analysis.get("key_stats", [])[:3]:
        icon = trend_icon.get(s.get("trend", "neutral"), "➡️")
        lines.append(f"{icon} {s.get('value','')} {s.get('unit','')} — {s.get('label','')}")

    if analysis.get("period"):
        lines += ["", f"📅 {analysis['period']}"]

    lines += ["", f'🔗 <a href="{article["url"]}">stat.uz</a>  •  <a href="{page_url}">Инфографика →</a>']
    caption = "\n".join(lines)[:1024]

    api = f"https://api.telegram.org/bot{token}"

    # Если есть картинка — отправляем с фото
    if img_local_path and os.path.exists(img_local_path):
        with open(img_local_path, "rb") as f:
            r = requests.post(f"{api}/sendPhoto", data={
                "chat_id": channel, "caption": caption, "parse_mode": "HTML"
            }, files={"photo": f}, timeout=30)
    else:
        r = requests.post(f"{api}/sendMessage", json={
            "chat_id": channel, "text": caption,
            "parse_mode": "HTML", "disable_web_page_preview": False
        }, timeout=15)

    if r.ok and r.json().get("ok"):
        print(f"[tg] Опубликовано: {analysis.get('headline','')[:40]}")
    else:
        print(f"[tg] Ошибка: {r.text[:100]}")
