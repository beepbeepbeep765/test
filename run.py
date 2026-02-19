"""Local development runner — python run.py"""
from app import app, init_db

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
