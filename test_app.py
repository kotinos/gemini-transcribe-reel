#!/usr/bin/env python3
"""
Unit tests for app.py Flask routes
Run with: python -m pytest test_app.py -v
"""

import json
from unittest.mock import patch, Mock
import pytest

import app as flask_app


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    flask_app.app.config['TESTING'] = True
    with flask_app.app.test_client() as client:
        yield client


class TestTranscribeEndpointStatusCodes:
    """Test HTTP status codes returned by /transcribe"""

    def test_no_urls_returns_400(self, client):
        """POST with empty urls list returns 400"""
        response = client.post('/transcribe',
                               data=json.dumps({'urls': []}),
                               content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'No URLs provided' in data['error']

    def test_no_body_urls_returns_400(self, client):
        """POST with no urls or url key returns 400"""
        response = client.post('/transcribe',
                               data=json.dumps({}),
                               content_type='application/json')
        assert response.status_code == 400

    @patch.object(flask_app, 'api_key', None)
    def test_missing_api_key_returns_500(self, client):
        """POST with missing API key returns 500"""
        response = client.post('/transcribe',
                               data=json.dumps({'urls': ['https://example.com/video']}),
                               content_type='application/json')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'GEMINI_API_KEY' in data['error']

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    def test_no_network_returns_503(self, mock_network, client):
        """POST with no network returns 503"""
        mock_network.return_value = False
        response = client.post('/transcribe',
                               data=json.dumps({'urls': ['https://example.com/video']}),
                               content_type='application/json')
        assert response.status_code == 503
        data = response.get_json()
        assert data['success'] is False
        assert 'No internet connection' in data['error']

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    def test_dependency_error_returns_500(self, mock_deps, mock_network, client):
        """POST with missing dependency returns 500"""
        mock_network.return_value = True
        mock_deps.side_effect = SystemExit(2)
        response = client.post('/transcribe',
                               data=json.dumps({'urls': ['https://example.com/video']}),
                               content_type='application/json')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'yt-dlp' in data['error']

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.process_url')
    def test_transcription_failure_returns_500(self, mock_process, mock_deps,
                                               mock_network, client):
        """POST with transcription failure on single URL returns 500"""
        mock_network.return_value = True
        mock_process.return_value = None
        response = client.post('/transcribe',
                               data=json.dumps({'urls': ['https://example.com/video']}),
                               content_type='application/json')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data


class TestTranscribeEndpointResponseShapes:
    """Test JSON response shapes for single and batch"""

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.process_url')
    def test_single_url_success_shape(self, mock_process, mock_deps,
                                      mock_network, client):
        """Single URL success returns {success, transcription}"""
        mock_network.return_value = True
        mock_process.return_value = "Hello world transcription"
        response = client.post('/transcribe',
                               data=json.dumps({'urls': ['https://example.com/video']}),
                               content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data == {'success': True, 'transcription': 'Hello world transcription'}

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.process_url')
    def test_single_url_failure_shape(self, mock_process, mock_deps,
                                      mock_network, client):
        """Single URL failure returns {success, error} with 500"""
        mock_network.return_value = True
        mock_process.return_value = None
        response = client.post('/transcribe',
                               data=json.dumps({'urls': ['https://example.com/video']}),
                               content_type='application/json')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data
        assert 'transcription' not in data

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.process_url')
    @patch('time.sleep')
    def test_batch_response_shape(self, mock_sleep, mock_process, mock_deps,
                                   mock_network, client):
        """Batch returns {success, results: [{url, success, transcription, error}]}"""
        mock_network.return_value = True
        mock_process.side_effect = ["Result 1", None]
        response = client.post('/transcribe',
                               data=json.dumps({'urls': [
                                   'https://example.com/video1',
                                   'https://example.com/video2'
                               ]}),
                               content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'results' in data
        assert len(data['results']) == 2
        # First result: success
        r1 = data['results'][0]
        assert r1['url'] == 'https://example.com/video1'
        assert r1['success'] is True
        assert r1['transcription'] == 'Result 1'
        assert r1['error'] is None
        # Second result: failure
        r2 = data['results'][1]
        assert r2['url'] == 'https://example.com/video2'
        assert r2['success'] is False
        assert r2['transcription'] is None
        assert r2['error'] == 'Transcription failed'

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.process_url')
    def test_legacy_single_url_format(self, mock_process, mock_deps,
                                      mock_network, client):
        """Legacy {url: "..."} format works for single URL"""
        mock_network.return_value = True
        mock_process.return_value = "Legacy result"
        response = client.post('/transcribe',
                               data=json.dumps({'url': 'https://example.com/video'}),
                               content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['transcription'] == 'Legacy result'

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    def test_invalid_url_in_batch(self, mock_deps, mock_network, client):
        """Invalid URL in batch is recorded as error, not rejected"""
        mock_network.return_value = True
        response = client.post('/transcribe',
                               data=json.dumps({'urls': ['not-a-url']}),
                               content_type='application/json')
        # Single invalid URL returns 500
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
