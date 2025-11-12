# Reel Transcriber - Zero Cost MVP

A dead-simple command-line tool that transcribes Instagram/TikTok/Facebook Reels using the free Gemini API.

## Quick Setup (2 minutes)

1. **Install FFmpeg:**
   ```bash
   brew install ffmpeg
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Get free Gemini API key:**
   - Visit: https://makersuite.google.com/app/apikey
   - Create a new API key (free tier: 15 requests/minute, 1,500/day)

4. **Create .env file:**
   ```bash
   echo "GEMINI_API_KEY=your_key_here" > .env
   ```

## Usage

```bash
python transcribe.py "https://instagram.com/reel/xyz"
```

**Success output:**
```
Hey everyone, today I'm showing you how to make perfect coffee at home.
```

**Error output (to stderr):**
```
ERROR: Invalid reel URL
```

## Supported Platforms

- Instagram Reels
- TikTok Videos
- Facebook Videos

## Error Codes

| Exit Code | Error Type | Message |
|-----------|------------|---------|
| 0 | Success | *(transcription text)* |
| 1 | Invalid URL | `ERROR: Invalid reel URL` |
| 2 | Download Failed | `ERROR: Could not download reel (check URL or network)` |
| 3 | API Key Missing | `ERROR: GEMINI_API_KEY not found in .env file` |
| 4 | API Limit | `ERROR: Gemini API rate limit (wait 1 minute)` |
| 5 | API Error | `ERROR: Gemini API error - check your API key` |
| 6 | Audio Error | `ERROR: Could not process audio from video` |
| 7 | Network Error | `ERROR: No internet connection` |

## Troubleshooting

- **Error code 1-7:** See error message for specific fix
- **Rate limited?** Wait 60 seconds (free tier = 15 requests/minute)
- **No output?** Check stderr for errors: `python transcribe.py "url" 2>&1`
- **yt-dlp errors?** Update with: `pip install -U yt-dlp`

## Free Tier Limits (Gemini)

- 15 requests per minute
- 1 million tokens per minute
- 1,500 requests per day
- Perfect for personal use and testing

## Examples

**Basic usage:**
```bash
python transcribe.py "https://www.instagram.com/reel/C123456/"
```

**Pipe to file:**
```bash
python transcribe.py "https://www.instagram.com/reel/C123456/" > transcription.txt
```

**Check exit code:**
```bash
python transcribe.py "https://www.instagram.com/reel/C123456/"
echo $?
```

## Technical Details

- **Processing:** Download → Extract Audio → Transcribe → Cleanup
- **Temp files:** Automatically cleaned up after processing
- **Output:** Plain text only (pipe-friendly)
- **Errors:** Sent to stderr with appropriate exit codes
