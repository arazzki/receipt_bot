import sys
from pathlib import Path

# Add root project path to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import logging
from database.connection import init_db, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

if __name__ == "__main__":
    print(f"Initializing database using engine: {engine.url}")
    init_db()
    print("Database initialization complete.")
