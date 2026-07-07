"""
Строит HTML-инфографики для GitHub Pages.
Дизайн: анимированные счётчики, KPI-карточки, Chart.js, градиенты.
"""
import json
import re
from pathlib import Path
from datetime import datetime

DOCS = Path("docs")
NEWS_DIR = DOCS / "news"
NEWS_DIR.mkdir(parents=True, exist_ok=True)

MONTHS_RU_GENITIVE = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}
MONTH_NAMES_RU = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]


def _parse_date(date_str: str):
    """Парсит дату вида «26 июня 2026» → (год, месяц, день) для сортировки/группировки.
    Возвращает (0, 0, 0), если распознать не удалось (такие статьи уходят в конец списка)."""
    m = re.search(r'(\d{1,2})\s+([а-яё]+)\s+(\d{4})', (date_str or "").lower())
    if not m:
        return (0, 0, 0)
    day = int(m.group(1))
    month = MONTHS_RU_GENITIVE.get(m.group(2), 0)
    year = int(m.group(3))
    return (year, month, day)


def _month_key(date_str: str) -> str:
    y, mo, _ = _parse_date(date_str)
    if not y:
        return ""
    return f"{y:04d}-{mo:02d}"


def _month_label(date_str: str) -> str:
    y, mo, _ = _parse_date(date_str)
    if not y:
        return ""
    return f"{MONTH_NAMES_RU[mo]} {y}"

# ── Цвета и иконки категорий ──────────────────────────────────────────────────
CATEGORIES = {
    "Демография":         {"color": "#7b1fa2", "light": "#f3e5f5", "icon": "👥"},
    "Экономика":          {"color": "#1565c0", "light": "#e3f2fd", "icon": "📈"},
    "Промышленность":     {"color": "#bf360c", "light": "#fbe9e7", "icon": "🏭"},
    "Цены":               {"color": "#e65100", "light": "#fff3e0", "icon": "💰"},
    "Торговля":           {"color": "#00695c", "light": "#e0f2f1", "icon": "🛒"},
    "Транспорт":          {"color": "#1565c0", "light": "#e3f2fd", "icon": "🚆"},
    "Здравоохранение":    {"color": "#b71c1c", "light": "#ffebee", "icon": "🏥"},
    "Образование":        {"color": "#0277bd", "light": "#e1f5fe", "icon": "🎓"},
    "Спорт":              {"color": "#2e7d32", "light": "#e8f5e9", "icon": "🏆"},
    "Туризм":             {"color": "#00695c", "light": "#e0f2f1", "icon": "✈️"},
    "Статистика":         {"color": "#37474f", "light": "#eceff1", "icon": "📊"},
    "Занятость":          {"color": "#0d47a1", "light": "#e8eaf6", "icon": "💼"},
    "Сельское хозяйство": {"color": "#33691e", "light": "#f1f8e9", "icon": "🌾"},
    "Строительство":      {"color": "#4e342e", "light": "#efebe9", "icon": "🏗️"},
}

def _cat(cat: str) -> dict:
    return CATEGORIES.get(cat, CATEGORIES["Статистика"])


def _trend_badge(trend: str) -> str:
    if trend == "up":
        return '<span class="trend up">↑</span>'
    elif trend == "down":
        return '<span class="trend down">↓</span>'
    return '<span class="trend neutral">→</span>'


def _fmt_value(val: str) -> str:
    """Форматирует число с пробелами-разделителями."""
    try:
        n = float(val)
        if n == int(n):
            return f"{int(n):,}".replace(",", " ")
        return f"{n:,.1f}".replace(",", " ")
    except (ValueError, TypeError):
        return val


def _kpi_cards(key_stats: list, color: str, light: str, headline: str = "") -> str:
    if not key_stats:
        return ""

    cards = ""
    for i, s in enumerate(key_stats[:6]):
        trend_html = _trend_badge(s.get("trend", "neutral"))
        val_fmt = _fmt_value(s["value"])
        # Метка: очищаем от обрывков предложений — берём только до первого глагола
        raw_label = s.get("label", "Показатель")
        label = raw_label[:55]
        unit = s.get("unit", "")[:20]

        # Первая карточка — большая героическая
        if i == 0:
            hero_label = headline[:80] if headline else label
            cards += f"""
      <div class="kpi-hero" style="--c:{color};--bg:{light}">
        <div class="kpi-hero-val">
          <span class="counter" data-target="{s['value']}">{val_fmt}</span>
          <span class="kpi-hero-unit">{unit}</span>
          {trend_html}
        </div>
        <div class="kpi-hero-label">{hero_label}</div>
      </div>"""
        else:
            cards += f"""
      <div class="kpi-card" style="--c:{color};--bg:{light}">
        <div class="kpi-val">
          <span class="counter" data-target="{s['value']}">{val_fmt}</span>
          <span class="kpi-unit">{unit}</span>
        </div>
        <div class="kpi-label">{label}</div>
        {trend_html}
      </div>"""

    return f'<div class="kpi-grid">{cards}</div>'


def _has_years(chart_data: list) -> bool:
    """Проверяет, содержат ли метки годы (временной ряд)."""
    import re
    return sum(1 for s in chart_data if re.search(r'\b(19|20)\d{2}\b', s.get("label", ""))) >= 2


def _chart_block(analysis: dict, color: str) -> str:
    chart_data = analysis.get("chart_data") or []
    if len(chart_data) < 2:
        return ""

    try:
        values = [float(s["value"]) for s in chart_data]
    except (ValueError, TypeError):
        return ""

    _unit_parts = chart_data[0].get("unit", "").split() if chart_data else []
    unit = _unit_parts[0] if _unit_parts else ""
    n = len(chart_data)
    is_timeseries = _has_years(chart_data)

    # Для временных рядов — line chart с градиентной заливкой
    if is_timeseries:
        import re
        raw_labels = []
        for s in chart_data:
            m = re.search(r'\b(19|20)\d{2}\b', s.get("label", ""))
            raw_labels.append(m.group() if m else s.get("label", "")[:12])
        labels = json.dumps(raw_labels, ensure_ascii=False)
        vals_js = json.dumps(values)
        return f"""
<div class="chart-wrap">
  <div class="section-label">Динамика по годам</div>
  <div style="position:relative;height:220px">
    <canvas id="mainChart"></canvas>
  </div>
</div>
<script>
(function(){{
  const ctx = document.getElementById('mainChart').getContext('2d');
  const c = "{color}";
  const grad = ctx.createLinearGradient(0,0,0,220);
  grad.addColorStop(0, c + '44');
  grad.addColorStop(1, c + '00');
  new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: {labels},
      datasets: [{{
        data: {vals_js},
        borderColor: c,
        borderWidth: 2.5,
        backgroundColor: grad,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: c,
        pointRadius: 5,
        pointHoverRadius: 7,
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          backgroundColor: '#1a1a2e',
          padding: 10,
          cornerRadius: 8,
          callbacks: {{ label: ctx => '  ' + ctx.raw.toLocaleString('ru-RU') + ' {unit}' }}
        }}
      }},
      scales: {{
        x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 12, family: 'Inter', weight: '600' }}, color: '#546e7a' }} }},
        y: {{ grid: {{ color: 'rgba(0,0,0,.05)' }}, ticks: {{ font: {{ size: 11, family: 'Inter' }}, color: '#90a4ae' }} }}
      }},
      animation: {{ duration: 1000, easing: 'easeOutQuart' }}
    }}
  }});
}})();
</script>"""

    # Для сравнительных данных — горизонтальный бар
    is_horiz = n >= 4
    axis_param = '"y"' if is_horiz else '"x"'
    max_h = max(280, n * 40) if is_horiz else 220
    grad_coords = "0,0,0,300" if is_horiz else "0,0,300,0"
    labels = json.dumps([s.get("label", "")[:35] for s in chart_data], ensure_ascii=False)
    vals_js = json.dumps(values)

    return f"""
<div class="chart-wrap">
  <div class="section-label">Структура показателей</div>
  <div style="position:relative;height:{max_h}px">
    <canvas id="mainChart"></canvas>
  </div>
</div>
<script>
(function(){{
  const ctx = document.getElementById('mainChart').getContext('2d');
  const c = "{color}";
  const grad = ctx.createLinearGradient({grad_coords});
  grad.addColorStop(0, c + 'ff');
  grad.addColorStop(1, c + '88');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: {labels},
      datasets: [{{
        data: {vals_js},
        backgroundColor: grad,
        borderColor: c,
        borderWidth: 0,
        borderRadius: 5,
        borderSkipped: false,
      }}]
    }},
    options: {{
      indexAxis: {axis_param},
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          backgroundColor: '#1a1a2e',
          padding: 10,
          cornerRadius: 8,
          callbacks: {{ label: ctx => '  ' + ctx.raw.toLocaleString('ru-RU') + ' {unit}' }}
        }}
      }},
      scales: {{
        x: {{ grid: {{ color: 'rgba(0,0,0,.04)' }}, ticks: {{ font: {{ size: 11, family: 'Inter' }}, color: '#78909c' }} }},
        y: {{ grid: {{ display: {'false' if is_horiz else 'true'}, color: 'rgba(0,0,0,.04)' }}, ticks: {{ font: {{ size: 11, family: 'Inter' }}, color: '#546e7a' }} }}
      }},
      animation: {{ duration: 900, easing: 'easeOutQuart' }}
    }}
  }});
}})();
</script>"""


def _donut_chart(chart_data: list, color: str) -> str:
    if len(chart_data) < 2:
        return ""
    try:
        values = [float(s["value"]) for s in chart_data]
    except (ValueError, TypeError):
        return ""

    palette = [
        color + "ff", color + "cc", color + "99",
        color + "77", color + "55", color + "33",
    ]
    colors_js = json.dumps(palette[:len(chart_data)])
    labels = json.dumps([s.get("label", "")[:35] for s in chart_data], ensure_ascii=False)
    vals_js = json.dumps(values)
    _unit_parts = chart_data[0].get("unit", "").split() if chart_data else []
    unit = _unit_parts[0] if _unit_parts else ""

    return f"""
<div class="chart-wrap">
  <div class="section-label">Структура показателей</div>
  <div style="position:relative;height:240px">
    <canvas id="mainChart"></canvas>
  </div>
</div>
<script>
(function(){{
  new Chart(document.getElementById('mainChart'), {{
    type: 'doughnut',
    data: {{
      labels: {labels},
      datasets: [{{
        data: {vals_js},
        backgroundColor: {colors_js},
        borderWidth: 0,
        hoverOffset: 8,
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      cutout: '62%',
      plugins: {{
        legend: {{
          position: 'right',
          labels: {{ font: {{ size: 11, family: 'Inter' }}, color: '#546e7a', padding: 10 }}
        }},
        tooltip: {{
          backgroundColor: '#1a1a2e',
          padding: 10,
          cornerRadius: 8,
          callbacks: {{
            label: ctx => '  ' + ctx.raw.toLocaleString('ru-RU') + ' {unit}'
          }}
        }}
      }},
      animation: {{ animateRotate: true, duration: 900 }}
    }}
  }});
}})();
</script>"""


def _progress_section(analysis: dict, color: str) -> str:
    # Прогресс-бары убраны: горизонтальный бар-чарт уже показывает сравнение,
    # а блок аналитики даёт текстовые выводы. Дублирование только путает.
    return ""


def _insights_block(analysis: dict, color: str, light: str) -> str:
    """Аналитический блок: расширенные выводы на основе данных статьи."""
    import re as _re
    chart_data = analysis.get("chart_data") or []
    key_stats  = analysis.get("key_stats") or []

    if not chart_data and not key_stats:
        return ""

    # Каждый инсайт: (emoji, заголовок, текст)
    insights = []
    is_timeseries = _has_years(chart_data)

    # ── ВРЕМЕННОЙ РЯД ────────────────────────────────────────────────────────
    if is_timeseries and len(chart_data) >= 2:
        try:
            vals  = [float(s["value"]) for s in chart_data]
            years = []
            for s in chart_data:
                m = _re.search(r'\b(19|20)\d{2}\b', s.get("label", ""))
                if m:
                    years.append(int(m.group()))
            unit = chart_data[0].get("unit", "")

            first_val, last_val = vals[0], vals[-1]
            n_years = (years[-1] - years[0]) if len(years) >= 2 else 0

            # 1. Общий рост + CAGR
            if first_val > 0 and n_years > 0:
                total_pct = round((last_val - first_val) / first_val * 100, 1)
                cagr      = round(((last_val / first_val) ** (1 / n_years) - 1) * 100, 1)
                direction = "вырос" if total_pct > 0 else "снизился"
                insights.append((
                    "📈", "Общий рост",
                    f"За {n_years} лет ({years[0]}–{years[-1]}) показатель <b>{direction} "
                    f"на {abs(total_pct):.1f}%</b>. Среднегодовой темп роста (CAGR): "
                    f"<b>{cagr:+.1f}% в год</b>."
                ))

            # 2. Рекордный годовой скачок
            max_jump = 0; max_j_idx = 1
            for i in range(1, len(vals)):
                if vals[i-1] > 0:
                    j = abs((vals[i] - vals[i-1]) / vals[i-1] * 100)
                    if j > max_jump:
                        max_jump = j; max_j_idx = i
            if max_jump > 3 and max_j_idx < len(years):
                dir_w  = "рост" if vals[max_j_idx] > vals[max_j_idx-1] else "падение"
                emoji  = "🚀" if vals[max_j_idx] > vals[max_j_idx-1] else "📉"
                yr_j   = years[max_j_idx]
                insights.append((
                    emoji, "Рекордный скачок",
                    f"Максимальный однолетний {dir_w} — в <b>{yr_j} году</b>: "
                    f"с {_fmt_value(str(vals[max_j_idx-1]))} до "
                    f"{_fmt_value(str(vals[max_j_idx]))} {unit} "
                    f"(<b>{dir_w} {max_jump:.1f}%</b> за год)."
                ))

            # 3. Минимум за весь период
            min_i  = vals.index(min(vals))
            max_i2 = vals.index(max(vals))
            if len(years) > min_i:
                insights.append((
                    "📌", "Минимум и максимум",
                    f"Минимальное значение — <b>{_fmt_value(str(vals[min_i]))} {unit}</b> "
                    f"({years[min_i]} г.), максимальное — "
                    f"<b>{_fmt_value(str(vals[max_i2]))} {unit}</b> "
                    f"({years[max_i2] if max_i2 < len(years) else '–'} г.). "
                    f"Амплитуда: <b>{round((vals[max_i2]-vals[min_i])/vals[min_i]*100, 1):.1f}%</b>."
                    if vals[min_i] > 0 else
                    f"Минимальное значение — <b>{_fmt_value(str(vals[min_i]))} {unit}</b> "
                    f"({years[min_i]} г.), максимальное — "
                    f"<b>{_fmt_value(str(vals[max_i2]))} {unit}</b>."
                ))

            # 4. Последний период
            if len(vals) >= 2 and len(years) >= 2:
                delta     = vals[-1] - vals[-2]
                delta_pct = round(delta / vals[-2] * 100, 1) if vals[-2] else 0
                dir_w2    = "вырос" if delta > 0 else "снизился"
                insights.append((
                    "🔄", f"{years[-1]} vs {years[-2]}",
                    f"В последний период показатель <b>{dir_w2} на {abs(delta_pct):.1f}%</b>: "
                    f"с {_fmt_value(str(vals[-2]))} до <b>{_fmt_value(str(vals[-1]))} {unit}</b>."
                ))

            # 5. Среднее значение
            avg = sum(vals) / len(vals)
            above_avg = sum(1 for v in vals if v >= avg)
            insights.append((
                "📐", "Среднее за период",
                f"Среднее значение за весь период наблюдений: "
                f"<b>{_fmt_value(str(round(avg, 2)))} {unit}</b>. "
                f"Текущий показатель <b>{'выше' if vals[-1] >= avg else 'ниже'} среднего</b> "
                f"на {abs(round((vals[-1]-avg)/avg*100, 1)):.1f}%."
                if avg > 0 else
                f"Среднее значение за весь период: <b>{_fmt_value(str(round(avg, 2)))} {unit}</b>."
            ))

            # 6. Прогноз на следующий год (простая линейная экстраполяция по последним 3 точкам)
            if len(vals) >= 3 and n_years > 0:
                recent_vals  = vals[-3:]
                recent_growth = [(recent_vals[i] - recent_vals[i-1]) / recent_vals[i-1]
                                  for i in range(1, len(recent_vals)) if recent_vals[i-1] > 0]
                if recent_growth:
                    avg_recent_g = sum(recent_growth) / len(recent_growth)
                    forecast     = round(vals[-1] * (1 + avg_recent_g), 2)
                    next_year    = years[-1] + 1
                    dir_f        = "вырастет" if avg_recent_g > 0 else "снизится"
                    insights.append((
                        "🔮", f"Прогноз на {next_year}",
                        f"При сохранении среднего темпа последних лет "
                        f"({avg_recent_g*100:+.1f}%/год) к <b>{next_year} году</b> "
                        f"показатель {dir_f} до <b>~{_fmt_value(str(forecast))} {unit}</b>."
                    ))

        except Exception:
            pass

    # ── РЕГИОНАЛЬНЫЕ / СТРУКТУРНЫЕ ДАННЫЕ ───────────────────────────────────
    elif chart_data and not is_timeseries and len(chart_data) >= 2:
        try:
            vals   = [float(s["value"]) for s in chart_data]
            labels = [s.get("label", "")[:40].rstrip(" \t-–—") for s in chart_data]
            unit   = chart_data[0].get("unit", "")
            total  = sum(vals)
            avg    = total / len(vals)
            sorted_pairs = sorted(zip(vals, labels), reverse=True)
            max_v, max_l = sorted_pairs[0]
            min_v, min_l = sorted_pairs[-1]

            # 1. Лидер
            leader_share = round(max_v / total * 100, 1) if total else 0
            insights.append((
                "🥇", "Лидер",
                f"<b>{max_l}</b> занимает первое место: "
                f"<b>{_fmt_value(str(max_v))} {unit}</b> — "
                f"это <b>{leader_share}%</b> от суммарного объёма по всем регионам."
            ))

            # 2. Аутсайдер + разрыв
            ratio = round(max_v / min_v, 1) if min_v > 0 else None
            ratio_txt = f" Разрыв с лидером — <b>в {ratio}×</b>." if ratio else ""
            insights.append((
                "🔻", "Аутсайдер",
                f"Наименьший показатель у <b>{min_l}</b>: "
                f"<b>{_fmt_value(str(min_v))} {unit}</b>.{ratio_txt}"
            ))

            # 3. Топ-3 концентрация
            if len(vals) >= 3:
                top3_sum   = sum(v for v, _ in sorted_pairs[:3])
                top3_share = round(top3_sum / total * 100, 1) if total else 0
                top3_names = ", ".join(f"<b>{l}</b>" for _, l in sorted_pairs[:3])
                insights.append((
                    "📊", "Концентрация",
                    f"Топ-3 — {top3_names} — формируют "
                    f"<b>{top3_share}%</b> от общего объёма."
                ))

            # 4. Среднее и баланс
            above = sum(1 for v in vals if v >= avg)
            below = len(vals) - above
            insights.append((
                "⚖️", "Баланс",
                f"Среднее значение по всем регионам: "
                f"<b>{_fmt_value(str(round(avg, 1)))} {unit}</b>. "
                f"Выше среднего — <b>{above}</b> из {len(vals)} регионов, "
                f"ниже — <b>{below}</b>."
            ))

            # 5. Суммарный объём
            insights.append((
                "💰", "Итого",
                f"Суммарный объём по всем {len(vals)} регионам: "
                f"<b>{_fmt_value(str(round(total, 1)))} {unit}</b>. "
                f"Второе место занимает <b>{sorted_pairs[1][1]}</b> — "
                f"{_fmt_value(str(sorted_pairs[1][0]))} {unit} "
                f"({round(sorted_pairs[1][0]/total*100,1)}%)."
                if len(sorted_pairs) >= 2 else
                f"Суммарный объём: <b>{_fmt_value(str(round(total, 1)))} {unit}</b>."
            ))

            # 6. Равномерность (коэффициент вариации)
            if avg > 0:
                std  = (sum((v - avg)**2 for v in vals) / len(vals)) ** 0.5
                cv   = round(std / avg * 100, 1)
                spread_word = ("крайне неравномерно" if cv > 80
                               else "неравномерно" if cv > 40
                               else "относительно равномерно")
                insights.append((
                    "📏", "Неравномерность",
                    f"Распределение по регионам — <b>{spread_word}</b> "
                    f"(коэффициент вариации: {cv}%). "
                    f"{'Сильный дисбаланс между лидером и аутсайдером.' if cv > 80 else 'Умеренные различия между регионами.' if cv > 40 else 'Показатели регионов близки к среднему.'}"
                ))

        except Exception:
            pass

    if not insights:
        return ""

    cards_html = ""
    for emoji, title, text in insights:
        cards_html += f"""
    <div class="insight-card">
      <div class="insight-card-head">
        <span class="insight-emoji">{emoji}</span>
        <span class="insight-card-title">{title}</span>
      </div>
      <div class="insight-card-body">{text}</div>
    </div>"""

    return f"""
<div class="insights-block" style="--c:{color};--bg:{light}">
  <div class="insights-header">
    <span class="insights-icon">💡</span>
    <span class="insights-title">Аналитика</span>
  </div>
  <div class="insights-grid">
    {cards_html}
  </div>
</div>"""


def build_article_page(article: dict, analysis: dict) -> str:
    aid = article["id"]
    c = _cat(analysis.get("category", ""))
    color = c["color"]
    light = c["light"]
    icon = c["icon"]
    cat = analysis.get("category", "Статистика")

    key_stats = analysis.get("key_stats", [])
    chart_data = analysis.get("chart_data") or []
    headline = analysis.get("headline", article.get("title", ""))

    kpi_html = _kpi_cards(key_stats, color, light, headline)

    units = [s.get("unit", "").lower() for s in chart_data]
    use_donut = any("%" in u or "доля" in u or "процент" in u for u in units)
    chart_html = (_donut_chart(chart_data, color) if use_donut
                  else _chart_block(analysis, color))

    prog_html = _progress_section(analysis, color)
    insights_html = _insights_block(analysis, color, light)

    period = analysis.get("period", "")
    url = article.get("url", "")
    date = article.get("date", "")

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{headline}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --c: {color};
  --bg: {light};
  --radius: 16px;
  --shadow: 0 2px 24px rgba(0,0,0,.09);
}}
body {{
  font-family: 'Inter', -apple-system, sans-serif;
  background: #f0f2f5;
  color: #1a1a2e;
  min-height: 100vh;
}}

.nav {{
  background: {color};
  padding: 0 20px;
  height: 54px;
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 12px rgba(0,0,0,.18);
}}
.nav-back {{
  color: rgba(255,255,255,.9);
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: color .2s;
}}
.nav-back:hover {{ color: #fff; }}
.nav-title {{
  color: rgba(255,255,255,.7);
  font-size: 13px;
  margin-left: auto;
  letter-spacing: .2px;
}}

.page {{
  max-width: 820px;
  margin: 0 auto;
  padding: 20px 16px 60px;
}}

.hero-card {{
  background: {color};
  border-radius: var(--radius);
  overflow: hidden;
  margin-bottom: 14px;
  position: relative;
}}
.hero-card::before {{
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,.08) 0%, transparent 60%);
  pointer-events: none;
}}
.hero-bg-icon {{
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 80px;
  opacity: .1;
  line-height: 1;
  pointer-events: none;
  user-select: none;
}}
.hero-body {{
  padding: 28px 28px 24px;
  position: relative;
}}
.badge {{
  display: inline-block;
  background: rgba(255,255,255,.2);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 20px;
  letter-spacing: .6px;
  text-transform: uppercase;
  margin-bottom: 12px;
}}
.hero-title {{
  color: #fff;
  font-size: 20px;
  font-weight: 800;
  line-height: 1.35;
  max-width: 85%;
}}
.hero-period {{
  color: rgba(255,255,255,.65);
  font-size: 13px;
  margin-top: 8px;
  font-weight: 500;
}}

.kpi-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}}
.kpi-hero {{
  background: #fff;
  border-radius: var(--radius);
  padding: 20px 22px;
  box-shadow: var(--shadow);
  border-left: 4px solid var(--c);
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}}
.kpi-hero-val {{
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}}
.kpi-hero-val .counter {{
  font-size: 48px;
  font-weight: 900;
  color: var(--c);
  line-height: 1;
  letter-spacing: -1px;
}}
.kpi-hero-unit {{
  font-size: 20px;
  font-weight: 700;
  color: var(--c);
  opacity: .7;
}}
.kpi-hero-label {{
  font-size: 13px;
  color: #546e7a;
  font-weight: 500;
  flex: 1;
  min-width: 120px;
}}
.kpi-card {{
  background: #fff;
  border-radius: 12px;
  padding: 16px 18px;
  box-shadow: var(--shadow);
  border-top: 3px solid var(--c);
}}
.kpi-val {{
  display: flex;
  align-items: baseline;
  gap: 5px;
  margin-bottom: 4px;
}}
.kpi-val .counter {{
  font-size: 28px;
  font-weight: 800;
  color: var(--c);
  line-height: 1;
}}
.kpi-unit {{
  font-size: 12px;
  font-weight: 700;
  color: var(--c);
  opacity: .7;
}}
.kpi-label {{
  font-size: 11px;
  color: #78909c;
  font-weight: 500;
  line-height: 1.35;
}}

.trend {{
  font-size: 13px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 6px;
  display: inline-block;
  margin-left: 4px;
}}
.trend.up   {{ color: #2e7d32; background: #e8f5e9; }}
.trend.down {{ color: #c62828; background: #ffebee; }}
.trend.neutral {{ color: #78909c; background: #f5f5f5; }}

.chart-wrap {{
  background: #fff;
  border-radius: var(--radius);
  padding: 20px 22px 24px;
  box-shadow: var(--shadow);
  margin-bottom: 14px;
}}
.section-label {{
  font-size: 11px;
  font-weight: 700;
  color: #90a4ae;
  letter-spacing: .7px;
  text-transform: uppercase;
  margin-bottom: 14px;
}}

.prog-section {{
  background: #fff;
  border-radius: var(--radius);
  padding: 20px 22px 24px;
  box-shadow: var(--shadow);
  margin-bottom: 14px;
}}
.prow {{ margin-bottom: 14px; }}
.prow:last-child {{ margin-bottom: 0; }}
.prow-top {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 5px;
  gap: 8px;
}}
.prow-label {{
  font-size: 12px;
  color: #546e7a;
  font-weight: 500;
  flex: 1;
  line-height: 1.3;
}}
.prow-val {{
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}}
.ptrack {{
  background: #f0f2f5;
  border-radius: 6px;
  height: 8px;
  overflow: hidden;
}}
.pfill {{
  height: 100%;
  border-radius: 6px;
  transition: width .8s cubic-bezier(.4,0,.2,1);
}}

.insights-block {{
  background: #fff;
  border-radius: var(--radius);
  padding: 20px 22px 22px;
  box-shadow: var(--shadow);
  margin-bottom: 14px;
}}
.insights-header {{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}}
.insights-icon {{
  font-size: 18px;
  line-height: 1;
}}
.insights-title {{
  font-size: 11px;
  font-weight: 700;
  color: #90a4ae;
  letter-spacing: .7px;
  text-transform: uppercase;
}}
.insights-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
}}
.insight-card {{
  background: var(--bg);
  border-radius: 12px;
  padding: 14px 16px;
  border-left: 3px solid var(--c);
}}
.insight-card-head {{
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 6px;
}}
.insight-emoji {{
  font-size: 16px;
  line-height: 1;
}}
.insight-card-title {{
  font-size: 11px;
  font-weight: 700;
  color: var(--c);
  text-transform: uppercase;
  letter-spacing: .4px;
}}
.insight-card-body {{
  font-size: 12.5px;
  color: #455a64;
  line-height: 1.6;
}}
.insight-card-body b {{
  color: var(--c);
  font-weight: 700;
}}

.foot {{
  background: #fff;
  border-radius: var(--radius);
  padding: 16px 22px;
  box-shadow: var(--shadow);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}}
.foot a {{
  color: {color};
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 5px;
}}
.foot a:hover {{ text-decoration: underline; }}
.foot-date {{
  font-size: 12px;
  color: #90a4ae;
}}

@media (max-width: 500px) {{
  .hero-title {{ font-size: 17px; }}
  .kpi-hero-val .counter {{ font-size: 38px; }}
  .kpi-grid {{ grid-template-columns: 1fr 1fr; }}
  .kpi-hero {{ grid-column: 1 / -1; flex-direction: column; align-items: flex-start; }}
}}
</style>
</head>
<body>

<nav class="nav">
  <a class="nav-back" href="../index.html">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
    Все новости
  </a>
  <span class="nav-title">{icon} {cat}</span>
</nav>

<div class="page">

  <div class="hero-card">
    <div class="hero-bg-icon">{icon}</div>
    <div class="hero-body">
      <div class="badge">{cat}</div>
      <div class="hero-title">{headline}</div>
      {"<div class='hero-period'>" + period + "</div>" if period else ""}
    </div>
  </div>

  {kpi_html}
  {chart_html}
  {prog_html}
  {insights_html}

  <div class="foot">
    <a href="{url}" target="_blank" rel="noopener">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
        <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
      </svg>
      Источник: stat.uz
    </a>
    <span class="foot-date">{date}</span>
  </div>

</div>

<script>
(function() {{
  function animateCounter(el) {{
    const target = parseFloat(el.dataset.target);
    if (isNaN(target)) return;
    const isInt = Number.isInteger(target);
    const duration = 1200;
    const start = performance.now();
    function tick(now) {{
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      const val = target * ease;
      el.textContent = isInt
        ? Math.round(val).toLocaleString('ru-RU')
        : val.toLocaleString('ru-RU', {{minimumFractionDigits: 1, maximumFractionDigits: 1}});
      if (progress < 1) requestAnimationFrame(tick);
    }}
    requestAnimationFrame(tick);
  }}

  const obs = new IntersectionObserver(entries => {{
    entries.forEach(e => {{
      if (e.isIntersecting) {{
        animateCounter(e.target);
        obs.unobserve(e.target);
      }}
    }});
  }}, {{ threshold: 0.3 }});

  document.querySelectorAll('.counter').forEach(el => obs.observe(el));

  const pobs = new IntersectionObserver(entries => {{
    entries.forEach(e => {{
      if (e.isIntersecting) {{
        e.target.style.width = e.target.dataset.w + '%';
        pobs.unobserve(e.target);
      }}
    }});
  }}, {{ threshold: 0.2 }});

  document.querySelectorAll('.pfill').forEach(el => pobs.observe(el));
}})();
</script>

</body>
</html>"""

    path = NEWS_DIR / f"{aid}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


# ── Index page ────────────────────────────────────────────────────────────────

def build_index(articles: list):
    ordered = sorted(articles, key=lambda x: _parse_date(x.get("date", "")), reverse=True)[:200]

    # Категории и месяцы, реально встречающиеся в данных — только их и показываем в фильтрах
    cats_present = []
    seen_cats = set()
    months_present = {}  # month_key -> label
    for a in ordered:
        cat = a.get("analysis", {}).get("category", "Статистика")
        if cat not in seen_cats:
            seen_cats.add(cat)
            cats_present.append(cat)
        mk = _month_key(a.get("date", ""))
        if mk and mk not in months_present:
            months_present[mk] = _month_label(a.get("date", ""))

    cards = ""
    for a in ordered:
        an = a.get("analysis", {})
        cat = an.get("category", "Статистика")
        c = _cat(cat)
        color = c["color"]
        light = c["light"]
        icon = c["icon"]
        mv = an.get("main_value", "")
        mu = an.get("main_unit", "")
        mv_fmt = _fmt_value(mv) if mv else ""
        month_key = _month_key(a.get("date", ""))

        cards += f"""
    <a href="news/{a['id']}.html" class="card-link" data-cat="{cat}" data-month="{month_key}">
      <div class="card">
        <div class="card-stripe" style="background:{color}"></div>
        <div class="card-body">
          <div class="card-badge" style="background:{light};color:{color}">{icon} {cat}</div>
          <div class="card-title">{an.get('headline', a.get('title',''))[:75]}</div>
          {"<div class='card-num' style='color:" + color + "'>" + mv_fmt + "<span class='card-unit'> " + mu[:18] + "</span></div>" if mv_fmt else "<div style='height:36px'></div>"}
          <div class="card-date">{a.get('date','')}</div>
        </div>
      </div>
    </a>"""

    # Пилюли категорий
    cat_pills = '<button class="pill active" data-cat="all">Все</button>'
    for cat in cats_present:
        icon = _cat(cat)["icon"]
        cat_pills += f'<button class="pill" data-cat="{cat}">{icon} {cat}</button>'

    # Опции месяцев (уже отсортированы по убыванию, т.к. ordered отсортирован по дате)
    month_options = '<option value="all">Все месяцы</option>'
    for mk, label in months_present.items():
        month_options += f'<option value="{mk}">{label}</option>'

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    total = len(articles)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Статистика Узбекистана</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',-apple-system,sans-serif;background:#f0f2f5;color:#1a1a2e}}

.topbar{{
  background:linear-gradient(135deg,#1a3a6e 0%,#1565c0 100%);
  padding:20px 24px 18px;
  position:sticky;top:0;z-index:10;
  box-shadow:0 2px 16px rgba(0,0,0,.2);
}}
.topbar-inner{{max-width:1100px;margin:0 auto;display:flex;justify-content:space-between;align-items:center}}
.site-title{{color:#fff;font-size:20px;font-weight:800;letter-spacing:-.3px}}
.site-sub{{color:rgba(255,255,255,.55);font-size:11px;margin-top:2px;font-weight:500}}
.count-pill{{
  background:rgba(255,255,255,.15);color:#fff;
  font-size:12px;font-weight:700;padding:5px 14px;border-radius:20px;
}}

.filterbar{{
  background:#fff;
  position:sticky;top:76px;z-index:9;
  border-bottom:1px solid #e4e8ec;
  box-shadow:0 1px 6px rgba(0,0,0,.05);
}}
.filterbar-inner{{
  max-width:1100px;margin:0 auto;
  padding:10px 20px;
  display:flex;align-items:center;gap:10px;
  flex-wrap:wrap;
}}
.pills{{
  display:flex;gap:6px;flex-wrap:wrap;flex:1;min-width:0;
}}
.pill{{
  font-family:inherit;
  background:#f0f2f5;color:#546e7a;
  border:none;border-radius:20px;
  font-size:11.5px;font-weight:700;
  padding:6px 13px;cursor:pointer;
  white-space:nowrap;
  transition:background .15s ease,color .15s ease,transform .1s ease;
}}
.pill:hover{{transform:translateY(-1px)}}
.pill.active{{background:#1565c0;color:#fff}}
.month-select{{
  font-family:inherit;
  background:#f0f2f5;color:#37474f;
  border:none;border-radius:20px;
  font-size:11.5px;font-weight:700;
  padding:7px 14px;cursor:pointer;
  margin-left:auto;
}}
.no-results{{
  display:none;
  text-align:center;
  padding:60px 20px;
  color:#90a4ae;
  font-size:13px;
  font-weight:600;
}}
.card-link.hidden{{display:none}}

@media(max-width:480px){{
  .filterbar{{top:70px}}
  .month-select{{margin-left:0}}
}}

.grid{{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
  gap:14px;
  padding:20px 20px 40px;
  max-width:1100px;
  margin:0 auto;
}}
.card-link{{text-decoration:none;color:inherit;display:block}}
.card{{
  background:#fff;
  border-radius:12px;
  overflow:hidden;
  box-shadow:0 1px 8px rgba(0,0,0,.07);
  transition:transform .18s ease,box-shadow .18s ease;
  height:100%;
}}
.card:hover{{transform:translateY(-3px);box-shadow:0 8px 28px rgba(0,0,0,.13)}}
.card-stripe{{height:4px}}
.card-body{{padding:14px 16px 16px}}
.card-badge{{
  display:inline-flex;align-items:center;gap:4px;
  font-size:10px;font-weight:700;padding:3px 10px;
  border-radius:20px;margin-bottom:8px;letter-spacing:.3px;
}}
.card-title{{font-size:12px;font-weight:600;line-height:1.4;color:#1a1a2e;margin-bottom:8px;min-height:32px}}
.card-num{{font-size:28px;font-weight:900;line-height:1;margin-bottom:2px;letter-spacing:-.5px}}
.card-unit{{font-size:12px;font-weight:600;opacity:.65}}
.card-date{{font-size:10px;color:#90a4ae;margin-top:8px;font-weight:500}}

@media(max-width:480px){{
  .grid{{grid-template-columns:1fr 1fr;gap:10px;padding:12px 12px 40px}}
  .card-num{{font-size:22px}}
}}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-inner">
    <div>
      <div class="site-title">📊 Статистика Узбекистана</div>
      <div class="site-sub">Госкомстат УЗ · Обновлено {now}</div>
    </div>
    <div class="count-pill" id="countPill">{total} материалов</div>
  </div>
</div>

<div class="filterbar">
  <div class="filterbar-inner">
    <div class="pills" id="catPills">{cat_pills}</div>
    <select class="month-select" id="monthSelect">{month_options}</select>
  </div>
</div>

<div class="grid" id="grid">{cards}</div>
<div class="no-results" id="noResults">Ничего не найдено по выбранным фильтрам</div>

<script>
(function() {{
  var activeCat = 'all';
  var activeMonth = 'all';
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card-link'));
  var pills = Array.prototype.slice.call(document.querySelectorAll('.pill'));
  var monthSelect = document.getElementById('monthSelect');
  var countPill = document.getElementById('countPill');
  var noResults = document.getElementById('noResults');
  var grid = document.getElementById('grid');

  function applyFilters() {{
    var visible = 0;
    cards.forEach(function(card) {{
      var matchCat = activeCat === 'all' || card.dataset.cat === activeCat;
      var matchMonth = activeMonth === 'all' || card.dataset.month === activeMonth;
      var show = matchCat && matchMonth;
      card.classList.toggle('hidden', !show);
      if (show) visible++;
    }});
    countPill.textContent = visible + (visible === 1 ? ' материал' : ' материалов');
    grid.style.display = visible ? 'grid' : 'none';
    noResults.style.display = visible ? 'none' : 'block';
  }}

  pills.forEach(function(pill) {{
    pill.addEventListener('click', function() {{
      pills.forEach(function(p) {{ p.classList.remove('active'); }});
      pill.classList.add('active');
      activeCat = pill.dataset.cat;
      applyFilters();
    }});
  }});

  monthSelect.addEventListener('change', function() {{
    activeMonth = monthSelect.value;
    applyFilters();
  }});
}})();
</script>

</body>
</html>"""

    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print(f"[site] index.html → {total} статей")
