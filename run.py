"""Local development runner — python run.py"""
import os

# Set a local dev password if none is configured
if not os.environ.get("CRM_PASSWORD"):
    os.environ["CRM_PASSWORD"] = "localdev"

from app import app, init_db

if __name__ == "__main__":
    init_db()
    app.run(debug=False, host="127.0.0.1", port=5000)
