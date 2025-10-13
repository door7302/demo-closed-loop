#!/usr/bin/env python3
import json
from pymongo import MongoClient

# === CONFIG ===
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "networkdb"
DATA_FILE = "data.json"

def init_db():
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # Drop existing collections (optional, for clean re-init)
    db.routers.drop()
    db.pops.drop()
    db.cmerrors.drop()

    # Load JSON data
    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    routers_data = data.get("routers", [])
    pops_data = data.get("pops", [])
    cmerrors_data = data.get("cmerrors", [])

    # Insert data into MongoDB
    if routers_data:
        db.routers.insert_many(routers_data)
        print(f"Inserted {len(routers_data)} routers")

    if pops_data:
        db.pops.insert_many(pops_data)
        print(f"Inserted {len(pops_data)} POPs")

    if cmerrors_data:
        db.cmerrors.insert_many(cmerrors_data)
        print(f"Inserted {len(cmerrors_data)} cmerror documents")

    # Create indexes
    db.routers.create_index("router_name", unique=True)
    db.pops.create_index("pop_name", unique=True)
    db.cmerrors.create_index("router_name", unique=True)

    print("✅ Database initialized successfully.")

if __name__ == "__main__":
    init_db()