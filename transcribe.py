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
    return url.startswith(('http://', 'https://')) and '.' in url

def check_dependencies():
    """Verify required tools are installed"""
    for cmd, install in [('yt-dlp', 'pip install yt-dlp'), ('ffmpeg', 'brew install ffmpeg')]:
        if subprocess.run(['which', cmd], capture_output=True).returncode != 0:
            print(f"ERROR: {cmd} not installed. Install with: {install}", file=sys.stderr)
            sys.exit(ERROR_DOWNLOAD if cmd == 'yt-dlp' else ERROR_AUDIO)

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

def extract_audio(video_path, audio_path):
    """Extract audio as WAV for better compatibility"""
    debug_print(f"Video path: '{video_path}'")
    debug_print(f"Audio path: '{audio_path}'")
    debug_print(f"Video exists: {Path(video_path).exists()}")
    
    try:
        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # No video
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            '-f', 'wav',  # WAV format
            '-y',  # Overwrite
            audio_path
        ]
        
        debug_print(f"Running command: {' '.join(cmd)}")
        
        # Run FFmpeg with error output visible
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,  # Get text output instead of bytes
            timeout=30
        )
        
        debug_print(f"FFmpeg return code: {result.returncode}")
        
        if result.stdout:
            debug_print(f"FFmpeg stdout:\n{result.stdout}")
        
        if result.stderr:
            debug_print(f"FFmpeg stderr:\n{result.stderr}")
        
        # Check if output file was created
        audio_exists = Path(audio_path).exists()
        debug_print(f"Audio file created: {audio_exists}")
        
        if audio_exists:
            size = Path(audio_path).stat().st_size
            debug_print(f"Audio file size: {size} bytes ({size/(1024*1024):.2f} MB)")
            
            # Check if file is too large
            if size > 20 * 1024 * 1024:  # 20MB
                print("ERROR: Audio file too large for free tier", file=sys.stderr)
                return False
            
            return True
        else:
            debug_print(f"Audio file not created at: {audio_path}")
            return False
        
    except subprocess.TimeoutExpired:
        debug_print("FFmpeg command timed out", file=sys.stderr)
        return False
    except Exception as e:
        debug_print(f"Exception in extract_audio: {e}", file=sys.stderr)
        return False

def transcribe_audio(audio_path):
    """Send audio to Gemini API, return transcription or None"""
    try:
        debug_print("Starting Gemini API call...")
        debug_print(f"Audio file size: {Path(audio_path).stat().st_size / (1024*1024):.2f} MB")
        
        # Upload and transcribe
        debug_print("Uploading file to Gemini...")
        audio_file = genai.upload_file(path=audio_path)
        debug_print(f"File uploaded successfully. File ID: {audio_file.name}")
        
        debug_print("Creating model...")
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        debug_print("Sending generation request...")
        prompt = "Transcribe this audio. Output only the transcribed speech text. Use the onscreen captions for assistance if available."
        response = model.generate_content([prompt, audio_file])
        
        debug_print("Response received successfully")
        
        # Cleanup
        try:
            debug_print("Cleaning up uploaded file...")
            audio_file.delete()
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
        print(f"Downloaded video: {video_path}")
        if video_path:
            print("Exists:", Path(video_path).exists(), "Size:", Path(video_path).stat().st_size)
        if not video_path:
            print("ERROR: Could not download reel (check URL or network)", file=sys.stderr)
            sys.exit(ERROR_DOWNLOAD)
        
        # Extract audio
        audio_path = str(Path(temp_dir) / 'audio.wav')
        if not extract_audio(video_path, audio_path):
            print("ERROR: Could not process audio from video", file=sys.stderr)
            sys.exit(ERROR_AUDIO)
        
        # Transcribe
        transcription = transcribe_audio(audio_path)
        if transcription:
            print(transcription)
        else:
            print("ERROR: Could not transcribe audio", file=sys.stderr)
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