# Morse

A Crisp-inspired customer support platform built with Django. **Multi-tenant SaaS**: each customer owns one or more websites with fully isolated data. Customers integrate using only a generated **widget key** — no project-specific configuration required.

## Features

- **Multi-tenant websites** — Each website is an isolated tenant with its own widget key, inbox, CRM, and knowledge base
- **Live Chat Widget** — Embeddable chat bubble identified by `public_widget_key` only
- **Shared Inbox** — Per-website agent inbox with filters, assignment, and status management
- **Support CRM** — Contact profiles, notes, and conversation history (scoped per website)
- **Knowledge Base** — Public help center with searchable articles per website
- **Analytics** — Per-website support metrics dashboard

## Quick Start (development)

```bash
cp .env.example .env
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
daphne -b 0.0.0.0 -p 8002 config.asgi:application
```

> **Important:** Use `daphne`, not `python manage.py runserver`. The chat widget needs WebSockets.

`seed_demo` prints the demo website's `public_widget_key`.

### Reset development database

If you have an old `db.sqlite3` from earlier setups (e.g. with legacy tenant domains), start clean:

```bash
rm -f db.sqlite3
python manage.py migrate
python manage.py seed_demo
```

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

## Management commands

| Command | Purpose |
|---------|---------|
| `seed_demo` | Local demo tenant (`demo.example.com`), sample KB, conversation, and admin user |
| `setup_website` | Create/update a customer website, activate it, assign owner as agent, print embed details |

### `seed_demo`

Uses `DEMO_ADMIN_PHONE` and `DEMO_ADMIN_PASSWORD` from the environment (defaults: `09000000000` / `changeme-demo`).

### `setup_website`

```bash
python manage.py setup_website --name "Customer Name" --domain customer.com [--owner-phone 09...]
```

If `--owner-phone` is omitted, the first superuser becomes the owner.

## Environment variables

Copy `.env.example` to `.env` and configure:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key (required in production) |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `PUBLIC_BASE_URL` | Public base URL of this deployment |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins (customer sites) |
| `WIDGET_EMBED_CROSS_ORIGIN` | `1` to allow cross-site widget cookies (production embed) |
| `SESSION_COOKIE_SECURE` | `1` when using HTTPS with cross-origin embed |
| `SMS_IR_API_KEY` | SMS.ir API key (SMS login) |
| `SMS_IR_LINE_NUMBER` | SMS.ir line number |
| `SMS_IR_VERIFY_TEMPLATE_ID` | SMS.ir verification template ID |
| `DEMO_ADMIN_PHONE` | Demo admin phone for `seed_demo` |
| `DEMO_ADMIN_PASSWORD` | Demo admin password for `seed_demo` |

SMS login requires all three `SMS_IR_*` variables. Without them, login attempts log an error and SMS is not sent.

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
| `/inbox/` | Shared inbox (requires login + active website) |
| `/widget/demo/?key=PUBLIC_KEY` | Chat widget demo |
| `/widget/embed.js?key=PUBLIC_KEY` | Embeddable widget script |
| `/help/?key=PUBLIC_KEY` | Public knowledge base |

## Embed the chat widget

```html
<script src="https://your-morse-host/widget/embed.js?key=YOUR_PUBLIC_WIDGET_KEY"></script>
```

Paste before `</body>` on the customer's website.

## Multi-tenant architecture

```
websites/        # Website (tenant) model, middleware, permissions
contacts/        # Visitors — FK to Website
inbox/           # Conversations, messages — FK to Website
knowledge/       # FAQ articles — FK to Website
widget/          # Public endpoints resolved by public_widget_key
dashboard/       # Agent UI scoped to session active website
```

- `WebsiteMiddleware` sets `request.website` from widget key or session
- `TenantManager` auto-filters queries by `request.website`
- Website owners and agents only see their websites; superusers see all

## Tech stack

- Django 5 + MVT pattern
- Django Channels (WebSockets)
- Daphne ASGI server
- SQLite (development)
- Vanilla JS + CSS

Inspired by [Crisp](https://crisp.chat/en/).
