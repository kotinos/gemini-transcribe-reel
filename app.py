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
    """Handle transcription requests"""
    data = request.get_json()
    url = data.get('url', '').strip()
    
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
    
    # Validate URL
    if not transcribe.validate_url(url):
        return jsonify({
            'success': False,
            'error': 'ERROR: Invalid URL format. Must be http:// or https:// from Instagram, TikTok, or Facebook.'
        }), 400
    
    # Check dependencies
    try:
        transcribe.check_dependencies()
    except SystemExit:
        return jsonify({
            'success': False,
            'error': 'ERROR: yt-dlp not installed. Server misconfiguration.'
        }), 500
    
    # Process the URL
    result = transcribe.process_url(url)
    
    if result:
        return jsonify({
            'success': True,
            'transcription': result
        })
    else:
        return jsonify({
            'success': False,
            'error': 'ERROR: Could not transcribe video. Check URL or try again later.'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
