#!/bin/bash
# test.sh - Test all error conditions

echo "Testing network error..."
sudo pfctl -e -f /dev/stdin <<< "block drop all" 2>/dev/null
python transcribe.py "https://instagram.com/reel/test"
sudo pfctl -d 2>/dev/null

echo "Testing invalid URL..."
python transcribe.py "not-a-url"

echo "Testing missing API key..."
mv .env .env.bak 2>/dev/null
python transcribe.py "https://instagram.com/reel/test"
mv .env.bak .env 2>/dev/null

echo "Testing rate limit..."
for i in {1..20}; do
    python transcribe.py "https://instagram.com/reel/test" &
done
wait