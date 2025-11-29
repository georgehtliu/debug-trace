#!/usr/bin/env python3
"""Initialize the database."""
from app.database import init_db

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")

