"""Local development runner — python run.py"""
import os

# Load .env file if present (copy .env.example to .env and fill in values)
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# Set a local dev password if none is configured
if not os.environ.get("CRM_PASSWORD"):
    os.environ["CRM_PASSWORD"] = "localdev"

from app import app, init_db

if __name__ == "__main__":
    init_db()
    app.run(debug=False, host="127.0.0.1", port=5000)
