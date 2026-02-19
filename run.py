"""Local development runner — python run.py"""
from app import app, init_db

if __name__ == "__main__":
    init_db()
    app.run(debug=False, host="127.0.0.1", port=5000)
