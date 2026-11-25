"""
Step 3: Check how well setlist.fm and Last.fm cover Impact's artists.

Input: sample_artists.csv, which you fill in by hand from impact_artists.csv.
Pick 15 artists: 5 from 2016-18, 5 from 2019-21, 5 from 2022+,
mixing very local acts with bigger ones. Two columns:
  artist,interview_date
  Example Band,2019-03-14

Needs two free API keys set as environment variables:
  SETLISTFM_API_KEY  -> https://www.setlist.fm/settings/api
  LASTFM_API_KEY     -> https://www.last.fm/api/account/create

Output: coverage.csv plus a go / narrow / drop verdict.
Check the setlist_match_name column by hand: the search takes the top
result, which can be a different artist with a similar name.

Run:  python step3_coverage_check.py
"""

import csv
import os
import time
import requests

SETLIST_API = "https://api.setlist.fm/rest/1.0"
LASTFM_API = "https://ws.audioscrobbler.com/2.0/"

MIN_SHOWS = 5  # "usable" = at least this many dated shows on setlist.fm


def setlist_lookup(name, headers):
    # Find the artist, then ask how many setlists they have in total
    params = {"artistName": name, "sort": "relevance", "p": 1}
    r = requests.get(SETLIST_API + "/search/artists", params=params, headers=headers, timeout=30)
    time.sleep(0.6)
    if r.status_code != 200:
        return "", "", 0

    artists = r.json().get("artist", [])
    if len(artists) == 0:
        return "", "", 0

    match = artists[0]
    mbid = match.get("mbid", "")
    if mbid == "":
        return match.get("name", ""), "", 0

    r = requests.get(SETLIST_API + "/artist/" + mbid + "/setlists",
                     params={"p": 1}, headers=headers, timeout=30)
    time.sleep(0.6)
    if r.status_code != 200:
        return match.get("name", ""), mbid, 0

    total = r.json().get("total", 0)
    return match.get("name", ""), mbid, total


def lastfm_lookup(name, key):
    params = {
        "method": "artist.getinfo",
        "artist": name,
        "api_key": key,
        "format": "json",
        "autocorrect": 1,
    }
    r = requests.get(LASTFM_API, params=params, timeout=30)
    time.sleep(0.3)
    if r.status_code != 200:
        return 0
    data = r.json()
    if "error" in data:
        return 0
    stats = data.get("artist", {}).get("stats", {})
    return int(stats.get("listeners", 0))


def main():
    setlist_key = os.environ.get("SETLISTFM_API_KEY")
    lastfm_key = os.environ.get("LASTFM_API_KEY")
    if not setlist_key or not lastfm_key:
        print("Set SETLISTFM_API_KEY and LASTFM_API_KEY first (see the top of this file).")
        return

    headers = {"x-api-key": setlist_key, "Accept": "application/json"}

    artists = []
    with open("sample_artists.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            artists.append(row)

    results = []
    usable_count = 0

    for row in artists:
        name = row["artist"].strip()
        print("Checking", name, "...")

        match_name, mbid, show_count = setlist_lookup(name, headers)
        listeners = lastfm_lookup(name, lastfm_key)

        has_setlist = show_count >= MIN_SHOWS
        has_lastfm = listeners > 0
        usable = has_setlist and has_lastfm
        if usable:
            usable_count += 1

        results.append({
            "artist": name,
            "interview_date": row.get("interview_date", ""),
            "setlist_match_name": match_name,
            "setlist_mbid": mbid,
            "setlist_total_shows": show_count,
            "lastfm_listeners": listeners,
            "setlist_ok": "yes" if has_setlist else "no",
            "lastfm_ok": "yes" if has_lastfm else "no",
            "usable_both": "yes" if usable else "no",
        })

    with open("coverage.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    setlist_yes = 0
    lastfm_yes = 0
    for row in results:
        if row["setlist_ok"] == "yes":
            setlist_yes += 1
        if row["lastfm_ok"] == "yes":
            lastfm_yes += 1

    n = len(results)
    print("\nSaved coverage.csv")
    print("setlist.fm (5+ shows):", setlist_yes, "of", n)
    print("Last.fm (any listeners):", lastfm_yes, "of", n)
    print("Usable in both:", usable_count, "of", n)

    if usable_count >= 10:
        print("Verdict: GO")
    elif usable_count >= 5:
        print("Verdict: NARROW - timelines for covered artists, lighter analysis")
    else:
        print("Verdict: DROP or rethink - discuss with mentor in Call 1")


if __name__ == "__main__":
    main()
