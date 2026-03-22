#!/usr/bin/env python3
"""
Unit tests for app.py Flask routes
Run with: python -m pytest test_app.py -v
"""

import json
from unittest.mock import patch, Mock
import pytest

import app as flask_app
import db
import transcribe


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    flask_app.app.config['TESTING'] = True
    with flask_app.app.test_client() as client:
        yield client


@pytest.fixture
def db_client(tmp_path):
    """Create a test client with a temporary database"""
    test_db = str(tmp_path / "test.db")
    db.init_db(test_db)
    db.DB_PATH = test_db
    flask_app.app.config['TESTING'] = True
    with flask_app.app.test_client() as client:
        yield client
    db.DB_PATH = 'scripts.db'


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


class TestModelsEndpoint:
    """Test GET /models endpoint"""

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_available_models')
    def test_get_models_success(self, mock_models, client):
        """GET /models returns list of models"""
        mock_models.return_value = ['gemini-2.5-flash', 'gemini-2.0-flash']
        response = client.get('/models')
        assert response.status_code == 200
        data = response.get_json()
        assert data['models'] == ['gemini-2.5-flash', 'gemini-2.0-flash']

    @patch.object(flask_app, 'api_key', None)
    def test_get_models_no_api_key(self, client):
        """GET /models returns default model when no API key"""
        response = client.get('/models')
        assert response.status_code == 200
        data = response.get_json()
        assert data['models'] == [transcribe.DEFAULT_MODEL]

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.process_url')
    def test_transcribe_with_model(self, mock_process, mock_deps,
                                    mock_network, client):
        """POST /transcribe with model passes it through"""
        mock_network.return_value = True
        mock_process.return_value = "Result"
        response = client.post('/transcribe',
                               data=json.dumps({'urls': ['https://example.com/video'],
                                                'model': 'gemini-2.0-flash'}),
                               content_type='application/json')
        assert response.status_code == 200
        mock_process.assert_called_once()
        _, kwargs = mock_process.call_args
        assert kwargs.get('model_name') == 'gemini-2.0-flash'

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.process_url')
    def test_transcribe_without_model(self, mock_process, mock_deps,
                                      mock_network, client):
        """POST /transcribe without model uses default"""
        mock_network.return_value = True
        mock_process.return_value = "Result"
        response = client.post('/transcribe',
                               data=json.dumps({'urls': ['https://example.com/video']}),
                               content_type='application/json')
        assert response.status_code == 200
        mock_process.assert_called_once()
        _, kwargs = mock_process.call_args
        assert kwargs.get('model_name') == transcribe.DEFAULT_MODEL


class TestScriptsEndpoints:
    """Test CRUD routes for /scripts"""

    def test_get_scripts_empty(self, db_client):
        """GET /scripts returns empty list when no records"""
        response = db_client.get('/scripts')
        assert response.status_code == 200
        assert response.get_json() == []

    def test_get_scripts_with_data(self, db_client):
        """GET /scripts returns records in descending order"""
        db.save_script('https://example.com/1', 'First')
        db.save_script('https://example.com/2', 'Second')
        response = db_client.get('/scripts')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        assert data[0]['url'] == 'https://example.com/2'

    def test_get_script_by_id(self, db_client):
        """GET /scripts/<id> returns the correct record"""
        saved = db.save_script('https://example.com/video', 'Content')
        response = db_client.get(f'/scripts/{saved["id"]}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['transcription'] == 'Content'

    def test_get_script_not_found(self, db_client):
        """GET /scripts/<id> returns 404 for nonexistent ID"""
        response = db_client.get('/scripts/999')
        assert response.status_code == 404

    def test_update_script_success(self, db_client):
        """PUT /scripts/<id> updates the transcription"""
        saved = db.save_script('https://example.com/video', 'Original')
        response = db_client.put(f'/scripts/{saved["id"]}',
                                  data=json.dumps({'transcription': 'Edited'}),
                                  content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['transcription'] == 'Edited'

    def test_update_script_no_body(self, db_client):
        """PUT /scripts/<id> returns 400 when transcription is missing"""
        saved = db.save_script('https://example.com/video', 'Original')
        response = db_client.put(f'/scripts/{saved["id"]}',
                                  data=json.dumps({}),
                                  content_type='application/json')
        assert response.status_code == 400

    def test_update_script_not_found(self, db_client):
        """PUT /scripts/<id> returns 404 for nonexistent ID"""
        response = db_client.put('/scripts/999',
                                  data=json.dumps({'transcription': 'Text'}),
                                  content_type='application/json')
        assert response.status_code == 404

    def test_delete_script_success(self, db_client):
        """DELETE /scripts/<id> removes the record"""
        saved = db.save_script('https://example.com/video', 'Content')
        response = db_client.delete(f'/scripts/{saved["id"]}')
        assert response.status_code == 204

    def test_delete_script_not_found(self, db_client):
        """DELETE /scripts/<id> returns 404 for nonexistent ID"""
        response = db_client.delete('/scripts/999')
        assert response.status_code == 404

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.process_url')
    def test_transcribe_auto_saves(self, mock_process, mock_deps,
                                    mock_network, db_client):
        """POST /transcribe auto-saves successful results to database"""
        mock_network.return_value = True
        mock_process.return_value = "Auto saved result"
        response = db_client.post('/transcribe',
                                   data=json.dumps({'urls': ['https://example.com/video']}),
                                   content_type='application/json')
        assert response.status_code == 200
        scripts = db.get_all_scripts()
        assert len(scripts) == 1
        assert scripts[0]['transcription'] == 'Auto saved result'


class TestRegenerateEndpoint:
    """Test POST /regenerate endpoint"""

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.process_url')
    def test_regenerate_success(self, mock_process, mock_deps,
                                 mock_network, client):
        """POST /regenerate returns successful transcription"""
        mock_network.return_value = True
        mock_process.return_value = "Regenerated text"
        response = client.post('/regenerate',
                               data=json.dumps({'url': 'https://example.com/video'}),
                               content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['transcription'] == 'Regenerated text'

    def test_regenerate_no_url(self, client):
        """POST /regenerate returns 400 when url is missing"""
        response = client.post('/regenerate',
                               data=json.dumps({}),
                               content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_regenerate_invalid_url(self, client):
        """POST /regenerate returns 400 for invalid URL"""
        response = client.post('/regenerate',
                               data=json.dumps({'url': 'not-a-url'}),
                               content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    @patch.object(flask_app, 'api_key', None)
    def test_regenerate_missing_api_key(self, client):
        """POST /regenerate returns 500 when API key missing"""
        response = client.post('/regenerate',
                               data=json.dumps({'url': 'https://example.com/video'}),
                               content_type='application/json')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    def test_regenerate_no_network(self, mock_network, client):
        """POST /regenerate returns 503 when no network"""
        mock_network.return_value = False
        response = client.post('/regenerate',
                               data=json.dumps({'url': 'https://example.com/video'}),
                               content_type='application/json')
        assert response.status_code == 503

    @patch.object(flask_app, 'api_key', 'test_key')
    @patch('transcribe.check_network')
    @patch('transcribe.check_dependencies')
    @patch('transcribe.process_url')
    def test_regenerate_transcription_failure(self, mock_process, mock_deps,
                                              mock_network, client):
        """POST /regenerate returns 500 when transcription fails"""
        mock_network.return_value = True
        mock_process.return_value = None
        response = client.post('/regenerate',
                               data=json.dumps({'url': 'https://example.com/video'}),
                               content_type='application/json')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
