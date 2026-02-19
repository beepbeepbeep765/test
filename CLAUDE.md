# CLAUDE.md

This file provides context, conventions, and workflow guidance for AI assistants (e.g., Claude Code) working in this repository.

---

## Project: ACRe Solutions Capital Markets CRM

A lightweight internal web application for the ACRe Solutions capital markets team to:

1. **Track deal outreach** — log every contact made for each deal being marketed, including who sent it, date, message summary, response, and follow-up flags.
2. **Farm GP contacts** — maintain a searchable database of General Partners (GPs) to approach for future equity raises.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Web framework | Flask 3.x |
| Database | SQLite (file: `crm.db`) |
| Frontend | Bootstrap 5.3 + Bootstrap Icons (CDN) |
| Production server | Gunicorn |
| Hosting | Render (see `render.yaml`) |

---

## Project Structure

```
acre-crm/
├── app.py              # Flask app — all routes and DB logic
├── run.py              # Local dev runner (python run.py)
├── requirements.txt    # Python dependencies
├── Procfile            # Gunicorn start command for Render/Heroku
├── render.yaml         # Render deployment config
├── .gitignore
├── templates/
│   ├── base.html           # Navbar, flash messages, Bootstrap imports
│   ├── index.html          # Dashboard with stats + active deals table
│   ├── deals.html          # All deals list
│   ├── deal_form.html      # Create / edit a deal
│   ├── deal_detail.html    # Single deal view with full outreach log
│   ├── outreach_form.html  # Log / edit an outreach entry
│   ├── contacts.html       # GP contacts list with search + filter
│   ├── contact_form.html   # Add / edit a GP contact
│   └── contact_detail.html # Single GP contact view
└── static/
    └── style.css           # Custom styles (minimal, Bootstrap-first)
```

---

## Database Schema

Three tables, all in `crm.db` (SQLite). The DB is auto-created on first startup via `init_db()`.

### `deals`
Represents a CRE deal being marketed.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | Deal name (required) |
| asset_type | TEXT | e.g. Multifamily, Office |
| location | TEXT | e.g. Atlanta, GA |
| target_raise | TEXT | e.g. $25M |
| status | TEXT | Active / On Hold / Closed / Dead |
| notes | TEXT | Free-form deal summary |
| created_at | TEXT | ISO datetime |

### `outreach`
One row per outreach attempt, linked to a deal.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| deal_id | INTEGER FK | References deals.id |
| contact_name | TEXT | Required |
| company | TEXT | |
| email | TEXT | |
| sent_by | TEXT | Which team member sent it |
| outreach_date | TEXT | ISO date |
| outreach_summary | TEXT | What we sent / said |
| response_date | TEXT | ISO date |
| response_summary | TEXT | Their reply / outcome |
| follow_up_needed | INTEGER | 0 or 1 (boolean) |
| created_at | TEXT | |

### `gp_contacts`
GP farming database.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | Required |
| title | TEXT | e.g. Managing Partner |
| company | TEXT | Firm name |
| email | TEXT | |
| phone | TEXT | |
| location | TEXT | |
| aum_range | TEXT | e.g. $100M–$500M |
| strategy | TEXT | e.g. Value-add multifamily |
| min_check | TEXT | Min equity check |
| max_check | TEXT | Max equity check |
| source | TEXT | Where we found them |
| status | TEXT | New / In Contact / Meeting Scheduled / Hot Lead / Passed |
| notes | TEXT | Relationship / fit notes |
| last_contacted | TEXT | ISO date |
| created_at | TEXT | |

---

## Running Locally

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the dev server (creates crm.db automatically)
python run.py
```

Then open `http://localhost:5000` in your browser.

---

## Deploying to Render (free tier)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service → connect the repo
3. Render auto-detects `render.yaml` — just click **Create Web Service**
4. The `SECRET_KEY` env var is auto-generated; `DATABASE_PATH` points to a persistent disk path

> **Note on the database:** SQLite on Render's free tier is ephemeral unless you add a persistent disk. For a small internal tool with 1-2 users this is fine during development, but if you want data to survive redeploys, either upgrade to a paid Render plan with a disk, or migrate to Render's managed Postgres (requires changing the DB layer in `app.py`).

---

## Development Conventions

### Adding new fields
- Schema is defined in the `init_db()` function in `app.py` — modify the `CREATE TABLE IF NOT EXISTS` statements there.
- Since SQLite with `CREATE TABLE IF NOT EXISTS` doesn't auto-migrate, for adding columns to an existing database run `ALTER TABLE` manually or delete `crm.db` and let it recreate (dev only).

### Adding new routes
- All routes live in `app.py`. Follow the existing pattern: GET renders a template, POST processes the form and redirects.
- Use `flash()` for user feedback (success / danger / info).
- Always redirect after POST to prevent form resubmission on refresh.

### Templates
- All templates extend `base.html`.
- Use Bootstrap 5 utility classes first; add custom CSS to `static/style.css` only when Bootstrap doesn't cover it.
- Keep forms and tables consistent with existing patterns.

### Security
- Never put real credentials or `.env` files in the repo
- The `SECRET_KEY` must be set via environment variable in production (Render generates it automatically)
- `crm.db` is in `.gitignore` — never commit the database file

---

## Git Workflow

- `master` — primary branch
- `claude/<description>-<session-id>` — AI assistant working branches
- Write imperative commit messages: `Add GP contact export`, `Fix follow-up flag not saving`
- Never commit `crm.db`, `*.pyc`, or `.env`

---

Last updated: 2026-02-19
