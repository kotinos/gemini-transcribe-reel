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
import db

app = Flask(__name__)

# Load environment variables
load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

if api_key:
    genai.configure(api_key=api_key)

# Initialize database
try:
    db.init_db()
except Exception:
    pass

@app.route('/')
def index():
    """Serve the minimal UI"""
    return render_template('index.html')

@app.route('/models')
def models_endpoint():
    """Return available Gemini models"""
    try:
        if not api_key:
            return jsonify({'models': [transcribe.DEFAULT_MODEL]})
        models = transcribe.check_available_models()
        return jsonify({'models': models})
    except Exception:
        return jsonify({'models': [transcribe.DEFAULT_MODEL]})

@app.route('/transcribe', methods=['POST'])
def transcribe_endpoint():
    """Handle transcription requests (single or batch)"""
    import time
    
    data = request.get_json()
    urls = data.get('urls', [])
    model = data.get('model', transcribe.DEFAULT_MODEL)
    
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
        result = transcribe.process_url(url, i, total, model_name=model)
        
        results.append({
            'url': url,
            'success': result is not None,
            'transcription': result,
            'error': None if result else 'Transcription failed'
        })

        # Auto-save successful transcriptions
        if result is not None:
            try:
                db.save_script(url, result)
            except Exception:
                pass
        
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


@app.route('/scripts')
def get_scripts():
    """Return all saved scripts"""
    scripts = db.get_all_scripts()
    return jsonify(scripts)


@app.route('/scripts/<int:script_id>')
def get_script(script_id):
    """Return a single script by ID"""
    script = db.get_script(script_id)
    if script is None:
        return jsonify({'error': 'Script not found'}), 404
    return jsonify(script)


@app.route('/scripts/<int:script_id>', methods=['PUT'])
def update_script(script_id):
    """Update a script's transcription"""
    data = request.get_json()
    transcription = data.get('transcription') if data else None
    if not transcription:
        return jsonify({'error': 'Missing transcription'}), 400
    updated = db.update_script(script_id, transcription)
    if updated is None:
        return jsonify({'error': 'Script not found'}), 404
    return jsonify(updated)


@app.route('/scripts/<int:script_id>', methods=['DELETE'])
def delete_script(script_id):
    """Delete a script by ID"""
    if db.delete_script(script_id):
        return '', 204
    return jsonify({'error': 'Script not found'}), 404


@app.route('/regenerate', methods=['POST'])
def regenerate_endpoint():
    """Re-run transcription for a single URL"""
    data = request.get_json()
    url = data.get('url', '').strip() if data else ''

    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    if not transcribe.validate_url(url):
        return jsonify({'success': False, 'error': 'Invalid URL'}), 400

    if not api_key:
        return jsonify({
            'success': False,
            'error': 'ERROR: GEMINI_API_KEY not found in .env file'
        }), 500

    if not transcribe.check_network():
        return jsonify({
            'success': False,
            'error': 'ERROR: No internet connection'
        }), 503

    try:
        transcribe.check_dependencies()
    except SystemExit:
        return jsonify({
            'success': False,
            'error': 'ERROR: yt-dlp not installed. Server misconfiguration.'
        }), 500

    model = data.get('model', transcribe.DEFAULT_MODEL)
    result = transcribe.process_url(url, model_name=model)

    if result is not None:
        try:
            db.save_script(url, result)
        except Exception:
            pass
        return jsonify({'success': True, 'transcription': result})
    else:
        return jsonify({
            'success': False,
            'error': 'Transcription failed'
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
