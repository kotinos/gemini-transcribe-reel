#!/usr/bin/env python3
"""
Minimal Reel Transcriber - Zero cost MVP
Usage: python transcribe.py <reel_url> [--debug]
"""

import sys
import os
import tempfile
import subprocess
import socket
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    import google.generativeai as genai
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install google-generativeai python-dotenv", file=sys.stderr)
    sys.exit(1)

# Global debug flag
DEBUG = False

def debug_print(message, **kwargs):
    """Print debug messages only if DEBUG is enabled"""
    if DEBUG:
        print(f"[DEBUG] {message}", **kwargs)

# Error codes
ERROR_INVALID_URL = 1
ERROR_DOWNLOAD = 2
ERROR_API_KEY = 3
ERROR_RATE_LIMIT = 4
ERROR_API = 5
ERROR_AUDIO = 6
ERROR_NETWORK = 7

def check_network():
    """Quick network connectivity check"""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except:
        return False

def validate_url(url):
    """Basic URL validation - just check if it's a URL"""
    # Add length limit to prevent DoS
    if len(url) > 2048:
        return False
    return url.startswith(('http://', 'https://')) and '.' in url

def check_dependencies():
    """Verify required tools are installed"""
    # Only need yt-dlp now, no FFmpeg required for video upload
    if subprocess.run(['which', 'yt-dlp'], capture_output=True).returncode != 0:
        print("ERROR: yt-dlp not installed. Install with: pip install yt-dlp", file=sys.stderr)
        sys.exit(ERROR_DOWNLOAD)

def download_reel(url, output_dir):
    try:
        result = subprocess.run(
            [
                'yt-dlp',
                '-P', output_dir,         # Download directly to the temp folder
                '--max-filesize', '200M',
                '--no-playlist',
                '--quiet',
                '--no-warnings',
                url
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        # Find any new video file created (by extension)
        videos = []
        for ext in ('mp4', 'mkv', 'webm', 'mov', 'flv'):
            videos.extend(Path(output_dir).glob(f'*.{ext}'))
        if not videos:
            debug_print(f"No video file found after download in {output_dir}", file=sys.stderr)
            return None
        debug_print(f"Downloaded files: {[str(v) for v in videos]}")
        return str(sorted(videos, key=lambda x: -x.stat().st_mtime)[0])  # Most recent
    except subprocess.TimeoutExpired:
        debug_print("yt-dlp timed out.", file=sys.stderr)
        return None
    except Exception as e:
        debug_print(f"Other download error: {e}", file=sys.stderr)
        return None

def transcribe_video(video_path):
    """Send video to Gemini API, wait for processing, then transcribe"""
    try:
        debug_print("Starting Gemini API call (video)...")
        size_mb = Path(video_path).stat().st_size / (1024 * 1024)
        debug_print(f"Video file size: {size_mb:.2f} MB")
        
        if size_mb > 20:
            print("ERROR: Video file too large for free tier (max 20MB)", file=sys.stderr)
            return None

        debug_print("Uploading video file to Gemini...")
        video_file = genai.upload_file(path=video_path)
        debug_print(f"File uploaded. File ID: {video_file.name}")
        
        # Wait for file to be processed
        debug_print("Waiting for file to be processed...")
        max_wait_time = 60  # Maximum 60 seconds
        wait_interval = 2   # Check every 2 seconds
        elapsed = 0
        
        while elapsed < max_wait_time:
            # Refresh file status
            file_info = genai.get_file(video_file.name)
            debug_print(f"File state: {file_info.state.name}")
            
            if file_info.state.name == 'ACTIVE':
                debug_print("File is now active!")
                break
            elif file_info.state.name == 'FAILED':
                print("ERROR: File processing failed", file=sys.stderr)
                return None
            
            debug_print(f"Still processing... ({elapsed}s elapsed)")
            time.sleep(wait_interval)
            elapsed += wait_interval
        
        if elapsed >= max_wait_time:
            print("ERROR: File processing timeout", file=sys.stderr)
            return None

        # Now generate content with the active file
        debug_print("Creating model...")
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = (
            "Transcribe all spoken words from this video. "
            "If there are visible captions or text overlays, include them as well. "
            "Output only the complete transcription text."
        )
        
        debug_print("Sending generation request...")
        response = model.generate_content([prompt, video_file])
        debug_print("Response received successfully")

        # Cleanup
        try:
            debug_print("Cleaning up uploaded file...")
            video_file.delete()
        except:
            pass

        if response and response.text:
            debug_print("Transcription successful")
            return response.text.strip()
        else:
            debug_print("No text in response")
            return None

    except Exception as e:
        debug_print(f"Exception type: {type(e).__name__}")
        debug_print(f"Full error message: {str(e)}")
        debug_print(f"Error repr: {repr(e)}")
        
        # Check if it has specific error attributes
        if hasattr(e, 'code'):
            debug_print(f"Error code: {e.code}")
        if hasattr(e, 'details'):
            debug_print(f"Error details: {e.details}")
        if hasattr(e, 'status_code'):
            debug_print(f"Status code: {e.status_code}")
            
        error_msg = str(e).lower()
        
        if any(word in error_msg for word in ['rate', 'quota', 'limit', '429']):
            debug_print(f"Detected rate limit in error: {str(e)}")
            print("ERROR: Gemini API rate limit (wait 1 minute)", file=sys.stderr)
            sys.exit(ERROR_RATE_LIMIT)
        elif any(word in error_msg for word in ['api', 'key', 'auth', '401', '403']):
            print("ERROR: Gemini API error - check your API key", file=sys.stderr)
            sys.exit(ERROR_API)
        else:
            print(f"ERROR: Unexpected Gemini error: {str(e)}", file=sys.stderr)
            return None

def check_available_models():
    """List available Gemini models"""
    try:
        debug_print("Available models:")
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                debug_print(f"  - {model.name}")
    except Exception as e:
        debug_print(f"Error listing models: {e}")

def main():
    global DEBUG
    
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <reel_url> [--debug]", file=sys.stderr)
        sys.exit(1)
    
    # Parse arguments
    args = sys.argv[1:]
    if '--debug' in args:
        DEBUG = True
        args.remove('--debug')
        debug_print("Debug mode enabled")
    
    if len(args) != 1:
        print("Usage: python transcribe.py <reel_url> [--debug]", file=sys.stderr)
        sys.exit(1)
    
    url = args[0]
    
    # Validate URL
    if not validate_url(url):
        print("ERROR: Invalid reel URL", file=sys.stderr)
        sys.exit(ERROR_INVALID_URL)
    
    # Check network
    if not check_network():
        print("ERROR: No internet connection", file=sys.stderr)
        sys.exit(ERROR_NETWORK)
    
    # Check dependencies
    check_dependencies()
    
    # Load and check API key
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env file", file=sys.stderr)
        sys.exit(ERROR_API_KEY)
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # List available Gemini models for debugging
    if DEBUG:
        check_available_models()
    
    # Process video
    with tempfile.TemporaryDirectory(prefix='reel_') as temp_dir:
        # Download
        video_path = download_reel(url, temp_dir)
        debug_print(f"Downloaded video: {video_path}")
        if video_path:
            debug_print(f"Exists: {Path(video_path).exists()}, Size: {Path(video_path).stat().st_size} bytes")
        if not video_path:
            print("ERROR: Could not download reel (check URL or network)", file=sys.stderr)
            sys.exit(ERROR_DOWNLOAD)
        
        # Transcribe video directly (no audio extraction needed)
        transcription = transcribe_video(video_path)
        if transcription:
            print(transcription)
        else:
            print("ERROR: Could not transcribe video", file=sys.stderr)
            sys.exit(ERROR_API)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error", file=sys.stderr)
        sys.exit(1)