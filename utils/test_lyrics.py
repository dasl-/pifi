#!/usr/bin/env python3
"""Test syncedlyrics library with known songs."""

import syncedlyrics

TEST_SONGS = [
    ("Bohemian Rhapsody", "Queen"),
    ("Creep", "Radiohead"),
    ("Like Spinning Plates", "Radiohead"),
    ("Karma Police", "Radiohead"),
    ("Billie Jean", "Michael Jackson"),
]

print("Testing syncedlyrics library...\n")
print(f"syncedlyrics version: {syncedlyrics.__version__}\n")

for title, artist in TEST_SONGS:
    query = f"{title} {artist}"
    print(f"Searching: '{query}'")

    try:
        lrc = syncedlyrics.search(query)
        if lrc:
            lines = [l for l in lrc.split('\n') if l.strip() and '[' in l]
            print(f"  Found {len(lines)} lines")
            if lines:
                # Show first non-metadata line
                for line in lines[:5]:
                    if not any(tag in line.lower() for tag in ['[ar:', '[ti:', '[al:', '[by:']):
                        print(f"  Preview: {line[:60]}")
                        break
        else:
            print("  No lyrics found")
    except Exception as e:
        print(f"  Error: {e}")

    print()
