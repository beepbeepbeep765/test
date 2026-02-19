import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

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
            status TEXT DEFAULT 'Active',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
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
            created_at TEXT DEFAULT (datetime('now')),
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
            status TEXT DEFAULT 'New',
            notes TEXT,
            last_contacted TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


# ── Dashboard ──────────────────────────────────────────────────────────────────

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


# ── Deals ──────────────────────────────────────────────────────────────────────

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
            (
                request.form["name"],
                request.form.get("asset_type", ""),
                request.form.get("location", ""),
                request.form.get("target_raise", ""),
                request.form.get("status", "Active"),
                request.form.get("notes", ""),
            ),
        )
        conn.commit()
        conn.close()
        flash("Deal created.", "success")
        return redirect(url_for("deals"))
    return render_template("deal_form.html", deal=None, title="New Deal")


@app.route("/deals/<int:deal_id>")
def deal_detail(deal_id):
    conn = get_db()
    deal = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
    if not deal:
        conn.close()
        flash("Deal not found.", "danger")
        return redirect(url_for("deals"))
    outreaches = conn.execute(
        "SELECT * FROM outreach WHERE deal_id = ? ORDER BY outreach_date DESC, created_at DESC",
        (deal_id,),
    ).fetchall()
    conn.close()
    return render_template("deal_detail.html", deal=deal, outreaches=outreaches)


@app.route("/deals/<int:deal_id>/edit", methods=["GET", "POST"])
def edit_deal(deal_id):
    conn = get_db()
    deal = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
    if not deal:
        conn.close()
        flash("Deal not found.", "danger")
        return redirect(url_for("deals"))
    if request.method == "POST":
        conn.execute(
            "UPDATE deals SET name=?, asset_type=?, location=?, target_raise=?, status=?, notes=? "
            "WHERE id=?",
            (
                request.form["name"],
                request.form.get("asset_type", ""),
                request.form.get("location", ""),
                request.form.get("target_raise", ""),
                request.form.get("status", "Active"),
                request.form.get("notes", ""),
                deal_id,
            ),
        )
        conn.commit()
        conn.close()
        flash("Deal updated.", "success")
        return redirect(url_for("deal_detail", deal_id=deal_id))
    conn.close()
    return render_template("deal_form.html", deal=deal, title="Edit Deal")


@app.route("/deals/<int:deal_id>/delete", methods=["POST"])
def delete_deal(deal_id):
    conn = get_db()
    conn.execute("DELETE FROM outreach WHERE deal_id = ?", (deal_id,))
    conn.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
    conn.commit()
    conn.close()
    flash("Deal deleted.", "info")
    return redirect(url_for("deals"))


# ── Outreach ───────────────────────────────────────────────────────────────────

@app.route("/deals/<int:deal_id>/outreach/new", methods=["GET", "POST"])
def new_outreach(deal_id):
    conn = get_db()
    deal = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
    if not deal:
        conn.close()
        flash("Deal not found.", "danger")
        return redirect(url_for("deals"))
    if request.method == "POST":
        conn.execute(
            "INSERT INTO outreach (deal_id, contact_name, company, email, sent_by, "
            "outreach_date, outreach_summary, response_date, response_summary, follow_up_needed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                deal_id,
                request.form["contact_name"],
                request.form.get("company", ""),
                request.form.get("email", ""),
                request.form.get("sent_by", ""),
                request.form.get("outreach_date") or None,
                request.form.get("outreach_summary", ""),
                request.form.get("response_date") or None,
                request.form.get("response_summary", ""),
                1 if request.form.get("follow_up_needed") else 0,
            ),
        )
        conn.commit()
        conn.close()
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
        conn.close()
        flash("Not found.", "danger")
        return redirect(url_for("deals"))
    if request.method == "POST":
        conn.execute(
            "UPDATE outreach SET contact_name=?, company=?, email=?, sent_by=?, "
            "outreach_date=?, outreach_summary=?, response_date=?, response_summary=?, "
            "follow_up_needed=? WHERE id=?",
            (
                request.form["contact_name"],
                request.form.get("company", ""),
                request.form.get("email", ""),
                request.form.get("sent_by", ""),
                request.form.get("outreach_date") or None,
                request.form.get("outreach_summary", ""),
                request.form.get("response_date") or None,
                request.form.get("response_summary", ""),
                1 if request.form.get("follow_up_needed") else 0,
                outreach_id,
            ),
        )
        conn.commit()
        conn.close()
        flash("Outreach updated.", "success")
        return redirect(url_for("deal_detail", deal_id=deal_id))
    conn.close()
    return render_template("outreach_form.html", deal=deal, outreach=outreach, title="Edit Outreach")


@app.route("/deals/<int:deal_id>/outreach/<int:outreach_id>/delete", methods=["POST"])
def delete_outreach(deal_id, outreach_id):
    conn = get_db()
    conn.execute("DELETE FROM outreach WHERE id = ? AND deal_id = ?", (outreach_id, deal_id))
    conn.commit()
    conn.close()
    flash("Outreach entry deleted.", "info")
    return redirect(url_for("deal_detail", deal_id=deal_id))


# ── GP Contacts ────────────────────────────────────────────────────────────────

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
            (
                request.form["name"],
                request.form.get("title", ""),
                request.form.get("company", ""),
                request.form.get("email", ""),
                request.form.get("phone", ""),
                request.form.get("location", ""),
                request.form.get("aum_range", ""),
                request.form.get("strategy", ""),
                request.form.get("min_check", ""),
                request.form.get("max_check", ""),
                request.form.get("source", ""),
                request.form.get("status", "New"),
                request.form.get("notes", ""),
                request.form.get("last_contacted") or None,
            ),
        )
        conn.commit()
        conn.close()
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
        conn.close()
        flash("Contact not found.", "danger")
        return redirect(url_for("contacts"))
    if request.method == "POST":
        conn.execute(
            "UPDATE gp_contacts SET name=?, title=?, company=?, email=?, phone=?, location=?, "
            "aum_range=?, strategy=?, min_check=?, max_check=?, source=?, status=?, notes=?, "
            "last_contacted=? WHERE id=?",
            (
                request.form["name"],
                request.form.get("title", ""),
                request.form.get("company", ""),
                request.form.get("email", ""),
                request.form.get("phone", ""),
                request.form.get("location", ""),
                request.form.get("aum_range", ""),
                request.form.get("strategy", ""),
                request.form.get("min_check", ""),
                request.form.get("max_check", ""),
                request.form.get("source", ""),
                request.form.get("status", "New"),
                request.form.get("notes", ""),
                request.form.get("last_contacted") or None,
                contact_id,
            ),
        )
        conn.commit()
        conn.close()
        flash("Contact updated.", "success")
        return redirect(url_for("contact_detail", contact_id=contact_id))
    conn.close()
    return render_template("contact_form.html", contact=contact, title="Edit GP Contact")


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
def delete_contact(contact_id):
    conn = get_db()
    conn.execute("DELETE FROM gp_contacts WHERE id = ?", (contact_id,))
    conn.commit()
    conn.close()
    flash("Contact deleted.", "info")
    return redirect(url_for("contacts"))


# Run init_db on startup regardless of how the app is invoked (gunicorn, flask run, etc.)
with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
