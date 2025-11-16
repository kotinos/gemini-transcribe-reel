#!/usr/bin/env python3
"""
Minimal web UI for Gemini Transcribe Reel
Flask backend for single-purpose video transcription
"""

import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# Import functions from the main transcribe module
import transcribe

app = Flask(__name__)

# Load environment variables
load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

if api_key:
    genai.configure(api_key=api_key)

@app.route('/')
def index():
    """Serve the minimal UI"""
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe_endpoint():
    """Handle transcription requests (single or batch)"""
    import time
    
    data = request.get_json()
    urls = data.get('urls', [])
    
    # Support legacy single URL format
    if not urls and 'url' in data:
        urls = [data['url'].strip()]
    
    if not urls:
        return jsonify({
            'success': False,
            'error': 'ERROR: No URLs provided'
        }), 400
    
    # Check for API key
    if not api_key:
        return jsonify({
            'success': False,
            'error': 'ERROR: GEMINI_API_KEY not found in .env file'
        }), 500
    
    # Check network
    if not transcribe.check_network():
        return jsonify({
            'success': False,
            'error': 'ERROR: No internet connection'
        }), 503
    
    # Check dependencies
    try:
        transcribe.check_dependencies()
    except SystemExit:
        return jsonify({
            'success': False,
            'error': 'ERROR: yt-dlp not installed. Server misconfiguration.'
        }), 500
    
    # Process URLs
    results = []
    total = len(urls)
    
    for i, url in enumerate(urls, 1):
        # Validate URL
        if not transcribe.validate_url(url):
            results.append({
                'url': url,
                'success': False,
                'transcription': None,
                'error': 'Invalid URL format'
            })
            continue
        
        # Process the URL
        result = transcribe.process_url(url, i, total)
        
        results.append({
            'url': url,
            'success': result is not None,
            'transcription': result,
            'error': None if result else 'Transcription failed'
        })
        
        # Rate limiting between requests (except for last one)
        if i < total:
            time.sleep(4)  # Free tier: 15 requests/minute
    
    # Return appropriate response
    if len(urls) == 1:
        # Single URL - return simple format
        if results[0]['success']:
            return jsonify({
                'success': True,
                'transcription': results[0]['transcription']
            })
        else:
            return jsonify({
                'success': False,
                'error': f"ERROR: {results[0]['error']}"
            }), 500
    else:
        # Batch - return all results
        return jsonify({
            'success': True,
            'results': results
        })

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
