"""
ACRe CRM — one-shot setup script.
Run:  python setup_acre_crm.py
Creates an `acre-crm` folder on your Desktop with the full app inside.
"""
import os, sys, pathlib, textwrap

desktop = pathlib.Path.home() / "Desktop"
root = desktop / "acre-crm"

files = {}

files["requirements.txt"] = "flask>=3.0,<4.0\ngunicorn>=21.0,<22.0\n"

files["Procfile"] = "web: gunicorn app:app\n"

files[".gitignore"] = textwrap.dedent("""\
    *.db
    *.db-shm
    *.db-wal
    __pycache__/
    *.pyc
    .env
    .venv/
    venv/
    dist/
    *.egg-info/
""")

files["render.yaml"] = textwrap.dedent("""\
    services:
      - type: web
        name: acre-crm
        env: python
        buildCommand: pip install -r requirements.txt
        startCommand: gunicorn app:app
        envVars:
          - key: SECRET_KEY
            generateValue: true
          - key: DATABASE_PATH
            value: /opt/render/project/src/crm.db
""")

files["run.py"] = textwrap.dedent('''\
    """Local development runner — python run.py"""
    from app import app, init_db

    if __name__ == "__main__":
        init_db()
        app.run(debug=True, port=5000)
''')

files["app.py"] = textwrap.dedent('''\
    import os
    import sqlite3
    from flask import Flask, render_template, request, redirect, url_for, flash

    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

    DATABASE = os.environ.get("DATABASE_PATH", "crm.db")


    def get_db():
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn


    def init_db():
        conn = get_db()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                asset_type TEXT,
                location TEXT,
                target_raise TEXT,
                status TEXT DEFAULT \'Active\',
                notes TEXT,
                created_at TEXT DEFAULT (datetime(\'now\'))
            );
            CREATE TABLE IF NOT EXISTS outreach (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id INTEGER NOT NULL,
                contact_name TEXT NOT NULL,
                company TEXT,
                email TEXT,
                sent_by TEXT,
                outreach_date TEXT,
                outreach_summary TEXT,
                response_date TEXT,
                response_summary TEXT,
                follow_up_needed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime(\'now\')),
                FOREIGN KEY (deal_id) REFERENCES deals(id)
            );
            CREATE TABLE IF NOT EXISTS gp_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                title TEXT,
                company TEXT,
                email TEXT,
                phone TEXT,
                location TEXT,
                aum_range TEXT,
                strategy TEXT,
                min_check TEXT,
                max_check TEXT,
                source TEXT,
                status TEXT DEFAULT \'New\',
                notes TEXT,
                last_contacted TEXT,
                created_at TEXT DEFAULT (datetime(\'now\'))
            );
        """)
        conn.commit()
        conn.close()


    @app.route("/")
    def index():
        conn = get_db()
        deals = conn.execute(
            "SELECT d.*, COUNT(o.id) as outreach_count "
            "FROM deals d LEFT JOIN outreach o ON d.id = o.deal_id "
            "GROUP BY d.id ORDER BY d.created_at DESC"
        ).fetchall()
        gp_count = conn.execute("SELECT COUNT(*) FROM gp_contacts").fetchone()[0]
        pending_followups = conn.execute(
            "SELECT COUNT(*) FROM outreach WHERE follow_up_needed = 1"
        ).fetchone()[0]
        conn.close()
        return render_template("index.html", deals=deals, gp_count=gp_count,
                               pending_followups=pending_followups)


    @app.route("/deals")
    def deals():
        conn = get_db()
        rows = conn.execute(
            "SELECT d.*, COUNT(o.id) as outreach_count "
            "FROM deals d LEFT JOIN outreach o ON d.id = o.deal_id "
            "GROUP BY d.id ORDER BY d.created_at DESC"
        ).fetchall()
        conn.close()
        return render_template("deals.html", deals=rows)


    @app.route("/deals/new", methods=["GET", "POST"])
    def new_deal():
        if request.method == "POST":
            conn = get_db()
            conn.execute(
                "INSERT INTO deals (name, asset_type, location, target_raise, status, notes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (request.form["name"], request.form.get("asset_type",""),
                 request.form.get("location",""), request.form.get("target_raise",""),
                 request.form.get("status","Active"), request.form.get("notes","")),
            )
            conn.commit(); conn.close()
            flash("Deal created.", "success")
            return redirect(url_for("deals"))
        return render_template("deal_form.html", deal=None, title="New Deal")


    @app.route("/deals/<int:deal_id>")
    def deal_detail(deal_id):
        conn = get_db()
        deal = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
        if not deal:
            conn.close(); flash("Deal not found.", "danger")
            return redirect(url_for("deals"))
        outreaches = conn.execute(
            "SELECT * FROM outreach WHERE deal_id = ? ORDER BY outreach_date DESC, created_at DESC",
            (deal_id,)).fetchall()
        conn.close()
        return render_template("deal_detail.html", deal=deal, outreaches=outreaches)


    @app.route("/deals/<int:deal_id>/edit", methods=["GET", "POST"])
    def edit_deal(deal_id):
        conn = get_db()
        deal = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
        if not deal:
            conn.close(); flash("Deal not found.", "danger")
            return redirect(url_for("deals"))
        if request.method == "POST":
            conn.execute(
                "UPDATE deals SET name=?, asset_type=?, location=?, target_raise=?, status=?, notes=? WHERE id=?",
                (request.form["name"], request.form.get("asset_type",""),
                 request.form.get("location",""), request.form.get("target_raise",""),
                 request.form.get("status","Active"), request.form.get("notes",""), deal_id),
            )
            conn.commit(); conn.close()
            flash("Deal updated.", "success")
            return redirect(url_for("deal_detail", deal_id=deal_id))
        conn.close()
        return render_template("deal_form.html", deal=deal, title="Edit Deal")


    @app.route("/deals/<int:deal_id>/delete", methods=["POST"])
    def delete_deal(deal_id):
        conn = get_db()
        conn.execute("DELETE FROM outreach WHERE deal_id = ?", (deal_id,))
        conn.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
        conn.commit(); conn.close()
        flash("Deal deleted.", "info")
        return redirect(url_for("deals"))


    @app.route("/deals/<int:deal_id>/outreach/new", methods=["GET", "POST"])
    def new_outreach(deal_id):
        conn = get_db()
        deal = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
        if not deal:
            conn.close(); flash("Deal not found.", "danger")
            return redirect(url_for("deals"))
        if request.method == "POST":
            conn.execute(
                "INSERT INTO outreach (deal_id, contact_name, company, email, sent_by, "
                "outreach_date, outreach_summary, response_date, response_summary, follow_up_needed) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (deal_id, request.form["contact_name"], request.form.get("company",""),
                 request.form.get("email",""), request.form.get("sent_by",""),
                 request.form.get("outreach_date") or None, request.form.get("outreach_summary",""),
                 request.form.get("response_date") or None, request.form.get("response_summary",""),
                 1 if request.form.get("follow_up_needed") else 0),
            )
            conn.commit(); conn.close()
            flash("Outreach logged.", "success")
            return redirect(url_for("deal_detail", deal_id=deal_id))
        conn.close()
        return render_template("outreach_form.html", deal=deal, outreach=None, title="Log Outreach")


    @app.route("/deals/<int:deal_id>/outreach/<int:outreach_id>/edit", methods=["GET", "POST"])
    def edit_outreach(deal_id, outreach_id):
        conn = get_db()
        deal = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
        outreach = conn.execute("SELECT * FROM outreach WHERE id = ? AND deal_id = ?",
                                (outreach_id, deal_id)).fetchone()
        if not deal or not outreach:
            conn.close(); flash("Not found.", "danger")
            return redirect(url_for("deals"))
        if request.method == "POST":
            conn.execute(
                "UPDATE outreach SET contact_name=?, company=?, email=?, sent_by=?, "
                "outreach_date=?, outreach_summary=?, response_date=?, response_summary=?, "
                "follow_up_needed=? WHERE id=?",
                (request.form["contact_name"], request.form.get("company",""),
                 request.form.get("email",""), request.form.get("sent_by",""),
                 request.form.get("outreach_date") or None, request.form.get("outreach_summary",""),
                 request.form.get("response_date") or None, request.form.get("response_summary",""),
                 1 if request.form.get("follow_up_needed") else 0, outreach_id),
            )
            conn.commit(); conn.close()
            flash("Outreach updated.", "success")
            return redirect(url_for("deal_detail", deal_id=deal_id))
        conn.close()
        return render_template("outreach_form.html", deal=deal, outreach=outreach, title="Edit Outreach")


    @app.route("/deals/<int:deal_id>/outreach/<int:outreach_id>/delete", methods=["POST"])
    def delete_outreach(deal_id, outreach_id):
        conn = get_db()
        conn.execute("DELETE FROM outreach WHERE id = ? AND deal_id = ?", (outreach_id, deal_id))
        conn.commit(); conn.close()
        flash("Outreach entry deleted.", "info")
        return redirect(url_for("deal_detail", deal_id=deal_id))


    @app.route("/contacts")
    def contacts():
        q = request.args.get("q", "").strip()
        status_filter = request.args.get("status", "")
        conn = get_db()
        sql = "SELECT * FROM gp_contacts WHERE 1=1"
        params = []
        if q:
            sql += " AND (name LIKE ? OR company LIKE ? OR strategy LIKE ? OR location LIKE ?)"
            params += [f"%{q}%"] * 4
        if status_filter:
            sql += " AND status = ?"
            params.append(status_filter)
        sql += " ORDER BY created_at DESC"
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return render_template("contacts.html", contacts=rows, q=q, status_filter=status_filter)


    @app.route("/contacts/new", methods=["GET", "POST"])
    def new_contact():
        if request.method == "POST":
            conn = get_db()
            conn.execute(
                "INSERT INTO gp_contacts (name, title, company, email, phone, location, "
                "aum_range, strategy, min_check, max_check, source, status, notes, last_contacted) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (request.form["name"], request.form.get("title",""), request.form.get("company",""),
                 request.form.get("email",""), request.form.get("phone",""), request.form.get("location",""),
                 request.form.get("aum_range",""), request.form.get("strategy",""),
                 request.form.get("min_check",""), request.form.get("max_check",""),
                 request.form.get("source",""), request.form.get("status","New"),
                 request.form.get("notes",""), request.form.get("last_contacted") or None),
            )
            conn.commit(); conn.close()
            flash("GP contact added.", "success")
            return redirect(url_for("contacts"))
        return render_template("contact_form.html", contact=None, title="Add GP Contact")


    @app.route("/contacts/<int:contact_id>")
    def contact_detail(contact_id):
        conn = get_db()
        contact = conn.execute("SELECT * FROM gp_contacts WHERE id = ?", (contact_id,)).fetchone()
        conn.close()
        if not contact:
            flash("Contact not found.", "danger")
            return redirect(url_for("contacts"))
        return render_template("contact_detail.html", contact=contact)


    @app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
    def edit_contact(contact_id):
        conn = get_db()
        contact = conn.execute("SELECT * FROM gp_contacts WHERE id = ?", (contact_id,)).fetchone()
        if not contact:
            conn.close(); flash("Contact not found.", "danger")
            return redirect(url_for("contacts"))
        if request.method == "POST":
            conn.execute(
                "UPDATE gp_contacts SET name=?, title=?, company=?, email=?, phone=?, location=?, "
                "aum_range=?, strategy=?, min_check=?, max_check=?, source=?, status=?, notes=?, "
                "last_contacted=? WHERE id=?",
                (request.form["name"], request.form.get("title",""), request.form.get("company",""),
                 request.form.get("email",""), request.form.get("phone",""), request.form.get("location",""),
                 request.form.get("aum_range",""), request.form.get("strategy",""),
                 request.form.get("min_check",""), request.form.get("max_check",""),
                 request.form.get("source",""), request.form.get("status","New"),
                 request.form.get("notes",""), request.form.get("last_contacted") or None, contact_id),
            )
            conn.commit(); conn.close()
            flash("Contact updated.", "success")
            return redirect(url_for("contact_detail", contact_id=contact_id))
        conn.close()
        return render_template("contact_form.html", contact=contact, title="Edit GP Contact")


    @app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
    def delete_contact(contact_id):
        conn = get_db()
        conn.execute("DELETE FROM gp_contacts WHERE id = ?", (contact_id,))
        conn.commit(); conn.close()
        flash("Contact deleted.", "info")
        return redirect(url_for("contacts"))


    with app.app_context():
        init_db()

    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
''')

files["static/style.css"] = textwrap.dedent("""\
    body {
      background-color: #f5f6fa;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .navbar-brand { font-size: 1.2rem; letter-spacing: 0.5px; }
    .stat-card .card-body { padding: 1.25rem; }
    .stat-icon { font-size: 1.5rem; margin-bottom: 0.4rem; }
    .stat-value { font-size: 2rem; font-weight: 700; line-height: 1; margin-bottom: 0.2rem; }
    .stat-label { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; color: #6c757d; }
    .text-truncate-cell {
      display: inline-block; max-width: 200px; white-space: nowrap;
      overflow: hidden; text-overflow: ellipsis; vertical-align: middle; cursor: default;
    }
    .card-header { border-bottom: 1px solid rgba(0,0,0,.08); }
    .form-control:focus, .form-select:focus {
      border-color: #0d6efd;
      box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.15);
    }
    .table td, .table th { vertical-align: middle; font-size: 0.9rem; }
    .alert { border-radius: 8px; }
""")

files["templates/base.html"] = textwrap.dedent("""\
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>{% block title %}ACRe CRM{% endblock %}</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" />
      <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet" />
      <link href="{{ url_for('static', filename='style.css') }}" rel="stylesheet" />
    </head>
    <body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
      <div class="container-fluid">
        <a class="navbar-brand fw-bold" href="{{ url_for('index') }}">
          <span class="text-warning">ACRe</span> CRM
        </a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav ms-auto">
            <li class="nav-item">
              <a class="nav-link {% if request.endpoint == 'index' %}active{% endif %}" href="{{ url_for('index') }}">
                <i class="bi bi-speedometer2"></i> Dashboard
              </a>
            </li>
            <li class="nav-item">
              <a class="nav-link {% if 'deal' in (request.endpoint or '') %}active{% endif %}" href="{{ url_for('deals') }}">
                <i class="bi bi-building"></i> Deals
              </a>
            </li>
            <li class="nav-item">
              <a class="nav-link {% if 'contact' in (request.endpoint or '') %}active{% endif %}" href="{{ url_for('contacts') }}">
                <i class="bi bi-people"></i> GP Contacts
              </a>
            </li>
          </ul>
        </div>
      </div>
    </nav>
    <div class="container-fluid py-4 px-4">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
          </div>
        {% endfor %}
      {% endwith %}
      {% block content %}{% endblock %}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
""")

files["templates/index.html"] = textwrap.dedent("""\
    {% extends "base.html" %}
    {% block title %}Dashboard — ACRe CRM{% endblock %}
    {% block content %}
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2 class="fw-bold mb-0">Dashboard</h2>
      <span class="text-muted small">ACRe Solutions Capital Markets</span>
    </div>
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-3">
        <div class="card stat-card border-0 shadow-sm h-100"><div class="card-body">
          <div class="stat-icon text-primary"><i class="bi bi-building"></i></div>
          <div class="stat-value">{{ deals|length }}</div>
          <div class="stat-label">Active Deals</div>
        </div></div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card stat-card border-0 shadow-sm h-100"><div class="card-body">
          <div class="stat-icon text-success"><i class="bi bi-send"></i></div>
          <div class="stat-value">{{ deals|sum(attribute='outreach_count') }}</div>
          <div class="stat-label">Total Outreaches</div>
        </div></div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card stat-card border-0 shadow-sm h-100"><div class="card-body">
          <div class="stat-icon text-warning"><i class="bi bi-exclamation-circle"></i></div>
          <div class="stat-value">{{ pending_followups }}</div>
          <div class="stat-label">Follow-ups Needed</div>
        </div></div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card stat-card border-0 shadow-sm h-100"><div class="card-body">
          <div class="stat-icon text-info"><i class="bi bi-people"></i></div>
          <div class="stat-value">{{ gp_count }}</div>
          <div class="stat-label">GP Contacts</div>
        </div></div>
      </div>
    </div>
    <div class="card border-0 shadow-sm mb-4">
      <div class="card-header bg-white d-flex justify-content-between align-items-center py-3">
        <h5 class="mb-0 fw-semibold">Active Deals</h5>
        <a href="{{ url_for('new_deal') }}" class="btn btn-sm btn-primary"><i class="bi bi-plus-lg"></i> New Deal</a>
      </div>
      <div class="card-body p-0">
        {% if deals %}
        <div class="table-responsive">
          <table class="table table-hover mb-0">
            <thead class="table-light"><tr>
              <th>Deal</th><th>Type</th><th>Location</th><th>Target Raise</th><th>Status</th><th class="text-center">Outreaches</th><th></th>
            </tr></thead>
            <tbody>
              {% for d in deals %}
              <tr>
                <td class="fw-semibold"><a href="{{ url_for('deal_detail', deal_id=d.id) }}" class="text-decoration-none">{{ d.name }}</a></td>
                <td><span class="badge bg-secondary-subtle text-secondary-emphasis">{{ d.asset_type or '\\u2014' }}</span></td>
                <td class="text-muted">{{ d.location or '\\u2014' }}</td>
                <td>{{ d.target_raise or '\\u2014' }}</td>
                <td><span class="badge {% if d.status == 'Active' %}bg-success{% elif d.status == 'Closed' %}bg-secondary{% else %}bg-warning text-dark{% endif %}">{{ d.status }}</span></td>
                <td class="text-center">{{ d.outreach_count }}</td>
                <td><a href="{{ url_for('deal_detail', deal_id=d.id) }}" class="btn btn-sm btn-outline-secondary">View</a></td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        {% else %}
        <div class="text-center py-5 text-muted">
          <i class="bi bi-building fs-1 d-block mb-2"></i>
          No deals yet. <a href="{{ url_for('new_deal') }}">Add your first deal.</a>
        </div>
        {% endif %}
      </div>
    </div>
    {% endblock %}
""")

files["templates/deals.html"] = textwrap.dedent("""\
    {% extends "base.html" %}
    {% block title %}Deals — ACRe CRM{% endblock %}
    {% block content %}
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2 class="fw-bold mb-0">Deals</h2>
      <a href="{{ url_for('new_deal') }}" class="btn btn-primary"><i class="bi bi-plus-lg"></i> New Deal</a>
    </div>
    <div class="card border-0 shadow-sm">
      <div class="card-body p-0">
        {% if deals %}
        <div class="table-responsive">
          <table class="table table-hover mb-0">
            <thead class="table-light"><tr>
              <th>Deal Name</th><th>Asset Type</th><th>Location</th><th>Target Raise</th><th>Status</th><th class="text-center">Outreaches</th><th>Added</th><th></th>
            </tr></thead>
            <tbody>
              {% for d in deals %}
              <tr>
                <td class="fw-semibold"><a href="{{ url_for('deal_detail', deal_id=d.id) }}" class="text-decoration-none">{{ d.name }}</a></td>
                <td>{{ d.asset_type or '\\u2014' }}</td>
                <td>{{ d.location or '\\u2014' }}</td>
                <td>{{ d.target_raise or '\\u2014' }}</td>
                <td><span class="badge {% if d.status == 'Active' %}bg-success{% elif d.status == 'Closed' %}bg-secondary{% else %}bg-warning text-dark{% endif %}">{{ d.status }}</span></td>
                <td class="text-center">{{ d.outreach_count }}</td>
                <td class="text-muted small">{{ d.created_at[:10] if d.created_at else '\\u2014' }}</td>
                <td><div class="d-flex gap-1">
                  <a href="{{ url_for('deal_detail', deal_id=d.id) }}" class="btn btn-sm btn-outline-secondary">View</a>
                  <a href="{{ url_for('edit_deal', deal_id=d.id) }}" class="btn btn-sm btn-outline-primary">Edit</a>
                </div></td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        {% else %}
        <div class="text-center py-5 text-muted">
          <i class="bi bi-building fs-1 d-block mb-2"></i>
          No deals yet. <a href="{{ url_for('new_deal') }}">Create your first deal.</a>
        </div>
        {% endif %}
      </div>
    </div>
    {% endblock %}
""")

files["templates/deal_form.html"] = textwrap.dedent("""\
    {% extends "base.html" %}
    {% block title %}{{ title }} — ACRe CRM{% endblock %}
    {% block content %}
    <div class="d-flex align-items-center gap-2 mb-4">
      <a href="{{ url_for('deals') }}" class="btn btn-sm btn-outline-secondary"><i class="bi bi-arrow-left"></i></a>
      <h2 class="fw-bold mb-0">{{ title }}</h2>
    </div>
    <div class="card border-0 shadow-sm" style="max-width:640px;">
      <div class="card-body p-4">
        <form method="POST">
          <div class="mb-3">
            <label class="form-label fw-semibold">Deal Name <span class="text-danger">*</span></label>
            <input type="text" name="name" class="form-control" required value="{{ deal.name if deal else '' }}" placeholder="e.g. Parkview Multifamily Portfolio" />
          </div>
          <div class="row g-3 mb-3">
            <div class="col-sm-6">
              <label class="form-label fw-semibold">Asset Type</label>
              <input type="text" name="asset_type" class="form-control" value="{{ deal.asset_type if deal else '' }}" placeholder="e.g. Multifamily, Office" />
            </div>
            <div class="col-sm-6">
              <label class="form-label fw-semibold">Location</label>
              <input type="text" name="location" class="form-control" value="{{ deal.location if deal else '' }}" placeholder="e.g. Atlanta, GA" />
            </div>
          </div>
          <div class="row g-3 mb-3">
            <div class="col-sm-6">
              <label class="form-label fw-semibold">Target Raise</label>
              <input type="text" name="target_raise" class="form-control" value="{{ deal.target_raise if deal else '' }}" placeholder="e.g. $25M" />
            </div>
            <div class="col-sm-6">
              <label class="form-label fw-semibold">Status</label>
              <select name="status" class="form-select">
                {% for s in ['Active', 'On Hold', 'Closed', 'Dead'] %}
                <option value="{{ s }}" {% if deal and deal.status == s %}selected{% elif not deal and s == 'Active' %}selected{% endif %}>{{ s }}</option>
                {% endfor %}
              </select>
            </div>
          </div>
          <div class="mb-4">
            <label class="form-label fw-semibold">Notes</label>
            <textarea name="notes" class="form-control" rows="3" placeholder="Deal summary, key terms, strategy...">{{ deal.notes if deal else '' }}</textarea>
          </div>
          <div class="d-flex gap-2">
            <button type="submit" class="btn btn-primary">Save Deal</button>
            <a href="{{ url_for('deals') }}" class="btn btn-outline-secondary">Cancel</a>
            {% if deal %}
            <form method="POST" action="{{ url_for('delete_deal', deal_id=deal.id) }}" class="ms-auto" onsubmit="return confirm('Delete this deal and all its outreach logs?')">
              <button type="submit" class="btn btn-outline-danger">Delete Deal</button>
            </form>
            {% endif %}
          </div>
        </form>
      </div>
    </div>
    {% endblock %}
""")

files["templates/deal_detail.html"] = textwrap.dedent("""\
    {% extends "base.html" %}
    {% block title %}{{ deal.name }} — ACRe CRM{% endblock %}
    {% block content %}
    <div class="d-flex align-items-start justify-content-between mb-4 flex-wrap gap-2">
      <div class="d-flex align-items-center gap-2">
        <a href="{{ url_for('deals') }}" class="btn btn-sm btn-outline-secondary"><i class="bi bi-arrow-left"></i></a>
        <div>
          <h2 class="fw-bold mb-0">{{ deal.name }}</h2>
          <span class="text-muted small">
            {{ deal.asset_type or '' }}{% if deal.asset_type and deal.location %} &middot; {% endif %}{{ deal.location or '' }}{% if deal.target_raise %} &middot; {{ deal.target_raise }}{% endif %}
          </span>
        </div>
      </div>
      <div class="d-flex gap-2 align-items-center">
        <span class="badge fs-6 {% if deal.status == 'Active' %}bg-success{% elif deal.status == 'Closed' %}bg-secondary{% else %}bg-warning text-dark{% endif %}">{{ deal.status }}</span>
        <a href="{{ url_for('edit_deal', deal_id=deal.id) }}" class="btn btn-sm btn-outline-primary">Edit Deal</a>
      </div>
    </div>
    {% if deal.notes %}<div class="alert alert-light border mb-4"><strong>Notes:</strong> {{ deal.notes }}</div>{% endif %}
    <div class="card border-0 shadow-sm">
      <div class="card-header bg-white d-flex justify-content-between align-items-center py-3">
        <h5 class="mb-0 fw-semibold"><i class="bi bi-send"></i> Outreach Log</h5>
        <a href="{{ url_for('new_outreach', deal_id=deal.id) }}" class="btn btn-sm btn-primary"><i class="bi bi-plus-lg"></i> Log Outreach</a>
      </div>
      <div class="card-body p-0">
        {% if outreaches %}
        <div class="table-responsive">
          <table class="table table-hover mb-0 align-middle">
            <thead class="table-light"><tr>
              <th>Contact</th><th>Company</th><th>Sent By</th><th>Outreach Date</th><th>Our Message</th><th>Response Date</th><th>Their Reply</th><th>Follow-up</th><th></th>
            </tr></thead>
            <tbody>
              {% for o in outreaches %}
              <tr {% if o.follow_up_needed %}class="table-warning"{% endif %}>
                <td><div class="fw-semibold">{{ o.contact_name }}</div>{% if o.email %}<div class="text-muted small">{{ o.email }}</div>{% endif %}</td>
                <td>{{ o.company or '\\u2014' }}</td>
                <td>{% if o.sent_by %}<span class="badge bg-primary-subtle text-primary-emphasis">{{ o.sent_by }}</span>{% else %}\\u2014{% endif %}</td>
                <td class="text-nowrap">{{ o.outreach_date or '\\u2014' }}</td>
                <td><span class="text-truncate-cell" title="{{ o.outreach_summary }}">{{ o.outreach_summary or '\\u2014' }}</span></td>
                <td class="text-nowrap">{{ o.response_date or '\\u2014' }}</td>
                <td><span class="text-truncate-cell" title="{{ o.response_summary }}">{{ o.response_summary or '' }}</span></td>
                <td class="text-center">{% if o.follow_up_needed %}<span class="badge bg-warning text-dark"><i class="bi bi-exclamation-circle"></i> Yes</span>{% else %}<span class="text-muted">\\u2014</span>{% endif %}</td>
                <td><div class="d-flex gap-1">
                  <a href="{{ url_for('edit_outreach', deal_id=deal.id, outreach_id=o.id) }}" class="btn btn-sm btn-outline-secondary">Edit</a>
                  <form method="POST" action="{{ url_for('delete_outreach', deal_id=deal.id, outreach_id=o.id) }}" onsubmit="return confirm('Delete this outreach entry?')">
                    <button class="btn btn-sm btn-outline-danger">Del</button>
                  </form>
                </div></td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        {% else %}
        <div class="text-center py-5 text-muted">
          <i class="bi bi-send fs-1 d-block mb-2"></i>
          No outreach logged yet. <a href="{{ url_for('new_outreach', deal_id=deal.id) }}">Log your first outreach.</a>
        </div>
        {% endif %}
      </div>
    </div>
    {% endblock %}
""")

files["templates/outreach_form.html"] = textwrap.dedent("""\
    {% extends "base.html" %}
    {% block title %}{{ title }} — ACRe CRM{% endblock %}
    {% block content %}
    <div class="d-flex align-items-center gap-2 mb-4">
      <a href="{{ url_for('deal_detail', deal_id=deal.id) }}" class="btn btn-sm btn-outline-secondary"><i class="bi bi-arrow-left"></i></a>
      <div><h2 class="fw-bold mb-0">{{ title }}</h2><span class="text-muted small">Deal: {{ deal.name }}</span></div>
    </div>
    <div class="card border-0 shadow-sm" style="max-width:720px;">
      <div class="card-body p-4">
        <form method="POST">
          <h6 class="text-uppercase text-muted fw-semibold mb-3 small">Contact Info</h6>
          <div class="row g-3 mb-3">
            <div class="col-sm-6">
              <label class="form-label fw-semibold">Contact Name <span class="text-danger">*</span></label>
              <input type="text" name="contact_name" class="form-control" required value="{{ outreach.contact_name if outreach else '' }}" placeholder="Jane Smith" />
            </div>
            <div class="col-sm-6">
              <label class="form-label fw-semibold">Company</label>
              <input type="text" name="company" class="form-control" value="{{ outreach.company if outreach else '' }}" placeholder="Blackstone Real Estate" />
            </div>
            <div class="col-sm-6">
              <label class="form-label fw-semibold">Email</label>
              <input type="email" name="email" class="form-control" value="{{ outreach.email if outreach else '' }}" placeholder="jane@firm.com" />
            </div>
            <div class="col-sm-6">
              <label class="form-label fw-semibold">Sent By</label>
              <input type="text" name="sent_by" class="form-control" value="{{ outreach.sent_by if outreach else '' }}" placeholder="Your name or coworker's name" />
            </div>
          </div>
          <hr class="my-3" />
          <h6 class="text-uppercase text-muted fw-semibold mb-3 small">Our Outreach</h6>
          <div class="row g-3 mb-3">
            <div class="col-sm-4">
              <label class="form-label fw-semibold">Outreach Date</label>
              <input type="date" name="outreach_date" class="form-control" value="{{ outreach.outreach_date if outreach else '' }}" />
            </div>
            <div class="col-12">
              <label class="form-label fw-semibold">What We Sent / Said</label>
              <textarea name="outreach_summary" class="form-control" rows="3" placeholder="Brief summary of the email or call...">{{ outreach.outreach_summary if outreach else '' }}</textarea>
            </div>
          </div>
          <hr class="my-3" />
          <h6 class="text-uppercase text-muted fw-semibold mb-3 small">Their Response</h6>
          <div class="row g-3 mb-3">
            <div class="col-sm-4">
              <label class="form-label fw-semibold">Response Date</label>
              <input type="date" name="response_date" class="form-control" value="{{ outreach.response_date if outreach else '' }}" />
            </div>
            <div class="col-12">
              <label class="form-label fw-semibold">Their Reply / Outcome</label>
              <textarea name="response_summary" class="form-control" rows="3" placeholder="What they said — interested, passed, need more info, etc.">{{ outreach.response_summary if outreach else '' }}</textarea>
            </div>
          </div>
          <div class="form-check mb-4">
            <input class="form-check-input" type="checkbox" name="follow_up_needed" id="followup" {% if outreach and outreach.follow_up_needed %}checked{% endif %} />
            <label class="form-check-label fw-semibold" for="followup">Follow-up needed</label>
            <div class="form-text">Check this to flag this contact for a follow-up.</div>
          </div>
          <div class="d-flex gap-2">
            <button type="submit" class="btn btn-primary">Save</button>
            <a href="{{ url_for('deal_detail', deal_id=deal.id) }}" class="btn btn-outline-secondary">Cancel</a>
          </div>
        </form>
      </div>
    </div>
    {% endblock %}
""")

files["templates/contacts.html"] = textwrap.dedent("""\
    {% extends "base.html" %}
    {% block title %}GP Contacts — ACRe CRM{% endblock %}
    {% block content %}
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2 class="fw-bold mb-0">GP Contacts</h2>
      <a href="{{ url_for('new_contact') }}" class="btn btn-primary"><i class="bi bi-plus-lg"></i> Add GP Contact</a>
    </div>
    <form method="GET" class="d-flex gap-2 mb-4 flex-wrap">
      <input type="text" name="q" class="form-control" style="max-width:320px;" placeholder="Search name, firm, strategy, location\\u2026" value="{{ q }}" />
      <select name="status" class="form-select" style="max-width:180px;">
        <option value="">All Statuses</option>
        {% for s in ['New', 'In Contact', 'Meeting Scheduled', 'Passed', 'Hot Lead'] %}
        <option value="{{ s }}" {% if status_filter == s %}selected{% endif %}>{{ s }}</option>
        {% endfor %}
      </select>
      <button type="submit" class="btn btn-outline-secondary">Filter</button>
      {% if q or status_filter %}<a href="{{ url_for('contacts') }}" class="btn btn-outline-danger">Clear</a>{% endif %}
    </form>
    <div class="card border-0 shadow-sm">
      <div class="card-body p-0">
        {% if contacts %}
        <div class="table-responsive">
          <table class="table table-hover mb-0 align-middle">
            <thead class="table-light"><tr>
              <th>Name / Title</th><th>Firm</th><th>Strategy</th><th>AUM Range</th><th>Location</th><th>Status</th><th>Last Contacted</th><th>Source</th><th></th>
            </tr></thead>
            <tbody>
              {% for c in contacts %}
              <tr>
                <td><a href="{{ url_for('contact_detail', contact_id=c.id) }}" class="text-decoration-none fw-semibold">{{ c.name }}</a>{% if c.title %}<div class="text-muted small">{{ c.title }}</div>{% endif %}</td>
                <td>{{ c.company or '\\u2014' }}</td>
                <td>{{ c.strategy or '\\u2014' }}</td>
                <td>{{ c.aum_range or '\\u2014' }}</td>
                <td>{{ c.location or '\\u2014' }}</td>
                <td><span class="badge {% if c.status == 'Hot Lead' %}bg-danger{% elif c.status == 'In Contact' %}bg-primary{% elif c.status == 'Meeting Scheduled' %}bg-success{% elif c.status == 'Passed' %}bg-secondary{% else %}bg-light text-dark border{% endif %}">{{ c.status }}</span></td>
                <td class="text-muted small text-nowrap">{{ c.last_contacted or '\\u2014' }}</td>
                <td class="text-muted small">{{ c.source or '\\u2014' }}</td>
                <td><div class="d-flex gap-1">
                  <a href="{{ url_for('contact_detail', contact_id=c.id) }}" class="btn btn-sm btn-outline-secondary">View</a>
                  <a href="{{ url_for('edit_contact', contact_id=c.id) }}" class="btn btn-sm btn-outline-primary">Edit</a>
                </div></td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        <div class="px-3 py-2 text-muted small border-top">{{ contacts|length }} contact{{ 's' if contacts|length != 1 }}</div>
        {% else %}
        <div class="text-center py-5 text-muted">
          <i class="bi bi-people fs-1 d-block mb-2"></i>
          {% if q or status_filter %}No contacts match your search.{% else %}No GP contacts yet. <a href="{{ url_for('new_contact') }}">Add your first one.</a>{% endif %}
        </div>
        {% endif %}
      </div>
    </div>
    {% endblock %}
""")

files["templates/contact_form.html"] = textwrap.dedent("""\
    {% extends "base.html" %}
    {% block title %}{{ title }} — ACRe CRM{% endblock %}
    {% block content %}
    <div class="d-flex align-items-center gap-2 mb-4">
      <a href="{{ url_for('contacts') }}" class="btn btn-sm btn-outline-secondary"><i class="bi bi-arrow-left"></i></a>
      <h2 class="fw-bold mb-0">{{ title }}</h2>
    </div>
    <div class="card border-0 shadow-sm" style="max-width:720px;">
      <div class="card-body p-4">
        <form method="POST">
          <h6 class="text-uppercase text-muted fw-semibold mb-3 small">Person</h6>
          <div class="row g-3 mb-3">
            <div class="col-sm-6"><label class="form-label fw-semibold">Full Name <span class="text-danger">*</span></label><input type="text" name="name" class="form-control" required value="{{ contact.name if contact else '' }}" placeholder="John Doe" /></div>
            <div class="col-sm-6"><label class="form-label fw-semibold">Title</label><input type="text" name="title" class="form-control" value="{{ contact.title if contact else '' }}" placeholder="Managing Partner" /></div>
            <div class="col-sm-6"><label class="form-label fw-semibold">Email</label><input type="email" name="email" class="form-control" value="{{ contact.email if contact else '' }}" placeholder="john@firm.com" /></div>
            <div class="col-sm-6"><label class="form-label fw-semibold">Phone</label><input type="text" name="phone" class="form-control" value="{{ contact.phone if contact else '' }}" placeholder="(212) 555-0100" /></div>
          </div>
          <hr class="my-3" />
          <h6 class="text-uppercase text-muted fw-semibold mb-3 small">Firm</h6>
          <div class="row g-3 mb-3">
            <div class="col-sm-6"><label class="form-label fw-semibold">Company / Firm</label><input type="text" name="company" class="form-control" value="{{ contact.company if contact else '' }}" placeholder="Apex Capital Partners" /></div>
            <div class="col-sm-6"><label class="form-label fw-semibold">Location</label><input type="text" name="location" class="form-control" value="{{ contact.location if contact else '' }}" placeholder="Dallas, TX" /></div>
            <div class="col-sm-6"><label class="form-label fw-semibold">AUM Range</label><input type="text" name="aum_range" class="form-control" value="{{ contact.aum_range if contact else '' }}" placeholder="$100M\\u2013$500M" /></div>
            <div class="col-sm-6"><label class="form-label fw-semibold">Strategy / Asset Focus</label><input type="text" name="strategy" class="form-control" value="{{ contact.strategy if contact else '' }}" placeholder="Value-add multifamily, Sun Belt" /></div>
            <div class="col-sm-6"><label class="form-label fw-semibold">Min Check Size</label><input type="text" name="min_check" class="form-control" value="{{ contact.min_check if contact else '' }}" placeholder="$5M" /></div>
            <div class="col-sm-6"><label class="form-label fw-semibold">Max Check Size</label><input type="text" name="max_check" class="form-control" value="{{ contact.max_check if contact else '' }}" placeholder="$25M" /></div>
          </div>
          <hr class="my-3" />
          <h6 class="text-uppercase text-muted fw-semibold mb-3 small">Relationship</h6>
          <div class="row g-3 mb-3">
            <div class="col-sm-4"><label class="form-label fw-semibold">Status</label><select name="status" class="form-select">{% for s in ['New', 'In Contact', 'Meeting Scheduled', 'Hot Lead', 'Passed'] %}<option value="{{ s }}" {% if contact and contact.status == s %}selected{% elif not contact and s == 'New' %}selected{% endif %}>{{ s }}</option>{% endfor %}</select></div>
            <div class="col-sm-4"><label class="form-label fw-semibold">Last Contacted</label><input type="date" name="last_contacted" class="form-control" value="{{ contact.last_contacted if contact else '' }}" /></div>
            <div class="col-sm-4"><label class="form-label fw-semibold">Source</label><input type="text" name="source" class="form-control" value="{{ contact.source if contact else '' }}" placeholder="LinkedIn, referral, conf\\u2026" /></div>
            <div class="col-12"><label class="form-label fw-semibold">Notes</label><textarea name="notes" class="form-control" rows="3" placeholder="Relationship notes, deal fit, who referred them\\u2026">{{ contact.notes if contact else '' }}</textarea></div>
          </div>
          <div class="d-flex gap-2 mt-2">
            <button type="submit" class="btn btn-primary">Save Contact</button>
            <a href="{{ url_for('contacts') }}" class="btn btn-outline-secondary">Cancel</a>
            {% if contact %}
            <form method="POST" action="{{ url_for('delete_contact', contact_id=contact.id) }}" class="ms-auto" onsubmit="return confirm('Delete this contact?')">
              <button type="submit" class="btn btn-outline-danger">Delete</button>
            </form>
            {% endif %}
          </div>
        </form>
      </div>
    </div>
    {% endblock %}
""")

files["templates/contact_detail.html"] = textwrap.dedent("""\
    {% extends "base.html" %}
    {% block title %}{{ contact.name }} — ACRe CRM{% endblock %}
    {% block content %}
    <div class="d-flex align-items-start justify-content-between mb-4 flex-wrap gap-2">
      <div class="d-flex align-items-center gap-2">
        <a href="{{ url_for('contacts') }}" class="btn btn-sm btn-outline-secondary"><i class="bi bi-arrow-left"></i></a>
        <div>
          <h2 class="fw-bold mb-0">{{ contact.name }}</h2>
          {% if contact.title %}<div class="text-muted">{{ contact.title }}{% if contact.company %} at {{ contact.company }}{% endif %}</div>{% endif %}
        </div>
      </div>
      <a href="{{ url_for('edit_contact', contact_id=contact.id) }}" class="btn btn-sm btn-outline-primary">Edit</a>
    </div>
    <div class="row g-4">
      <div class="col-md-6">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-header bg-white fw-semibold py-3">Contact Details</div>
          <div class="card-body">
            <dl class="row mb-0">
              <dt class="col-5 text-muted">Email</dt><dd class="col-7">{% if contact.email %}<a href="mailto:{{ contact.email }}">{{ contact.email }}</a>{% else %}\\u2014{% endif %}</dd>
              <dt class="col-5 text-muted">Phone</dt><dd class="col-7">{{ contact.phone or '\\u2014' }}</dd>
              <dt class="col-5 text-muted">Company</dt><dd class="col-7">{{ contact.company or '\\u2014' }}</dd>
              <dt class="col-5 text-muted">Location</dt><dd class="col-7">{{ contact.location or '\\u2014' }}</dd>
              <dt class="col-5 text-muted">Status</dt><dd class="col-7"><span class="badge {% if contact.status == 'Hot Lead' %}bg-danger{% elif contact.status == 'In Contact' %}bg-primary{% elif contact.status == 'Meeting Scheduled' %}bg-success{% elif contact.status == 'Passed' %}bg-secondary{% else %}bg-light text-dark border{% endif %}">{{ contact.status }}</span></dd>
              <dt class="col-5 text-muted">Last Contacted</dt><dd class="col-7">{{ contact.last_contacted or '\\u2014' }}</dd>
              <dt class="col-5 text-muted">Source</dt><dd class="col-7">{{ contact.source or '\\u2014' }}</dd>
            </dl>
          </div>
        </div>
      </div>
      <div class="col-md-6">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-header bg-white fw-semibold py-3">Investment Profile</div>
          <div class="card-body">
            <dl class="row mb-0">
              <dt class="col-5 text-muted">Strategy</dt><dd class="col-7">{{ contact.strategy or '\\u2014' }}</dd>
              <dt class="col-5 text-muted">AUM Range</dt><dd class="col-7">{{ contact.aum_range or '\\u2014' }}</dd>
              <dt class="col-5 text-muted">Min Check Size</dt><dd class="col-7">{{ contact.min_check or '\\u2014' }}</dd>
              <dt class="col-5 text-muted">Max Check Size</dt><dd class="col-7">{{ contact.max_check or '\\u2014' }}</dd>
            </dl>
          </div>
        </div>
      </div>
      {% if contact.notes %}
      <div class="col-12"><div class="card border-0 shadow-sm"><div class="card-header bg-white fw-semibold py-3">Notes</div><div class="card-body">{{ contact.notes }}</div></div></div>
      {% endif %}
    </div>
    {% endblock %}
""")

# ── Write everything out ───────────────────────────────────────────────────────

print(f"\nCreating project at: {root}\n")
for rel_path, content in files.items():
    dest = root / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    print(f"  created  {rel_path}")

print(f"""
Done! Project created at:
  {root}

Next steps — run these commands one at a time:

  1. Open a Command Prompt IN that folder:
     - Open File Explorer, go to your Desktop, open the acre-crm folder
     - Click the address bar, type cmd, press Enter

  2. Then run:
       python -m venv venv
       venv\\Scripts\\activate
       pip install -r requirements.txt
       python run.py

  3. Open your browser and go to:
       http://localhost:5000
""")
