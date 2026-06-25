# Настройка GitHub репозитория

## Шаг 1 — Создать репозиторий на GitHub

1. Зайти на [github.com](https://github.com)
2. Нажать **+** (правый верхний угол) → **New repository**
3. Repository name: `statuz-infographics`
4. Выбрать **Public**
5. Нажать **Create repository**

## Шаг 2 — Загрузить файлы в репозиторий

На странице репозитория нажать **uploading an existing file** и перетащить все файлы из этой папки (`github-repo/`).

Или через терминал:
```bash
cd github-repo
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/ТВОЙ_ЛОГИН/statuz-infographics.git
git push -u origin main
```

## Шаг 3 — Включить GitHub Pages

1. В репозитории → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: **main**, папка: **/docs**
4. Нажать **Save**

Через 2 минуты сайт будет на: `https://ТВОЙ_ЛОГИН.github.io/statuz-infographics`

## Шаг 4 — Добавить секреты (токены)

В репозитории → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Добавить три секрета:

| Название | Значение |
|----------|----------|
| `TELEGRAM_BOT_TOKEN` | 123...:AAx... (от @BotFather) |
| `TELEGRAM_CHANNEL_ID` | @канал или -100... |

## Шаг 6 — Запустить первый раз вручную

В репозитории → **Actions** → **Update Uzbekistan Statistics** → **Run workflow** → **Run workflow**

Следить за выполнением. Через 3-5 минут на сайте появятся первые статьи.

После этого бот будет запускаться сам каждые 3 часа, без твоего участия.
