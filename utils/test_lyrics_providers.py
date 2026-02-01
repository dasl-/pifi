#!/usr/bin/env python3
"""Test lyrics provider comparison and timing accuracy.

These tests verify the smart provider selection logic that chooses between
Musixmatch (word-by-word) and LRCLIB (more accurate timing) based on
timestamp comparison.
"""

import re
import syncedlyrics


def get_first_timestamp(lrc_text):
    """Extract the first lyric line timestamp from LRC text."""
    if not lrc_text:
        return None

    for line in lrc_text.split('\n'):
        # Skip metadata lines
        if any(tag in line.lower() for tag in ['[ar:', '[ti:', '[al:', '[by:']):
            continue

        match = re.match(r'\[(\d+):(\d+)\.(\d+)\]', line)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            centiseconds = int(match.group(3))
            return minutes * 60 + seconds + centiseconds / 100.0

    return None


def test_provider_comparison(query, expected_winner=None):
    """Test provider comparison for a given song.

    Args:
        query: Search query (e.g., "Mr Brightside The Killers")
        expected_winner: Optional expected provider ('Musixmatch', 'LRCLIB', or None)

    Returns:
        Dict with test results
    """
    print(f"\n{'='*60}")
    print(f"Testing: {query}")
    print('='*60)

    # Fetch from both providers
    mm_lrc = None
    ll_lrc = None

    try:
        mm_lrc = syncedlyrics.search(
            query, synced_only=True, enhanced=True,
            providers=['Musixmatch']
        )
    except Exception as e:
        print(f"Musixmatch error: {e}")

    try:
        ll_lrc = syncedlyrics.search(
            query, synced_only=True,
            providers=['Lrclib']
        )
    except Exception as e:
        print(f"LRCLIB error: {e}")

    mm_ts = get_first_timestamp(mm_lrc)
    ll_ts = get_first_timestamp(ll_lrc)

    print(f"Musixmatch: {'%.2fs' % mm_ts if mm_ts else 'not found'}")
    print(f"LRCLIB:     {'%.2fs' % ll_ts if ll_ts else 'not found'}")

    # Determine winner
    winner = None
    diff = None

    if mm_ts and ll_ts:
        diff = abs(mm_ts - ll_ts)
        print(f"Difference: {diff:.2f}s")

        if diff <= 1.0:
            winner = 'Musixmatch'
            print("-> Would use Musixmatch (word-by-word, timing matches)")
        else:
            winner = 'LRCLIB'
            print("-> Would use LRCLIB (more accurate timing)")
    elif ll_ts:
        winner = 'LRCLIB'
        print("-> Would use LRCLIB (only option)")
    elif mm_ts:
        winner = 'Musixmatch'
        print("-> Would use Musixmatch (only option)")
    else:
        print("-> No lyrics found from either provider")

    # Check enhanced format
    is_enhanced = mm_lrc and '<' in mm_lrc and '>' in mm_lrc
    print(f"Musixmatch has word-by-word: {is_enhanced}")

    result = {
        'query': query,
        'musixmatch_ts': mm_ts,
        'lrclib_ts': ll_ts,
        'diff': diff,
        'winner': winner,
        'is_enhanced': is_enhanced,
    }

    if expected_winner and winner != expected_winner:
        print(f"WARNING: Expected {expected_winner}, got {winner}")
        result['passed'] = False
    else:
        result['passed'] = True

    return result


def test_lrc_parsing():
    """Test LRC format parsing for both standard and enhanced formats."""
    print("\n" + "="*60)
    print("Testing LRC Parsing")
    print("="*60)

    # Enhanced format with start+end pairs (Musixmatch style)
    enhanced_start_end = '<00:11.47> I <00:11.48>   <00:12.72> do <00:12.94>   <00:12.99> not <00:13.86>'

    # Enhanced format with start-only
    enhanced_start_only = '<00:12.34>First <00:12.89>line <00:13.45>of <00:13.78>lyrics'

    # Pattern that captures timestamp and following content
    pattern = r'<(\d+):(\d+)\.(\d+)>([^<]*)'

    print("\nStart+End format (Musixmatch):")
    print(f"  Input: {enhanced_start_end[:50]}...")
    raw_pairs = []
    for m in re.finditer(pattern, enhanced_start_end):
        ts = int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 100.0
        content = m.group(4).strip()
        raw_pairs.append((ts, content))
    word_timings = [(ts, word.upper()) for ts, word in raw_pairs if word]
    print(f"  Parsed words: {[w for _, w in word_timings]}")
    print(f"  Timestamps: {[f'{ts:.2f}' for ts, _ in word_timings]}")
    assert len(word_timings) == 3, f"Expected 3 words, got {len(word_timings)}"
    print("  PASS")

    print("\nStart-only format:")
    print(f"  Input: {enhanced_start_only}")
    raw_pairs = []
    for m in re.finditer(pattern, enhanced_start_only):
        ts = int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 100.0
        content = m.group(4).strip()
        raw_pairs.append((ts, content))
    word_timings = [(ts, word.upper()) for ts, word in raw_pairs if word]
    print(f"  Parsed words: {[w for _, w in word_timings]}")
    print(f"  Timestamps: {[f'{ts:.2f}' for ts, _ in word_timings]}")
    assert len(word_timings) == 4, f"Expected 4 words, got {len(word_timings)}"
    print("  PASS")


# Test cases - songs with known provider quality differences
TEST_CASES = [
    # (query, expected_winner or None to just report)
    ("Mr Brightside The Killers", "LRCLIB"),  # Known: Musixmatch ~3s off
    ("Bohemian Rhapsody Queen", None),
    ("15 Step Radiohead", None),  # Known to have enhanced lyrics
    ("Creep Radiohead", None),
    ("Shape of You Ed Sheeran", None),
    ("Harder Better Faster Stronger Daft Punk", None),
]


if __name__ == '__main__':
    import sys

    # Run parsing tests first (no network needed)
    test_lrc_parsing()

    # Run provider comparison tests
    results = []
    for query, expected in TEST_CASES:
        try:
            result = test_provider_comparison(query, expected)
            results.append(result)
        except Exception as e:
            print(f"Error testing '{query}': {e}")
            results.append({'query': query, 'passed': False, 'error': str(e)})

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed = sum(1 for r in results if r.get('passed', False))
    total = len(results)

    for r in results:
        status = "PASS" if r.get('passed') else "FAIL"
        winner = r.get('winner', 'none')
        diff = r.get('diff')
        diff_str = f" (diff={diff:.2f}s)" if diff else ""
        print(f"  [{status}] {r['query']}: {winner}{diff_str}")

    print(f"\n{passed}/{total} tests passed")
    sys.exit(0 if passed == total else 1)
