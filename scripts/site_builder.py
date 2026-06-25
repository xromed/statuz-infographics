"""
Строит HTML-дашборды для GitHub Pages.
Chart.js + прогресс-бары + динамика.
"""
import json
from pathlib import Path
from datetime import datetime

DOCS = Path("docs")
NEWS_DIR = DOCS / "news"
NEWS_DIR.mkdir(parents=True, exist_ok=True)

CATEGORY_COLOR = {
    "Демография":         "#7b1fa2",
    "Экономика":          "#1565c0",
    "Промышленность":     "#bf360c",
    "Цены":               "#e65100",
    "Торговля":           "#00695c",
    "Транспорт":          "#1565c0",
    "Здравоохранение":    "#b71c1c",
    "Образование":        "#0277bd",
    "Спорт":              "#2e7d32",
    "Туризм":             "#00695c",
    "Статистика":         "#37474f",
    "Занятость":          "#0d47a1",
    "Сельское хозяйство": "#33691e",
    "Строительство":      "#4e342e",
}


def _cat_color(cat):
    return CATEGORY_COLOR.get(cat, "#37474f")


def _chart_block(analysis: dict, color: str) -> str:
    chart_data = analysis.get("chart_data") or []
    if len(chart_data) < 2:
        # попробуем из key_stats
        chart_data = []
        for s in analysis.get("key_stats", []):
            try:
                float(s["value"])
                chart_data.append(s)
            except (ValueError, TypeError):
                pass
    if len(chart_data) < 2:
        return ""

    # Максимум для прогресс-баров
    try:
        max_val = max(float(s["value"]) for s in chart_data)
    except (ValueError, TypeError):
        return ""

    labels = json.dumps([s.get("label", "")[:35] for s in chart_data], ensure_ascii=False)
    values = json.dumps([float(s["value"]) for s in chart_data])
    units  = chart_data[0].get("unit", "").split()[0] if chart_data else ""

    # Определяем ориентацию
    axis = "y" if len(chart_data) >= 3 else "x"

    return f"""
<div class="chart-section">
  <div class="section-title">Структура показателей</div>
  <canvas id="mainChart"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
(function() {{
  const labels = {labels};
  const values = {values};
  const color  = "{color}";
  const canvas = document.getElementById('mainChart');
  canvas.style.maxHeight = (labels.length > 4 ? 280 : 200) + 'px';
  new Chart(canvas, {{
    type: 'bar',
    data: {{
      labels,
      datasets: [{{
        data: values,
        backgroundColor: color + 'bb',
        borderColor: color,
        borderWidth: 1.5,
        borderRadius: 5,
        borderSkipped: false,
      }}]
    }},
    options: {{
      indexAxis: '{axis}',
      responsive: true,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            label: ctx => ' ' + ctx.raw.toLocaleString('ru-RU') + ' {units}'
          }}
        }}
      }},
      scales: {{
        x: {{ grid: {{ color: 'rgba(0,0,0,.05)' }}, ticks: {{ font: {{ size: 11 }} }} }},
        y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 11 }} }} }}
      }}
    }}
  }});
}})();
</script>"""


def _progress_bars(analysis: dict, color: str) -> str:
    stats = analysis.get("key_stats", [])
    numeric = []
    for s in stats:
        try:
            numeric.append((float(s["value"]), s))
        except (ValueError, TypeError):
            pass
    if not numeric:
        return ""

    max_val = max(v for v, _ in numeric)
    if max_val == 0:
        return ""

    rows = ""
    for val, s in numeric[:6]:
        pct = round(val / max_val * 100)
        trend = s.get("trend", "neutral")
        t_icon  = {"up": "↑", "down": "↓", "neutral": "→"}.get(trend, "→")
        t_color = {"up": "#2e7d32", "down": "#c62828", "neutral": "#78909c"}.get(trend, "#78909c")
        val_str = f"{s['value']} {s['unit']}".strip()
        rows += f"""
    <div class="pbar-row">
      <div class="pbar-meta">
        <span class="pbar-label">{s.get('label','')[:55]}</span>
        <span class="pbar-val">{val_str} <span style="color:{t_color};font-size:12px">{t_icon}</span></span>
      </div>
      <div class="pbar-track"><div class="pbar-fill" style="width:{pct}%;background:{color}"></div></div>
    </div>"""

    return f'<div class="section-title">Ключевые показатели</div><div class="pbar-list">{rows}</div>'


def build_article_page(article: dict, analysis: dict) -> str:
    aid = article["id"]
    color = _cat_color(analysis.get("category", ""))
    bg = color + "14"

    chart_html = _chart_block(analysis, color)
    pbars_html = _progress_bars(analysis, color)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{analysis.get('headline', article.get('title',''))}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
      background:#f0f2f5;color:#1a1a2e;min-height:100vh}}
.wrap{{max-width:780px;margin:0 auto;padding:20px 16px 56px}}
.back{{display:inline-flex;align-items:center;gap:6px;color:{color};font-size:13px;
       font-weight:600;text-decoration:none;margin-bottom:14px}}
.card{{background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 2px 20px rgba(0,0,0,.07)}}

/* Шапка */
.hdr{{background:{color};padding:24px 26px 20px}}
.badge{{display:inline-block;background:rgba(255,255,255,.22);color:#fff;
        font-size:11px;font-weight:700;padding:3px 11px;border-radius:20px;
        letter-spacing:.5px;margin-bottom:10px}}
.hdr h1{{color:#fff;font-size:21px;font-weight:700;line-height:1.35}}
.period{{color:rgba(255,255,255,.7);font-size:13px;margin-top:7px}}

/* Тело */
.body{{padding:22px 24px 26px}}

/* Главная цифра */
.main-box{{background:{bg};border-radius:12px;padding:16px 20px;
           margin-bottom:22px;display:flex;align-items:baseline;gap:10px}}
.main-num{{font-size:52px;font-weight:800;color:{color};line-height:1}}
.main-unit{{font-size:18px;color:{color};opacity:.75;font-weight:600}}

/* Диаграмма */
.chart-section{{margin-bottom:22px}}
.section-title{{font-size:12px;font-weight:700;color:#90a4ae;
                letter-spacing:.6px;text-transform:uppercase;margin-bottom:10px}}

/* Прогресс-бары */
.pbar-list{{margin-bottom:22px}}
.pbar-row{{margin-bottom:10px}}
.pbar-meta{{display:flex;justify-content:space-between;align-items:baseline;
            margin-bottom:4px}}
.pbar-label{{font-size:12px;color:#546e7a;max-width:65%}}
.pbar-val{{font-size:13px;font-weight:700;color:{color};white-space:nowrap}}
.pbar-track{{background:#f0f2f5;border-radius:6px;height:7px;overflow:hidden}}
.pbar-fill{{height:100%;border-radius:6px;transition:width .6s ease}}

/* Подвал */
.foot{{border-top:1px solid #eceff1;padding-top:14px;
       display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;align-items:center}}
.foot a{{color:{color};font-size:13px;font-weight:600;text-decoration:none}}
.foot a:hover{{text-decoration:underline}}
.date{{font-size:12px;color:#90a4ae}}
</style>
</head>
<body>
<div class="wrap">
  <a class="back" href="../index.html">← Все новости</a>
  <div class="card">
    <div class="hdr">
      <div class="badge">{analysis.get('category','Статистика')}</div>
      <h1>{analysis.get('headline', article.get('title',''))}</h1>
      {"<div class='period'>" + analysis.get('period','') + "</div>" if analysis.get('period') else ""}
    </div>
    <div class="body">
      {"<div class='main-box'><span class='main-num'>" + analysis.get('main_value','') + "</span><span class='main-unit'>" + analysis.get('main_unit','') + "</span></div>" if analysis.get('main_value') else ""}
      {chart_html}
      {pbars_html}
      <div class="foot">
        <a href="{article.get('url','')}" target="_blank">Источник: stat.uz →</a>
        <span class="date">{article.get('date','')}</span>
      </div>
    </div>
  </div>
</div>
</body>
</html>"""

    path = NEWS_DIR / f"{aid}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def build_index(articles: list):
    cards = ""
    for a in sorted(articles, key=lambda x: x.get("date", ""), reverse=True)[:100]:
        an = a.get("analysis", {})
        color = _cat_color(an.get("category", ""))
        bg = color + "12"
        mv = an.get("main_value", "")
        mu = an.get("main_unit", "")

        cards += f"""
    <a href="news/{a['id']}.html" class="idx-link">
      <div class="idx-card">
        <div class="idx-bar" style="background:{color}"></div>
        <div class="idx-body">
          <span class="idx-badge" style="background:{bg};color:{color}">{an.get('category','Статистика')}</span>
          <div class="idx-title">{an.get('headline', a.get('title',''))[:72]}</div>
          {"<div class='idx-num' style='color:" + color + "'>" + mv + " <span class='idx-unit'>" + mu[:15] + "</span></div>" if mv else "<div style='height:32px'></div>"}
          <div class="idx-date">{a.get('date','')}</div>
        </div>
      </div>
    </a>"""

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    total = len(articles)
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Статистика Узбекистана</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
      background:#f0f2f5;color:#1a1a2e}}
.hdr{{background:#1a56a0;padding:18px 24px;position:sticky;top:0;z-index:10;
      display:flex;justify-content:space-between;align-items:center}}
.hdr h1{{color:#fff;font-size:18px;font-weight:600}}
.hdr p{{color:rgba(255,255,255,.6);font-size:11px}}
.count{{background:rgba(255,255,255,.2);color:#fff;font-size:11px;
        padding:3px 10px;border-radius:20px;white-space:nowrap}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(205px,1fr));
       gap:14px;padding:20px}}
.idx-link{{text-decoration:none;color:inherit;display:block}}
.idx-card{{background:#fff;border-radius:10px;overflow:hidden;
           box-shadow:0 1px 8px rgba(0,0,0,.07);
           transition:transform .18s,box-shadow .18s}}
.idx-card:hover{{transform:translateY(-2px);box-shadow:0 5px 20px rgba(0,0,0,.11)}}
.idx-bar{{height:5px}}
.idx-body{{padding:13px 15px 15px}}
.idx-badge{{display:inline-block;font-size:10px;font-weight:700;
            padding:2px 9px;border-radius:20px;margin-bottom:7px;letter-spacing:.3px}}
.idx-title{{font-size:12px;font-weight:600;line-height:1.4;color:#1a1a2e;
            margin-bottom:8px;min-height:34px}}
.idx-num{{font-size:26px;font-weight:800;line-height:1;margin-bottom:4px}}
.idx-unit{{font-size:12px;opacity:.72}}
.idx-date{{font-size:10px;color:#90a4ae;margin-top:7px}}
</style>
</head>
<body>
<div class="hdr">
  <div>
    <h1>📊 Статистика Узбекистана</h1>
    <p>Нацкомстат УЗ · Обновлено: {now}</p>
  </div>
  <div class="count">{total} статей</div>
</div>
<div class="grid">{cards}</div>
</body>
</html>"""

    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print(f"[site] index.html: {total} статей")
