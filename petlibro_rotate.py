#!/usr/bin/env python3
"""
PetLibro Wet Feeder Plate Rotator
Plate is determined by time so no state file is needed (works in ephemeral containers).
Credentials are read from environment variables:
  PETLIBRO_EMAIL, PETLIBRO_PASSWORD, PETLIBRO_DEVICE_SN, PETLIBRO_START_EPOCH
"""

import gzip
import hashlib
import json
import os
import time
import urllib.request
from datetime import datetime, timezone

# ── Config from environment ──────────────────────────────────────────────────
EMAIL     = os.environ["PETLIBRO_EMAIL"]
PASSWORD  = os.environ["PETLIBRO_PASSWORD"]
DEVICE_SN = os.environ["PETLIBRO_DEVICE_SN"]

BASE_URL   = "https://api.us.petlibro.com"
NUM_PLATES = 3
TIMEZONE   = "America/New_York"
# ────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "Content-Type":   "application/json",
    "source":         "ANDROID",
    "language":       "EN",
    "timezone":       TIMEZONE,
    "version":        "1.3.45",
    "accept-encoding": "gzip",
}


def post(path, payload, token=None):
    headers = HEADERS.copy()
    if token:
        headers["token"] = token
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE_URL + path, data=data, headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
        if r.info().get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return json.loads(raw)


def login():
    pw_hash = hashlib.md5(PASSWORD.encode("UTF-8")).hexdigest()
    resp = post("/member/auth/login", {
        "appId":               1,
        "appSn":               "c35772530d1041699c87fe62348507a8",
        "country":             "US",
        "email":               EMAIL,
        "password":            pw_hash,
        "phoneBrand":          "",
        "phoneSystemVersion":  "",
        "timezone":            TIMEZONE,
    })
    if resp.get("code") != 0:
        raise RuntimeError(f"Login failed: {resp.get('msg')} (code {resp.get('code')})")
    return resp["data"]["token"]


def current_plate() -> int:
    # Cron fires at 0:00, 2:00, 4:00 ... so hour//2 gives the interval index.
    hour = datetime.now(timezone.utc).hour
    return (hour // 2) % NUM_PLATES + 1


def main():
    plate = current_plate()
    print(f"Logging in...")
    token = login()
    print(f"Opening plate {plate}...")
    resp = post("/device/wetFeedingPlan/manualFeedNow", {
        "deviceSn": DEVICE_SN,
        "plate":    plate,
    }, token=token)
    if resp.get("code") != 0:
        raise RuntimeError(f"manualFeedNow failed: {resp.get('msg')} (code {resp.get('code')})")
    print(f"Done. Plate {plate} opened successfully.")


if __name__ == "__main__":
    main()
