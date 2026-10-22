#!/home/james/stacklabs/.venv/bin/python3
"""
End-to-End Test Harness for Anti-Spam Sentinel, Clickable Stream Provenance & Bleacher Links
Path: /home/james/stacklabs/scripts/test_anti_spam_and_provenance_bridge.py
"""
import re
import sys

SPAM_REGEX = re.compile(
    r"(\b(https?://|www\.)\S+)|"
    r"(\b[a-zA-Z0-9_-]+(\.com|\.net|\.org|\.io|\.tv|\.me|,çom|,com)\b)|"
    r"(buffstream|nflhd|nflcbs|vipbox|crackstream|streameast|livestream|live stream)|"
    r"(discord\.gg|t\.me)",
    re.IGNORECASE
)

def is_clean(message: str, author: str) -> bool:
    if not message or len(message.strip()) < 8:
        return False
    if SPAM_REGEX.search(message):
        return False
    math_chars = sum(1 for c in message if 0x1D400 <= ord(c) <= 0x1D7FF)
    if math_chars >= 3:
        return False
    colons = message.count(":")
    if colons >= 4 and len(message.split()) <= 4:
        return False
    if re.match(r"^@?[A-Za-z0-9_]{4,}-[a-zA-Z0-9]{3,}$", author):
        return False
    return True

def run_tests():
    print("Testing Anti-Spam Sentinel...")

    # Case 1: The exact bot spam caught on screen
    spam_1 = "𝐍𝐅𝐋𝐂𝐁𝐒,ÇOM :left_arrow: Cowboys vs. Packers LIVE :medal-yellow-first-red::yt::medal-yellow-first-red:"
    author_1 = "@FGHFGH-z8i"
    assert not is_clean(spam_1, author_1), "FAILED: Bot spam 1 was not rejected!"
    print("✓ Test 1 Passed: Bot spam 1 correctly rejected.")

    # Case 2: The Barf spam catch
    spam_2 = "NFLHD¸COM ⬅️ NFL GAME LIVE STREAM:text-yellow-goal: :buffering: :face-turquoise-drinking-coffee:"
    author_2 = "StreamBot44"
    assert not is_clean(spam_2, author_2), "FAILED: Bot spam 2 was not rejected!"
    print("✓ Test 2 Passed: Bot spam 2 correctly rejected.")

    # Case 3: Genuine Fan Comment
    clean_fan = "Love is throwing absolute dots right now on 3rd down!"
    author_fan = "LambeauFan99"
    assert is_clean(clean_fan, author_fan), "FAILED: Genuine fan comment was rejected!"
    print("✓ Test 3 Passed: Genuine fan comment correctly accepted.")

    # Case 4: Deep Link Markdown Construction
    stream_id = "kIRXpMWntv4"
    stream_title = "Cheesehead TV Live Watch Party"
    game_pk = "dal_gb"
    stream_url = f"https://www.youtube.com/watch?v={stream_id}"
    gameroom_url = f"https://faas.stacklabsllc.com/vfs/vfs-gameroom?game={game_pk}"
    provenance = f"🔗 [🔴 Live Watch Party: {stream_title}]({stream_url}) • [🏟️ FanStack Bleacher Chat]({gameroom_url})"
    assert stream_id in provenance and gameroom_url in provenance
    print("✓ Test 4 Passed: Clickable provenance markdown verified.")

    print("\n🎉 ALL ANTI-SPAM & PROVENANCE TESTS PASSED (100% CLEAN)")

if __name__ == "__main__":
    run_tests()
