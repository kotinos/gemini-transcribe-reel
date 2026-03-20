# Product Vision

## Overview

Reel Transcriber is a dead-simple, zero-cost tool that transcribes video content from Instagram Reels, TikTok videos, and Facebook videos using Google's free Gemini API.

## Target Users

- **Content creators & social media managers** who need quick transcriptions of short-form video
- **Accessibility advocates** adding captions or text versions of video content
- **Casual users** who want free, frictionless transcription without accounts or payments
- **Developers** who need a working example of the Gemini file-upload and transcription API

## Key Features

- **Dual interface** — CLI for scripting/automation, web UI for quick manual use
- **Batch processing** — Transcribe multiple URLs in one invocation (CLI args, file input, or web UI textarea)
- **Multi-platform video support** — Instagram Reels, TikTok, Facebook videos via yt-dlp
- **Automatic video compression** — Videos over 20 MB are compressed with FFmpeg to fit Gemini's upload limit
- **Structured error codes** — Seven specific exit codes (1–7) for easy scripting and debugging
- **Free-tier optimized** — Built-in 4-second rate-limiting delays respect the Gemini free tier (15 req/min)
- **Cross-platform** — Works on Windows, macOS, and Linux with dedicated setup guides

## Supported Platforms

| Platform       | URL Pattern                          |
|----------------|--------------------------------------|
| Instagram Reel | `https://www.instagram.com/reel/...` |
| TikTok Video   | `https://www.tiktok.com/@.../video/...` |
| Facebook Video | `https://www.facebook.com/.../videos/...` |

## Business Objectives

1. **Zero cost** — No paid APIs, no hosting fees, no subscriptions. The entire stack runs on free-tier services and local execution.
2. **Minimal friction** — A user should go from clone → first transcription in under 5 minutes.
3. **Reliability** — Every failure mode has a clear, actionable error code. No silent failures.
4. **Privacy** — No user accounts, no data persistence, no analytics. Videos are downloaded to temp files and deleted after processing.

## User Workflows

### CLI (primary)

```
python transcribe.py "https://instagram.com/reel/xyz"          # single
python transcribe.py url1 url2 url3                             # batch
python transcribe.py --file urls.txt                            # from file
```

### Web UI

```
python app.py        # start server on http://127.0.0.1:5000
```

Paste one or more URLs, click Transcribe, get results in the browser.

## Error Code Contract

| Code | Meaning          | User Action                        |
|------|------------------|------------------------------------|
| 0    | Success          | —                                  |
| 1    | Invalid URL      | Check URL format                   |
| 2    | Download failed  | Verify URL is public and accessible |
| 3    | Missing API key  | Create `.env` with `GEMINI_API_KEY` |
| 4    | Rate limit       | Wait 60 seconds and retry          |
| 5    | API error        | Verify API key is valid            |
| 6    | Audio error      | Video may have no audio track      |
| 7    | Network error    | Check internet connection          |

## Non-Goals

- User accounts or authentication
- Persistent storage or transcription history
- Paid API tier support or billing management
- Video editing or caption embedding
- Real-time / streaming transcription
