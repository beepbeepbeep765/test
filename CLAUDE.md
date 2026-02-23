# CLAUDE.md

This file provides context, conventions, and workflow guidance for AI assistants (e.g., Claude Code) working in this repository.

---

## Project: ACRe Solutions Capital Markets CRM

A lightweight internal web application for the ACRe Solutions capital markets team to:

1. **Track deal outreach** — log every contact made for each deal being marketed, including who sent it, date, message summary, response, and follow-up flags.
2. **Farm GP contacts** — maintain a searchable database of General Partners (GPs) to approach for future equity raises.
3. **Manage LP investors** — track individual LP investor relationships and commitments.
4. **Manage lenders** — maintain a directory of lender contacts with loan parameters.
5. **Sync Outlook emails** — import and archive emails from Exchange/Outlook, linked to deals and contacts.
6. **Run bulk email campaigns** — draft and send outreach campaigns with a review-before-send workflow.
7. **Semantic search** — full-text and ML-powered search across contacts, deals, and emails.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Web framework | Flask 3.x |
| Database | SQLite (file: `crm.db`) |
| Frontend | Bootstrap 5.3 + Bootstrap Icons (CDN) |
| Typography | Inter font (Google Fonts) |
| Semantic search | sentence-transformers (`all-MiniLM-L6-v2`, ~80 MB, local) |
| Data import | openpyxl (Excel/CSV Preqin import) |
| Email sync | pywin32 / MAPI (Windows only) |
| Production server | Gunicorn |
| Hosting | Render (see `render.yaml`) |

---

## Project Structure

```
acre-crm/
├── app.py                  # Flask app — all 60+ routes, DB logic, utilities
├── search_engine.py        # Local semantic search (sentence-transformers)
├── run.py                  # Local dev runner (python run.py)
├── requirements.txt        # Python dependencies
├── Procfile                # Gunicorn start command for Render/Heroku
├── render.yaml             # Render deployment config
├── setup_acre_crm.py       # Windows bootstrap/installer script
├── update_crm.py           # Script to update an existing installation
├── .gitignore
├── templates/
│   ├── base.html               # Navbar, flash messages, Bootstrap imports
│   ├── login.html              # Password login page
│   ├── index.html              # Dashboard with stats + active deals
│   ├── deals.html              # All deals list
│   ├── deal_form.html          # Create / edit a deal
│   ├── deal_detail.html        # Single deal view with outreach log
│   ├── deal_report.html        # Printable deal report
│   ├── outreach_form.html      # Log / edit an outreach entry
│   ├── contacts.html           # GP contacts list with search + filter
│   ├── contact_form.html       # Add / edit a GP contact
│   ├── contact_detail.html     # Single GP contact view with notes
│   ├── contacts_import.html    # Preqin CSV/Excel import UI
│   ├── lp_investors.html       # LP investor list
│   ├── lp_investor_form.html   # Add / edit LP investor
│   ├── lp_investor_detail.html # Single LP investor view
│   ├── lenders.html            # Lender list
│   ├── lender_form.html        # Add / edit lender
│   ├── lender_detail.html      # Single lender view
│   ├── emails.html             # Two-pane Outlook-style email archive
│   ├── email_detail.html       # Full email view
│   ├── email_pane.html         # AJAX reading pane (partial)
│   ├── outlook_sync.html       # Outlook email sync controls
│   ├── campaigns.html          # Campaign list
│   ├── campaign_new.html       # Create new campaign
│   ├── campaign_review.html    # Review emails before sending
│   ├── templates.html          # Email template library
│   ├── template_form.html      # Add / edit email template
│   ├── activity.html           # Activity log
│   ├── reminders.html          # Follow-up reminders with quick actions
│   └── search_results.html     # Global semantic search results
└── static/
    └── style.css               # Custom styles (Bootstrap-first, ~900 lines)
```

---

## Database Schema

Ten tables, all in `crm.db` (SQLite). The DB is auto-created on first startup via `init_db()`. Schema migrations are applied safely with `try/except` around `ALTER TABLE` statements — no migration tool required.

### `deals`
CRE deals being marketed.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT NOT NULL | Deal name |
| asset_type | TEXT | e.g. Multifamily, Office |
| location | TEXT | e.g. Atlanta, GA |
| target_raise | TEXT | e.g. $25M |
| status | TEXT | Active / On Hold / Closed / Dead |
| notes | TEXT | Free-form deal summary |
| purchase_price | TEXT | |
| units_sf | TEXT | Units or square footage |
| noi_current | TEXT | Current NOI |
| noi_projected | TEXT | Projected NOI |
| cap_rate | TEXT | |
| exit_cap_rate | TEXT | |
| ltv | TEXT | Loan-to-value |
| hold_period | TEXT | e.g. 5 years |
| irr_target | TEXT | |
| equity_multiple | TEXT | |
| closing_date | TEXT | ISO date |
| email_keywords | TEXT | Comma-separated terms for Outlook auto-linking |
| created_at | TEXT | ISO datetime (auto) |

### `outreach`
One row per outreach attempt, linked to a deal.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| deal_id | INTEGER FK | References `deals.id` |
| contact_name | TEXT NOT NULL | |
| company | TEXT | |
| email | TEXT | |
| sent_by | TEXT | Which team member sent it |
| outreach_date | TEXT | ISO date |
| outreach_summary | TEXT | What we sent/said |
| response_date | TEXT | ISO date |
| response_summary | TEXT | Their reply/outcome |
| follow_up_needed | INTEGER | 0 or 1 (boolean) |
| follow_up_date | TEXT | ISO date |
| stage | TEXT | Initial Email / Follow-Up / Meeting / LOI / Closed (default: Initial Email) |
| interest_level | TEXT | Unknown / Low / Medium / High (default: Unknown) |
| created_at | TEXT | ISO datetime (auto) |

### `gp_contacts`
GP farming database.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT NOT NULL | |
| title | TEXT | e.g. Managing Partner |
| company | TEXT | Firm name |
| email | TEXT | |
| phone | TEXT | |
| location | TEXT | |
| aum_range | TEXT | e.g. $100M–$500M |
| strategy | TEXT | e.g. Value-add multifamily |
| min_check | TEXT | Min equity check size |
| max_check | TEXT | Max equity check size |
| source | TEXT | Where the contact was found |
| status | TEXT | New / In Contact / Meeting Scheduled / Hot Lead / Passed |
| notes | TEXT | Relationship/fit notes |
| last_contacted | TEXT | ISO date |
| next_contact_date | TEXT | ISO date |
| created_at | TEXT | ISO datetime (auto) |

### `contact_notes`
Time-stamped notes attached to GP contacts.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| contact_id | INTEGER FK | References `gp_contacts.id` |
| note_date | TEXT | ISO date |
| note_text | TEXT NOT NULL | |
| created_at | TEXT | ISO datetime (auto) |

### `email_templates`
Reusable email template library. Four defaults are seeded on first startup.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT NOT NULL | Template display name |
| subject | TEXT | Subject line (may contain `[PLACEHOLDERS]`) |
| body | TEXT NOT NULL | Body text (may contain `[PLACEHOLDERS]`) |
| created_at | TEXT | ISO datetime (auto) |

### `emails`
Synced Outlook/Exchange emails.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| subject | TEXT | |
| body | TEXT | Full email body |
| from_addr | TEXT | Sender address |
| to_addr | TEXT | Recipient address(es) |
| cc_addr | TEXT | CC addresses |
| sent_on | TEXT | ISO datetime |
| direction | TEXT | `sent` or `received` (default: `sent`) |
| tags | TEXT | Comma-separated tags |
| deal_id | INTEGER FK | Optional link to `deals.id` |
| contact_id | INTEGER FK | Optional link to `gp_contacts.id` |
| entry_id | TEXT UNIQUE | Exchange/MAPI entry ID (prevents duplicates) |
| created_at | TEXT | ISO datetime (auto) |

### `lp_investors`
LP investor tracking.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT NOT NULL | |
| title | TEXT | |
| company | TEXT | |
| email | TEXT | |
| phone | TEXT | |
| location | TEXT | |
| net_worth | TEXT | |
| preferred_asset_types | TEXT | |
| preferred_markets | TEXT | |
| min_check | TEXT | |
| max_check | TEXT | |
| hold_period_pref | TEXT | |
| accredited | TEXT | Yes / No (default: Yes) |
| source | TEXT | |
| status | TEXT | New / In Contact / Meeting Scheduled / Committed / Passed |
| notes | TEXT | |
| last_contacted | TEXT | ISO date |
| next_contact_date | TEXT | ISO date |
| created_at | TEXT | ISO datetime (auto) |

### `lenders`
Lender directory with loan parameters.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT NOT NULL | Contact name |
| title | TEXT | |
| company | TEXT | Institution name |
| email | TEXT | |
| phone | TEXT | |
| lender_type | TEXT | e.g. Bridge, Perm, CMBS, Life Co |
| loan_types | TEXT | |
| asset_types | TEXT | Asset types they lend on |
| min_loan | TEXT | |
| max_loan | TEXT | |
| max_ltv | TEXT | |
| typical_rate | TEXT | |
| recourse | TEXT | Full / Partial / Non |
| markets | TEXT | Geographic focus |
| typical_term | TEXT | |
| origination_fee | TEXT | |
| status | TEXT | New / Active / Inactive |
| notes | TEXT | |
| last_contacted | TEXT | ISO date |
| created_at | TEXT | ISO datetime (auto) |

### `campaigns`
Bulk email campaign metadata.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT NOT NULL | Campaign display name |
| subject | TEXT NOT NULL | Email subject (Jinja2 template) |
| body_template | TEXT NOT NULL | Email body (Jinja2 template) |
| status | TEXT | `draft` / `sent` (default: `draft`) |
| total_count | INTEGER | Total emails generated |
| sent_count | INTEGER | Emails successfully sent |
| created_at | TEXT | ISO datetime (auto) |
| sent_at | TEXT | ISO datetime when sent |

### `campaign_emails`
Individual emails within a campaign (one row per recipient).

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| campaign_id | INTEGER FK | References `campaigns.id` |
| contact_id | INTEGER FK | Optional reference to `gp_contacts.id` |
| to_name | TEXT | Recipient display name |
| to_email | TEXT | Recipient email address |
| company | TEXT | Recipient company |
| subject | TEXT | Rendered subject |
| body | TEXT | Rendered body |
| status | TEXT | `pending` / `sent` / `failed` |
| created_at | TEXT | ISO datetime (auto) |
| sent_at | TEXT | ISO datetime when sent |

---

## Running Locally

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the dev server (auto-creates crm.db on first run)
python run.py
```

Open `http://localhost:5000`. Default password: `acre2026` (set via `CRM_PASSWORD` env var).

The `sentence-transformers` model (`all-MiniLM-L6-v2`, ~80 MB) is downloaded on first search and cached locally by the library.

---

## Environment Variables

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | `dev-secret-change-in-prod` | Flask session secret — **must** be set in production |
| `CRM_PASSWORD` | `acre2026` | Single shared password for login |
| `DATABASE_PATH` | `crm.db` | Path to the SQLite database file |

---

## Deploying to Render

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) → New → Web Service → connect the repo.
3. Render auto-detects `render.yaml` — click **Create Web Service**.
4. `SECRET_KEY` is auto-generated by Render; `DATABASE_PATH` points to a persistent disk at `/opt/render/project/src/crm.db`.

> **SQLite on Render free tier:** The free tier does not include persistent disk storage. Data will be lost on redeploy. Either upgrade to a paid plan with a persistent disk, or migrate `app.py` to use Render's managed Postgres if long-term persistence is needed.

---

## Key Utilities in `app.py`

### `fmtdatetime` template filter
Formats `'YYYY-MM-DD HH:MM'` or `'YYYY-MM-DD'` into `'Feb 20 · 2:30 PM'` or `'Feb 20'`. Register as `@app.template_filter("fmtdatetime")`. Use in templates as `{{ value | fmtdatetime }}`.

### `parse_money(s)`
Strips `$`, commas, and whitespace from a money string and returns a float (or `0.0` on failure). Used internally for numeric comparisons.

### `score_gp(gp, deal)`
Scores a GP contact against a deal based on check size overlap and strategy match. Returns a float score for sorting GP match lists.

### Authentication (`require_login`)
All routes except `/login`, `/logout`, and `/static` require `session['logged_in'] == True`. Unauthenticated requests redirect to `/login?next=<original_path>`.

---

## Outlook / Email Sync

- Email sync (`/emails/sync`) is **Windows-only** — it uses `pywin32` (MAPI/COM).
- MAPI COM operations run in a **dedicated thread** to avoid `CoInitialize` errors. Do not call MAPI from the main Flask thread.
- Sender resolution uses `GetExchangeUser` to convert Exchange DNs to SMTP addresses.
- Per-deal `email_keywords` (comma-separated) are used for auto-linking synced emails to deals.
- The `entry_id` column on `emails` prevents duplicate imports.

---

## Campaign / Bulk Email Flow

1. **Create campaign** (`/campaigns/new`): Select a deal, GP filter criteria, and a template. The app generates individual `campaign_emails` rows (one per matching GP contact) by rendering the Jinja2 body template with per-contact variables.
2. **Review** (`/campaigns/<id>/review`): Browse each rendered email before sending.
3. **Send** (`/campaigns/<id>/send` POST): Iterates `campaign_emails` with status `pending`, sends via MAPI, and marks each `sent` or `failed`.

---

## Semantic Search (`search_engine.py`)

- Model: `all-MiniLM-L6-v2` (loaded lazily on first use, cached by the library).
- `semantic_search(query, items, text_fn, top_k=8, threshold=0.2)` — takes a list of dicts, a callable that builds searchable text per item, and returns `[(item, score), ...]` sorted by descending relevance.
- No data ever leaves the machine — fully local inference.
- Also used in `/emails` for semantic email search and `/search` for global cross-entity search.

---

## All Routes

### Auth
| Method | URL | Description |
|---|---|---|
| GET/POST | `/login` | Login page |
| GET | `/logout` | Clear session and redirect to login |

### Dashboard
| Method | URL | Description |
|---|---|---|
| GET | `/` | Dashboard: stats, active deals, recent activity |

### Deals
| Method | URL | Description |
|---|---|---|
| GET | `/deals` | All deals list |
| GET/POST | `/deals/new` | Create deal |
| GET | `/deals/<id>` | Deal detail with outreach log |
| GET/POST | `/deals/<id>/edit` | Edit deal |
| POST | `/deals/<id>/delete` | Delete deal |
| GET | `/deals/<id>/report` | Printable deal report |
| GET | `/deals/export.csv` | Export all deals as CSV |

### Outreach
| Method | URL | Description |
|---|---|---|
| GET | `/deals/<id>/outreach/export.csv` | Export outreach log as CSV |
| GET/POST | `/deals/<id>/outreach/new` | Log new outreach |
| GET/POST | `/deals/<id>/outreach/<oid>/edit` | Edit outreach entry |
| POST | `/deals/<id>/outreach/<oid>/delete` | Delete outreach entry |
| POST | `/outreach/from-email` | Create outreach entry from a synced email |

### GP Contacts
| Method | URL | Description |
|---|---|---|
| GET | `/contacts` | GP contacts list with search and filters |
| GET/POST | `/contacts/new` | Add GP contact |
| GET | `/contacts/<id>` | GP contact detail with notes |
| GET/POST | `/contacts/<id>/edit` | Edit GP contact |
| POST | `/contacts/<id>/delete` | Delete GP contact |
| POST | `/contacts/<id>/notes/add` | Add a note to a GP contact |
| POST | `/contacts/<id>/notes/<nid>/delete` | Delete a note |
| GET/POST | `/contacts/import` | Upload Preqin Excel/CSV for import |
| POST | `/contacts/import/confirm` | Confirm and save imported contacts |
| GET | `/contacts/export.csv` | Export GP contacts as CSV |

### LP Investors
| Method | URL | Description |
|---|---|---|
| GET | `/lp-investors` | LP investor list |
| GET/POST | `/lp-investors/new` | Add LP investor |
| GET | `/lp-investors/<id>` | LP investor detail |
| GET/POST | `/lp-investors/<id>/edit` | Edit LP investor |
| POST | `/lp-investors/<id>/delete` | Delete LP investor |
| GET | `/lp-investors/export.csv` | Export LP investors as CSV |

### Lenders
| Method | URL | Description |
|---|---|---|
| GET | `/lenders` | Lender list |
| GET/POST | `/lenders/new` | Add lender |
| GET | `/lenders/<id>` | Lender detail |
| GET/POST | `/lenders/<id>/edit` | Edit lender |
| POST | `/lenders/<id>/delete` | Delete lender |
| GET | `/lenders/export.csv` | Export lenders as CSV |

### Emails
| Method | URL | Description |
|---|---|---|
| GET | `/emails` | Two-pane email archive with semantic search |
| GET | `/emails/<id>` | Full email detail view |
| GET | `/emails/<id>/pane` | Partial: reading pane HTML fragment |
| POST | `/emails/sync` | Trigger Outlook sync (Windows only) |
| POST | `/emails/<id>/link` | Link email to a deal |
| POST | `/emails/<id>/delete` | Delete email |
| GET/POST | `/deals/<id>/outlook` | Outlook sync page for a specific deal |
| POST | `/deals/<id>/outlook/import` | Import emails for a deal |

### Campaigns
| Method | URL | Description |
|---|---|---|
| GET | `/campaigns` | Campaign list |
| GET/POST | `/campaigns/new` | Create campaign (select deal, template, GP filter) |
| GET | `/campaigns/<id>/review` | Review rendered emails before sending |
| POST | `/campaigns/<id>/send` | Send all pending emails in a campaign |
| POST | `/campaigns/<id>/delete` | Delete campaign |

### Templates
| Method | URL | Description |
|---|---|---|
| GET | `/templates` | Email template library |
| GET/POST | `/templates/new` | Create template |
| GET/POST | `/templates/<id>/edit` | Edit template |
| POST | `/templates/<id>/delete` | Delete template |

### Utilities
| Method | URL | Description |
|---|---|---|
| GET | `/activity` | Recent activity log across all entities |
| GET | `/reminders` | Follow-up reminders for outreach and contacts |
| POST | `/reminders/quick` | Quick-action: reschedule or dismiss a reminder |
| POST | `/reminders/dismiss/<kind>/<id>` | Dismiss a specific reminder |
| GET | `/search` | Global semantic search across all entities |

---

## Development Conventions

### Adding new fields
- Schema is defined in `init_db()` in `app.py`. Modify the `CREATE TABLE IF NOT EXISTS` statements.
- For adding columns to an **existing** database: add an `ALTER TABLE ... ADD COLUMN ...` statement in the safe migration block inside `init_db()` (inside the `for stmt in [...]:` loop with the `try/except`). This runs at every startup but is harmless if the column already exists.
- In dev, you can also delete `crm.db` and let it recreate.

### Adding new routes
- All routes live in `app.py`. Follow the existing pattern: GET renders a template, POST processes the form and redirects.
- Use `flash()` for user feedback (`"success"`, `"danger"`, `"info"` as the category).
- Always redirect after POST to prevent double-submission on browser refresh (PRG pattern).
- Protect any new route by ensuring `require_login` (applied via `@app.before_request`) will catch it — i.e., do **not** add it to the `("login", "logout", "static")` exclusion list unless it genuinely must be public.

### Templates
- All templates extend `base.html`.
- Use Bootstrap 5 utility classes first; add custom CSS to `static/style.css` only when Bootstrap doesn't cover it.
- Keep forms and tables consistent with existing patterns in `deal_form.html` / `contacts.html`.
- The `fmtdatetime` filter is available globally: `{{ row.created_at | fmtdatetime }}`.

### Semantic search
- Use `from search_engine import semantic_search` where needed.
- Provide a `text_fn` callable that concatenates all searchable fields for an entity into a single string.
- Default `top_k=8`, `threshold=0.2` — adjust per use case.

### Security
- Never put real credentials or `.env` files in the repo.
- `SECRET_KEY` must be set via environment variable in production.
- `crm.db` is in `.gitignore` — never commit the database file.
- Use parameterised SQLite queries (`?` placeholders) — never interpolate user input into SQL strings.

---

## Git Workflow

- `master` — primary branch
- `claude/<description>-<session-id>` — AI assistant working branches
- Write imperative commit messages: `Add GP contact export`, `Fix follow-up flag not saving`
- Never commit `crm.db`, `*.pyc`, `.env`, or any file listed in `.gitignore`

---

Last updated: 2026-02-23
