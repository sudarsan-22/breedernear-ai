"""Load the curated sample breeders and listings into Firestore (idempotent: documents are overwritten).

Usage:
    GOOGLE_CLOUD_PROJECT=<project-id> python scripts/seed_firestore.py

Screening is recomputed by code on every run, so re-run this after changing trust rules or seed data.
It also creates or resets the two default demo accounts and their data (breedernear_core/default_accounts.py).
"""

import os
import sys

from google.cloud import firestore

from breedernear_core import deps
from breedernear_core.catalog import breeders, seed_listings
from breedernear_core.default_accounts import CUSTOMER_LOGIN, PASSWORD, SELLER_LOGIN, seed_default_accounts
from breedernear_core.services.store import FirestoreStore


def main() -> int:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        print("Set GOOGLE_CLOUD_PROJECT first.", file=sys.stderr)
        return 1
    db = firestore.Client(project=project)
    batch = db.batch()
    people = breeders()
    for breeder in people.values():
        batch.set(db.collection("breeders").document(breeder["id"]), breeder)
    records = seed_listings()
    for listing in records:
        batch.set(db.collection("listings").document(listing["id"]), listing)
    batch.commit()
    levels = {}
    for r in records:
        levels[r["trust_level"]] = levels.get(r["trust_level"], 0) + 1
    print(f"Seeded {len(people)} breeders and {len(records)} listings into {project}: {levels}")
    store = FirestoreStore(project=project)
    deps.set_deps(store=store)
    seed_default_accounts(store)
    print(f"Default accounts ready: {SELLER_LOGIN} and {CUSTOMER_LOGIN} (password {PASSWORD})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
