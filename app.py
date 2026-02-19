import os
import sqlite3
from datetime import datetime, date, timedelta
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
            follow_up_date TEXT,
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
            next_contact_date TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS contact_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            note_date TEXT,
            note_text TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (contact_id) REFERENCES gp_contacts(id)
        );

        CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT,
            body TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)

    # Safe migrations for existing databases
    for stmt in [
        "ALTER TABLE outreach ADD COLUMN follow_up_date TEXT",
        "ALTER TABLE gp_contacts ADD COLUMN next_contact_date TEXT",
    ]:
        try:
            conn.execute(stmt)
        except Exception:
            pass

    # Seed default email templates once
    if conn.execute("SELECT COUNT(*) FROM email_templates").fetchone()[0] == 0:
        seed = [
            (
                "Initial Deal Introduction",
                "Introduction: [DEAL NAME]",
                "Hi [CONTACT NAME],\n\nI hope this finds you well. I wanted to reach out regarding an opportunity we're currently marketing that I thought might be a strong fit for your investment criteria.\n\n[DEAL NAME] is a [ASSET TYPE] opportunity located in [LOCATION], with a target equity raise of [TARGET RAISE]. A few highlights:\n\n\u2022 [HIGHLIGHT 1]\n\u2022 [HIGHLIGHT 2]\n\u2022 [HIGHLIGHT 3]\n\nHappy to send over the full investment summary if you have interest. Would you have 15 minutes for a quick call this week?\n\nBest,\n[YOUR NAME]",
            ),
            (
                "Follow-Up (No Response)",
                "Following Up: [DEAL NAME]",
                "Hi [CONTACT NAME],\n\nJust wanted to follow up on my previous note regarding [DEAL NAME] \u2014 I know things get busy and wanted to make sure this didn\u2019t fall through the cracks.\n\nHappy to send the investment summary or get on a quick call at your convenience.\n\nBest,\n[YOUR NAME]",
            ),
            (
                "Follow-Up After Interest",
                "Next Steps: [DEAL NAME]",
                "Hi [CONTACT NAME],\n\nGreat speaking with you. As discussed, I\u2019m sending over the materials for [DEAL NAME].\n\nPlease don\u2019t hesitate to reach out with any questions. I\u2019d suggest we reconnect in two weeks to discuss further \u2014 does that work on your end?\n\nBest,\n[YOUR NAME]",
            ),
            (
                "Meeting Request",
                "Meeting Request: [DEAL NAME]",
                "Hi [CONTACT NAME],\n\nThank you for your interest in [DEAL NAME]. I\u2019d love to set up a call to walk you through the deal in more detail.\n\nAre any of the following times convenient?\n\n\u2022 [TIME OPTION 1]\n\u2022 [TIME OPTION 2]\n\u2022 [TIME OPTION 3]\n\nOr feel free to send over a time that works better for you.\n\nBest,\n[YOUR NAME]",
            ),
        ]
        conn.executemany(
            "INSERT INTO email_templates (name, subject, body) VALUES (?, ?, ?)", seed
        )

    conn.commit()
    conn.close()


# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_money(s):
    """Parse '$25M', '$500K', '$1B\u2013$2B' etc. into a float."""
    if not s:
        return None
    s = s.replace("$", "").replace(",", "").replace(" ", "").upper()
    for sep in ["\u2013", "\u2014", "-", "TO"]:
        if sep in s:
            parts = s.split(sep, 1)
            vals = [parse_money(p) for p in parts]
            vals = [v for v in vals if v is not None]
            return sum(vals) / len(vals) if vals else None
    mult = 1
    if s.endswith("B"):
        mult = 1_000_000_000; s = s[:-1]
    elif s.endswith("M"):
        mult = 1_000_000; s = s[:-1]
    elif s.endswith("K"):
        mult = 1_000; s = s[:-1]
    try:
        return float(s) * mult
    except Exception:
        return None


def score_gp(deal, gp):
    """Return (int score, [str reasons]) for a GP against a deal."""
    score = 0
    reasons = []
    deal_raise = parse_money(deal["target_raise"])
    gp_min = parse_money(gp["min_check"])
    gp_max = parse_money(gp["max_check"])

    if deal_raise and gp_min and gp_max:
        if gp_min <= deal_raise <= gp_max:
            score += 3; reasons.append("check size fits")
        elif deal_raise <= gp_max:
            score += 1; reasons.append("within max check")
    elif deal_raise and gp_max and deal_raise <= gp_max:
        score += 1; reasons.append("within max check")

    # Strategy keyword overlap
    if deal["asset_type"] and gp["strategy"]:
        stop = {"and", "or", "the", "in", "of", "for", "a", "an", "with",
                "value", "add", "core", "plus", "class", "real", "estate"}
        dw = set(deal["asset_type"].lower().split()) - stop
        gw = set(gp["strategy"].lower().split()) - stop
        if dw & gw:
            score += 2; reasons.append("strategy match")

    # Location overlap (city-level)
    if deal["location"] and gp["location"]:
        city = deal["location"].lower().split(",")[0].strip()
        if city and city in gp["location"].lower():
            score += 1; reasons.append("same market")

    return score, reasons


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    today = date.today().isoformat()
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

    overdue_outreach = conn.execute(
        "SELECT o.*, d.name as deal_name FROM outreach o "
        "JOIN deals d ON o.deal_id = d.id "
        "WHERE o.follow_up_needed = 1 AND o.follow_up_date IS NOT NULL AND o.follow_up_date <= ? "
        "ORDER BY o.follow_up_date ASC",
        (today,),
    ).fetchall()

    overdue_contacts = conn.execute(
        "SELECT * FROM gp_contacts "
        "WHERE next_contact_date IS NOT NULL AND next_contact_date <= ? "
        "ORDER BY next_contact_date ASC",
        (today,),
    ).fetchall()

    recent_activity = conn.execute(
        "SELECT o.*, d.name as deal_name FROM outreach o "
        "JOIN deals d ON o.deal_id = d.id "
        "ORDER BY COALESCE(o.outreach_date, o.created_at) DESC LIMIT 8"
    ).fetchall()

    conn.close()
    return render_template(
        "index.html",
        deals=deals,
        gp_count=gp_count,
        pending_followups=pending_followups,
        overdue_outreach=overdue_outreach,
        overdue_contacts=overdue_contacts,
        recent_activity=recent_activity,
        today=today,
    )


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
            "INSERT INTO deals (name, asset_type, location, target_raise, status, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (request.form["name"], request.form.get("asset_type", ""),
             request.form.get("location", ""), request.form.get("target_raise", ""),
             request.form.get("status", "Active"), request.form.get("notes", "")),
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
        conn.close(); flash("Deal not found.", "danger"); return redirect(url_for("deals"))
    outreaches = conn.execute(
        "SELECT * FROM outreach WHERE deal_id = ? ORDER BY outreach_date DESC, created_at DESC",
        (deal_id,),
    ).fetchall()
    all_gps = conn.execute("SELECT * FROM gp_contacts").fetchall()
    matches = []
    for gp in all_gps:
        sc, reasons = score_gp(deal, gp)
        if sc > 0:
            matches.append({"gp": gp, "score": sc, "reasons": reasons})
    matches.sort(key=lambda x: x["score"], reverse=True)
    conn.close()
    return render_template("deal_detail.html", deal=deal, outreaches=outreaches, matching_gps=matches[:10])


@app.route("/deals/<int:deal_id>/edit", methods=["GET", "POST"])
def edit_deal(deal_id):
    conn = get_db()
    deal = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
    if not deal:
        conn.close(); flash("Deal not found.", "danger"); return redirect(url_for("deals"))
    if request.method == "POST":
        conn.execute(
            "UPDATE deals SET name=?, asset_type=?, location=?, target_raise=?, status=?, notes=? WHERE id=?",
            (request.form["name"], request.form.get("asset_type", ""),
             request.form.get("location", ""), request.form.get("target_raise", ""),
             request.form.get("status", "Active"), request.form.get("notes", ""), deal_id),
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


# ── Outreach ───────────────────────────────────────────────────────────────────

@app.route("/deals/<int:deal_id>/outreach/new", methods=["GET", "POST"])
def new_outreach(deal_id):
    conn = get_db()
    deal = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
    if not deal:
        conn.close(); flash("Deal not found.", "danger"); return redirect(url_for("deals"))
    if request.method == "POST":
        conn.execute(
            "INSERT INTO outreach (deal_id, contact_name, company, email, sent_by, "
            "outreach_date, outreach_summary, response_date, response_summary, follow_up_needed, follow_up_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (deal_id, request.form["contact_name"], request.form.get("company", ""),
             request.form.get("email", ""), request.form.get("sent_by", ""),
             request.form.get("outreach_date") or None, request.form.get("outreach_summary", ""),
             request.form.get("response_date") or None, request.form.get("response_summary", ""),
             1 if request.form.get("follow_up_needed") else 0,
             request.form.get("follow_up_date") or None),
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
    outreach = conn.execute("SELECT * FROM outreach WHERE id = ? AND deal_id = ?", (outreach_id, deal_id)).fetchone()
    if not deal or not outreach:
        conn.close(); flash("Not found.", "danger"); return redirect(url_for("deals"))
    if request.method == "POST":
        conn.execute(
            "UPDATE outreach SET contact_name=?, company=?, email=?, sent_by=?, "
            "outreach_date=?, outreach_summary=?, response_date=?, response_summary=?, "
            "follow_up_needed=?, follow_up_date=? WHERE id=?",
            (request.form["contact_name"], request.form.get("company", ""),
             request.form.get("email", ""), request.form.get("sent_by", ""),
             request.form.get("outreach_date") or None, request.form.get("outreach_summary", ""),
             request.form.get("response_date") or None, request.form.get("response_summary", ""),
             1 if request.form.get("follow_up_needed") else 0,
             request.form.get("follow_up_date") or None, outreach_id),
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


# ── Activity Log ───────────────────────────────────────────────────────────────

@app.route("/activity")
def activity():
    conn = get_db()
    entries = conn.execute(
        "SELECT o.*, d.name as deal_name FROM outreach o "
        "JOIN deals d ON o.deal_id = d.id "
        "ORDER BY COALESCE(o.outreach_date, o.created_at) DESC LIMIT 150"
    ).fetchall()
    conn.close()
    return render_template("activity.html", entries=entries)


# ── GP Contacts ────────────────────────────────────────────────────────────────

@app.route("/contacts")
def contacts():
    q = request.args.get("q", "").strip()
    sf = request.args.get("status", "")
    conn = get_db()
    sql = "SELECT * FROM gp_contacts WHERE 1=1"
    params = []
    if q:
        sql += " AND (name LIKE ? OR company LIKE ? OR strategy LIKE ? OR location LIKE ?)"
        params += [f"%{q}%"] * 4
    if sf:
        sql += " AND status = ?"
        params.append(sf)
    rows = conn.execute(sql + " ORDER BY created_at DESC", params).fetchall()
    conn.close()
    return render_template("contacts.html", contacts=rows, q=q, status_filter=sf)


@app.route("/contacts/new", methods=["GET", "POST"])
def new_contact():
    if request.method == "POST":
        conn = get_db()
        conn.execute(
            "INSERT INTO gp_contacts (name, title, company, email, phone, location, "
            "aum_range, strategy, min_check, max_check, source, status, notes, last_contacted, next_contact_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (request.form["name"], request.form.get("title", ""), request.form.get("company", ""),
             request.form.get("email", ""), request.form.get("phone", ""), request.form.get("location", ""),
             request.form.get("aum_range", ""), request.form.get("strategy", ""),
             request.form.get("min_check", ""), request.form.get("max_check", ""),
             request.form.get("source", ""), request.form.get("status", "New"),
             request.form.get("notes", ""), request.form.get("last_contacted") or None,
             request.form.get("next_contact_date") or None),
        )
        conn.commit(); conn.close()
        flash("GP contact added.", "success")
        return redirect(url_for("contacts"))
    return render_template("contact_form.html", contact=None, title="Add GP Contact")


@app.route("/contacts/<int:contact_id>")
def contact_detail(contact_id):
    conn = get_db()
    contact = conn.execute("SELECT * FROM gp_contacts WHERE id = ?", (contact_id,)).fetchone()
    if not contact:
        conn.close(); flash("Contact not found.", "danger"); return redirect(url_for("contacts"))
    notes = conn.execute(
        "SELECT * FROM contact_notes WHERE contact_id = ? ORDER BY note_date DESC, created_at DESC",
        (contact_id,),
    ).fetchall()
    conn.close()
    return render_template("contact_detail.html", contact=contact, notes=notes)


@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def edit_contact(contact_id):
    conn = get_db()
    contact = conn.execute("SELECT * FROM gp_contacts WHERE id = ?", (contact_id,)).fetchone()
    if not contact:
        conn.close(); flash("Contact not found.", "danger"); return redirect(url_for("contacts"))
    if request.method == "POST":
        conn.execute(
            "UPDATE gp_contacts SET name=?, title=?, company=?, email=?, phone=?, location=?, "
            "aum_range=?, strategy=?, min_check=?, max_check=?, source=?, status=?, notes=?, "
            "last_contacted=?, next_contact_date=? WHERE id=?",
            (request.form["name"], request.form.get("title", ""), request.form.get("company", ""),
             request.form.get("email", ""), request.form.get("phone", ""), request.form.get("location", ""),
             request.form.get("aum_range", ""), request.form.get("strategy", ""),
             request.form.get("min_check", ""), request.form.get("max_check", ""),
             request.form.get("source", ""), request.form.get("status", "New"),
             request.form.get("notes", ""), request.form.get("last_contacted") or None,
             request.form.get("next_contact_date") or None, contact_id),
        )
        conn.commit(); conn.close()
        flash("Contact updated.", "success")
        return redirect(url_for("contact_detail", contact_id=contact_id))
    conn.close()
    return render_template("contact_form.html", contact=contact, title="Edit GP Contact")


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
def delete_contact(contact_id):
    conn = get_db()
    conn.execute("DELETE FROM contact_notes WHERE contact_id = ?", (contact_id,))
    conn.execute("DELETE FROM gp_contacts WHERE id = ?", (contact_id,))
    conn.commit(); conn.close()
    flash("Contact deleted.", "info")
    return redirect(url_for("contacts"))


# ── Contact Quick Notes ────────────────────────────────────────────────────────

@app.route("/contacts/<int:contact_id>/notes/add", methods=["POST"])
def add_contact_note(contact_id):
    note_text = request.form.get("note_text", "").strip()
    if note_text:
        conn = get_db()
        conn.execute(
            "INSERT INTO contact_notes (contact_id, note_date, note_text) VALUES (?, ?, ?)",
            (contact_id, request.form.get("note_date") or date.today().isoformat(), note_text),
        )
        conn.commit(); conn.close()
        flash("Note added.", "success")
    return redirect(url_for("contact_detail", contact_id=contact_id))


@app.route("/contacts/<int:contact_id>/notes/<int:note_id>/delete", methods=["POST"])
def delete_contact_note(contact_id, note_id):
    conn = get_db()
    conn.execute("DELETE FROM contact_notes WHERE id = ? AND contact_id = ?", (note_id, contact_id))
    conn.commit(); conn.close()
    flash("Note deleted.", "info")
    return redirect(url_for("contact_detail", contact_id=contact_id))


# ── Email Templates ────────────────────────────────────────────────────────────

@app.route("/templates")
def templates():
    conn = get_db()
    rows = conn.execute("SELECT * FROM email_templates ORDER BY created_at").fetchall()
    conn.close()
    return render_template("templates.html", templates=rows)


@app.route("/templates/new", methods=["GET", "POST"])
def new_template():
    if request.method == "POST":
        conn = get_db()
        conn.execute(
            "INSERT INTO email_templates (name, subject, body) VALUES (?, ?, ?)",
            (request.form["name"], request.form.get("subject", ""), request.form["body"]),
        )
        conn.commit(); conn.close()
        flash("Template saved.", "success")
        return redirect(url_for("templates"))
    return render_template("template_form.html", template=None, title="New Template")


@app.route("/templates/<int:template_id>/edit", methods=["GET", "POST"])
def edit_template(template_id):
    conn = get_db()
    tmpl = conn.execute("SELECT * FROM email_templates WHERE id = ?", (template_id,)).fetchone()
    if not tmpl:
        conn.close(); flash("Not found.", "danger"); return redirect(url_for("templates"))
    if request.method == "POST":
        conn.execute(
            "UPDATE email_templates SET name=?, subject=?, body=? WHERE id=?",
            (request.form["name"], request.form.get("subject", ""), request.form["body"], template_id),
        )
        conn.commit(); conn.close()
        flash("Template updated.", "success")
        return redirect(url_for("templates"))
    conn.close()
    return render_template("template_form.html", template=tmpl, title="Edit Template")


@app.route("/templates/<int:template_id>/delete", methods=["POST"])
def delete_template(template_id):
    conn = get_db()
    conn.execute("DELETE FROM email_templates WHERE id = ?", (template_id,))
    conn.commit(); conn.close()
    flash("Template deleted.", "info")
    return redirect(url_for("templates"))


# ── Outlook Sync ───────────────────────────────────────────────────────────────

@app.route("/deals/<int:deal_id>/outlook", methods=["GET", "POST"])
def outlook_sync(deal_id):
    conn = get_db()
    deal = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
    if not deal:
        conn.close(); flash("Deal not found.", "danger"); return redirect(url_for("deals"))

    emails = []
    error = None
    search_email = request.form.get("search_email", "").strip()
    days = int(request.form.get("days", 30))

    if request.method == "POST" and search_email:
        try:
            import win32com.client
            outlook = win32com.client.Dispatch("Outlook.Application")
            ns = outlook.GetNamespace("MAPI")
            sent = ns.GetDefaultFolder(5)
            cutoff = datetime.now() - timedelta(days=days)
            for item in sent.Items:
                try:
                    if item.Class != 43:
                        continue
                    sent_on = item.SentOn.replace(tzinfo=None)
                    if sent_on < cutoff:
                        continue
                    recipients = (item.To or "") + ";" + (item.CC or "")
                    if search_email.lower() not in recipients.lower():
                        continue
                    emails.append({
                        "subject": item.Subject or "",
                        "to": item.To or "",
                        "sent_on": sent_on.strftime("%Y-%m-%d"),
                        "preview": (item.Body or "")[:400].replace("\r\n", " ").replace("\n", " "),
                    })
                except Exception:
                    continue
        except ImportError:
            error = "pywin32 not installed. In your Command Prompt run: pip install pywin32"
        except Exception as e:
            error = f"Could not connect to Outlook: {e}"

    conn.close()
    return render_template(
        "outlook_sync.html", deal=deal, emails=emails,
        error=error, search_email=search_email, days=days,
    )


@app.route("/deals/<int:deal_id>/outlook/import", methods=["POST"])
def outlook_import(deal_id):
    conn = get_db()
    conn.execute(
        "INSERT INTO outreach (deal_id, contact_name, company, email, sent_by, "
        "outreach_date, outreach_summary, follow_up_needed) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
        (deal_id, request.form.get("contact_name", ""), request.form.get("company", ""),
         request.form.get("email", ""), request.form.get("sent_by", ""),
         request.form.get("outreach_date", ""), request.form.get("outreach_summary", "")),
    )
    conn.commit(); conn.close()
    flash("Email imported as outreach entry.", "success")
    return redirect(url_for("deal_detail", deal_id=deal_id))


with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
