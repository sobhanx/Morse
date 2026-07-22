# Architecture

Morse uses a **hybrid** layout: one business app (`morse`) holds the source of truth, while legacy Django apps keep their historical `app_label`s and migration graphs.

## Baseline (do not change casually)

| Package | Role |
|---------|------|
| `morse/` | Source of truth: models, views, services, tenant, middleware, signals, management commands, admin |
| `accounts/` | Authentication only (`AUTH_USER_MODEL = accounts.User`) — do not fold into `morse` |
| `config/` | Project shell: settings, root URLs, ASGI |
| `websites/`, `contacts/`, `inbox/`, `knowledge/` | Installed apps for **legacy `app_label`s**, migrations, and thin re-export shims |
| `widget/`, `dashboard/` | URL include packages only (not in `INSTALLED_APPS`) |

Models live under `morse/models/` but declare legacy labels, e.g. `class Meta: app_label = "inbox"`. That keeps existing tables, migration history, and ContentTypes stable **without** `SeparateDatabaseAndState` or ContentType remapping.

## Import preference

Prefer `morse.*` in new code:

```python
from morse.models import Contact, Conversation
from morse.permissions import website_required
from morse.services.telegram import send_telegram_notification
```

Legacy paths (`websites.permissions`, `inbox.models`, …) remain as shims for older imports and URL packages.

## Shim policy

### Keep (required for hybrid baseline)

- Legacy app packages in `INSTALLED_APPS` (`websites`, `contacts`, `inbox`, `knowledge`) — required so Django resolves `app_label` migrations
- `*/models.py` re-exports — safe and useful for `from inbox.models import …`
- `*/urls.py` — public URL namespaces (`dashboard:`, `widget:`, `inbox:`, …) stay stable
- `websites/templatetags/website_i18n.py` — Django discovers tags by installed app; keep here (calls `morse.demo`)
- Compatibility shims: `websites/{tenant,permissions,middleware,demo,platform_monitor}.py`, `inbox/{views,consumers,signals,routing}.py`, `knowledge/{localization,demo_content}.py`, etc.

### Safe to remove later (optional cleanup)

Only after nothing imports the old path:

- Explicit re-exports in `websites.admin` of `website_usage_queryset` / `website_usage_dashboard` (prefer `morse.usage` / `morse.admin`)
- `inbox.services` package (prefer `morse.services`)
- Empty `ready()` hooks or unused `apps.py` in packages that are not installed (`widget`, `dashboard`)

### Do not remove / do not migrate without a dedicated project

- Changing `Meta.app_label` to `morse`
- `SeparateDatabaseAndState` or ContentType migrations
- Moving auth out of `accounts` or changing `AUTH_USER_MODEL`
- Deleting migration history under legacy apps

## Layout sketch

```
morse/
  models/          # Website, Contact, Conversation, Message, Article, Category
  views/           # dashboard, inbox, widget, websites, knowledge, telegram
  services/        # Telegram notify + linking
  management/      # seed_demo, setup_website, telegram_*
  admin.py         # All domain ModelAdmins
  usage.py         # website_usage_queryset (shared by admin + monitor)
  tenant.py        # TenantManager / contextvars
  permissions.py   # Widget key + website access helpers
  middleware.py    # WebsiteMiddleware
  signals.py       # Message → Telegram alerts
  consumers.py     # Channels WebSocket consumers
  routing.py       # websocket_urlpatterns

accounts/          # User, SMS login — unchanged
config/            # settings, urls, asgi
```

## Runtime tenancy

1. `morse.middleware.WebsiteMiddleware` sets `request.website` from widget key or session.
2. `TenantManager` filters ORM queries by the current website context.
3. Public widget/help identify the tenant **only** via `public_widget_key` (`?key=`).

## Verification notes

- Prefer imports from `morse.*` to avoid relying on shim modules.
- Admin registrations live in `morse.admin`; legacy `*/admin.py` files are empty or re-export helpers only.
- Management commands are registered under the `morse` app.
