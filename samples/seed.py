"""
Seed Script — Populate the running API with demo data.

Usage:
  python samples/seed.py

Requires the API to be running at http://localhost:8000.
"""

from __future__ import annotations

import json
import urllib.request

API = "http://localhost:8000/api/v1"


def post(path: str, data: dict) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{API}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get(path: str) -> dict | list:
    req = urllib.request.Request(f"{API}{path}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main() -> None:
    print("Seeding Context Bridge API…\n")

    # 1. Create user
    user = post("/users/", {
        "display_name": "Alex",
        "location": "Portland, OR",
        "timezone": "America/Los_Angeles",
    })
    user_id = user["id"]
    print(f"✅ Created user: {user['display_name']}  (ID: {user_id})")

    # 2. Add facts
    facts = [
        ("profile", "name", "Alex", "low"),
        ("profile", "age", "32", "medium"),
        ("fitness", "morning_run", "5K at 6:30 AM daily", "low"),
        ("fitness", "goal", "Train for half marathon", "low"),
        ("pet", "pet_name", "Luna", "low"),
        ("pet", "pet_type", "Golden Retriever", "low"),
        ("pet", "vet_appointment", "March 15, annual checkup", "medium"),
        ("food", "diet", "Mostly plant-based", "low"),
        ("food", "allergy", "Tree nuts", "high"),
        ("food", "favorite_cuisine", "Thai", "low"),
        ("home", "smart_thermostat", "Nest, set to 68°F", "low"),
        ("travel", "commute", "Bike, 20 min", "low"),
        ("health", "blood_type", "O+", "critical"),
        ("hobby", "hobby", "Film photography", "low"),
    ]

    for cat, key, value, sens in facts:
        post(f"/users/{user_id}/facts/", {
            "category": cat,
            "key": key,
            "value": value,
            "sensitivity": sens,
        })
        print(f"   + [{cat}] {key} = {value}")

    # 3. Verify
    snapshots = get(f"/users/{user_id}/facts/snapshots")
    total = sum(s["fact_count"] for s in snapshots)
    print(f"\n✅ Seeded {total} facts across {len(snapshots)} categories")
    print(f"\n📋 Use this User ID in the extension: {user_id}")


if __name__ == "__main__":
    main()
