# Morse

**Multi-tenant SaaS** customer support platform: each customer owns one or more websites with fully isolated data. Customers integrate using only a generated **widget key** — no project-specific configuration required.

## Features

- **Multi-tenant websites** — Each website is an isolated tenant with its own widget key, inbox, CRM, and knowledge base
- **Live Chat Widget** — Embeddable chat bubble identified by `public_widget_key` only
- **Persistent visitors** — Stable visitor IDs stored in the parent page `localStorage` and passed into the widget iframe
- **Voice messages** — Visitors can send voice notes (up to 60 seconds); agents play them in the inbox
- **Shared Inbox** — Per-website agent inbox with filters, assignment, status management, WebSockets, and HTTP polling fallback
- **Support CRM** — Contact profiles, notes, and conversation history (scoped per website)
- **Knowledge Base** — Public help center with searchable articles **per website** (use the correct `?key=`)
- **Analytics** — Per-website support metrics dashboard
- **Bilingual UI** — Persian (default) and English, with an in-app language switcher

## Quick Start (development)

```bash
cp .env.example .env
pip install -r requirements.txt
python manage.py migrate
python manage.py compilemessages
python manage.py seed_demo
daphne -b 0.0.0.0 -p 8002 config.asgi:application
```

> **Important:** Use `daphne`, not `python manage.py runserver`. Real-time chat uses WebSockets. The inbox also polls over HTTP so conversations stay fresh if a socket drops.

`seed_demo` prints the demo website's `public_widget_key`.

Open:

- Landing: `http://127.0.0.1:8002/`
- Demo chat: `http://127.0.0.1:8002/widget/demo/?key=<PUBLIC_KEY>`
- Demo help: `http://127.0.0.1:8002/help/?key=<PUBLIC_KEY>` (or `/help/` without a key for the demo tenant)

### Reset development database

If you have an old `db.sqlite3` from earlier setups (e.g. with legacy tenant domains), start clean:

```bash
rm -f db.sqlite3
python manage.py migrate
python manage.py seed_demo
```

Uploaded voice files live under `media/` (served automatically when `DEBUG=True`).

## Onboard a customer

1. **Create an agent account** — The customer owner signs up via SMS login, or you create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

2. **Create and activate their website:**
   ```bash
   python manage.py setup_website --name "Acme Corp" --domain acme.com --owner-phone 09120000000
   ```

3. **Share the widget key and embed script** — The command prints:
   - `public_widget_key`
   - Embed snippet: `<script src="https://your-host/widget/embed.js?key=..."></script>`

4. **Production env** — Set `PUBLIC_BASE_URL`, `CSRF_TRUSTED_ORIGINS` (customer domains), and `WIDGET_EMBED_CROSS_ORIGIN=1` when embedding on external sites over HTTPS.

The widget identifies itself **only** via `public_widget_key`. Never send `website_id` from the frontend.

### Knowledge base note

Help articles are scoped to a website. Django admin can list articles from every tenant; the public Help Center only shows articles for the website resolved by `?key=`. Always open Help with that site’s widget key (dashboard → Help, or website settings).

## Management commands

| Command | Purpose |
|---------|---------|
| `seed_demo` | Local demo tenant (`demo.example.com`), sample KB, conversation, and admin user |
| `setup_website` | Create/update a customer website, activate it, assign owner as agent, print embed details |
| `compilemessages` | Build `.mo` files for FA/EN translations after editing `.po` files |
| `telegram_set_webhook` | Register `/inbox/telegram/webhook/` with Telegram `setWebhook` |
| `telegram_get_webhook_info` | Show Telegram's current webhook configuration |

### `seed_demo`

Uses `DEMO_ADMIN_PHONE` and `DEMO_ADMIN_PASSWORD` from the environment (defaults: `09000000000` / `changeme-demo`).

### `setup_website`

```bash
python manage.py setup_website --name "Customer Name" --domain customer.com [--owner-phone 09...]
```

If `--owner-phone` is omitted, the first superuser becomes the owner.

### Telegram webhook

1. Set env vars:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_WEBHOOK_URL` (public HTTPS URL, e.g. `https://your-host/inbox/telegram/webhook/`)
   - `TELEGRAM_WEBHOOK_SECRET` (recommended)
   - `TELEGRAM_BOT_USERNAME` (for deep links)
2. Register the webhook:
   ```bash
   python manage.py telegram_set_webhook
   ```
3. Verify:
   ```bash
   python manage.py telegram_get_webhook_info
   ```

Optional overrides: `telegram_set_webhook --url ... --secret ...`.

## Environment variables

Copy `.env.example` to `.env` and configure:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key (required in production) |
| `DEBUG` | `True` by default in development |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `PRODUCT_NAME` | Optional product display name (default: `Morse`) |
| `PUBLIC_BASE_URL` | Public base URL of this deployment |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins (customer sites) |
| `WIDGET_EMBED_CROSS_ORIGIN` | `1` to allow cross-site widget cookies (production embed) |
| `SESSION_COOKIE_SECURE` | `1` when using HTTPS with cross-origin embed |
| `SMS_IR_API_KEY` | SMS.ir API key (SMS login) |
| `SMS_IR_LINE_NUMBER` | SMS.ir line number |
| `SMS_IR_VERIFY_TEMPLATE_ID` | SMS.ir verification template ID |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (alerts + account linking) |
| `TELEGRAM_CHAT_ID` | Optional operator chat/channel ID for agent alerts |
| `TELEGRAM_BOT_USERNAME` | Bot username (no `@`) for `t.me` deep links |
| `TELEGRAM_WEBHOOK_URL` | Public HTTPS webhook URL for `telegram_set_webhook` |
| `TELEGRAM_WEBHOOK_SECRET` | Optional secret for Telegram webhook header checks |
| `DEMO_ADMIN_PHONE` | Demo admin phone for `seed_demo` |
| `DEMO_ADMIN_PASSWORD` | Demo admin password for `seed_demo` |

SMS login requires all three `SMS_IR_*` variables. Without them, login attempts log an error and SMS is not sent.

Telegram **operator alerts** require `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (see `inbox.services.telegram`).

Telegram **visitor account linking** uses deep links `https://t.me/<TELEGRAM_BOT_USERNAME>?start=<token>` and the webhook at `/inbox/telegram/webhook/`. Register it with `python manage.py telegram_set_webhook` (requires `TELEGRAM_WEBHOOK_URL`; optional `TELEGRAM_WEBHOOK_SECRET`).

## Demo credentials

After `seed_demo` (default env):

| Role  | Phone | Password |
|-------|-------|----------|
| Agent | `09000000000` | `changeme-demo` |

## Key URLs

| URL | Description |
|-----|-------------|
| `/` | Landing page |
| `/accounts/login/` | Agent SMS login |
| `/websites/` | Manage and switch websites |
| `/inbox/` | Shared inbox (login + active website) |
| `/contacts/` | CRM contacts list |
| `/analytics/` | Per-website analytics |
| `/admin/` | Django admin |
| `/widget/demo/?key=PUBLIC_KEY` | Chat widget demo |
| `/widget/embed.js?key=PUBLIC_KEY` | Embeddable widget script |
| `/help/?key=PUBLIC_KEY` | Public knowledge base for that website |
| `/inbox/telegram/webhook/` | Telegram Bot API webhook (account linking) |
| `/i18n/setlang/` | Language switch endpoint (FA/EN) |

## Embed the chat widget

```html
<script src="https://your-morse-host/widget/embed.js?key=YOUR_PUBLIC_WIDGET_KEY"></script>
```

Paste before `</body>` on the customer's website.

The embed script:

- Resolves the tenant from `key` only
- Stores a stable visitor ID in the **parent page** `localStorage` (`morse_visitor_id` / `morse_visitor_id:<key>`)
- Passes that ID into the chat iframe so refresh and page navigation keep the same visitor
- Loads the floating chat UI (text + voice)

Hard-refresh customer pages after updating Morse if the browser cached an old `/widget/embed.js`.

## Multi-tenant architecture

```
websites/        # Website (tenant) model, middleware, permissions
contacts/        # Visitors — FK to Website (session_id + short visitor_id)
inbox/           # Conversations, messages (text + voice) — FK to Website
knowledge/       # FAQ articles — FK to Website
widget/          # Public endpoints resolved by public_widget_key
dashboard/       # Agent UI scoped to session active website
accounts/        # SMS login agents / owners
locale/          # FA/EN translations
media/           # Uploaded voice files (local/dev)
```

- `WebsiteMiddleware` sets `request.website` from widget key (public paths) or session (dashboard)
- `TenantManager` auto-filters queries by the current website context
- Reverse relations (e.g. `category.articles`) are FK-scoped and do not re-apply a mismatched website filter
- Website owners and agents only see their websites; superusers see all
- Django admin can show cross-tenant rows — use the **Website** column/filter on knowledge models

## Localization

- Default language: Persian (`fa`); also supports English (`en`)
- Time zone: `Asia/Tehran`
- After changing strings in templates/code, update `locale/*/LC_MESSAGES/django.po` (or `scripts/fill_fa_translations.py`) and run `python manage.py compilemessages`

## Tech stack

- Django 5 + MVT pattern
- Django Channels (WebSockets) with in-memory channel layer (dev)
- Daphne ASGI server
- SQLite (development)
- Vanilla JS + CSS
- Pillow (voice/media handling)
