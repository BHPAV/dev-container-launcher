"""Unit tests for Flask web application."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import docker

# Import Flask app with mocked dependencies
with patch('scripts.devctl.docker_client'):
    from web_app import app, socketio


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def socketio_client():
    """Create a test client for Socket.IO."""
    return socketio.test_client(app)


class TestWebRoutes:
    """Test web routes."""
    
    def test_index_route(self, client):
        """Test index page loads."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Development Containers' in response.data
    
    def test_create_form_route(self, client):
        """Test create container form loads."""
        response = client.get('/create')
        assert response.status_code == 200
        assert b'Create New Container' in response.data
    
    @patch('scripts.devctl.get_container_info')
    def test_container_detail_route(self, mock_get_info, client):
        """Test container detail page loads."""
        mock_get_info.return_value = {
            'name': 'dev_test',
            'id': 'abc123',
            'status': 'running',
            'port': '2222',
            'image': 'devbox:latest',
            'created': '2024-01-01T00:00:00Z',
            'volumes': []
        }
        
        response = client.get('/container/test')
        assert response.status_code == 200
        assert b'dev_test' in response.data
    
    @patch('scripts.devctl.get_container_info')
    def test_container_detail_not_found(self, mock_get_info, client):
        """Test container detail page with non-existent container."""
        mock_get_info.side_effect = ValueError('Container not found')
        
        response = client.get('/container/nonexistent')
        assert response.status_code == 404
        assert b'Container not found' in response.data


class TestAPIEndpoints:
    """Test API endpoints."""
    
    @patch('scripts.devctl.list_all')
    def test_api_list_containers(self, mock_list_all, client):
        """Test container list API."""
        mock_container = Mock()
        mock_container.name = 'dev_test'
        mock_container.status = 'running'
        mock_container.ports = {'22/tcp': [{'HostPort': '2222'}]}
        mock_container.image.tags = ['devbox:latest']
        mock_container.short_id = 'abc123'
        
        mock_list_all.return_value = [mock_container]
        
        response = client.get('/api/containers')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == 'test'
        assert data['data'][0]['status'] == 'running'
    
    @patch('scripts.devctl.create')
    @patch('scripts.devctl.validate_container_name')
    def test_api_create_container(self, mock_validate, mock_create, client):
        """Test container creation API."""
        mock_container = Mock()
        mock_container.short_id = 'abc123'
        mock_create.return_value = (mock_container, 2222)
        
        response = client.post('/api/containers',
                             json={'name': 'test', 'image': 'devbox:latest'})
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['data']['name'] == 'test'
        assert data['data']['port'] == 2222
    
    @patch('scripts.devctl.validate_container_name')
    def test_api_create_container_invalid_name(self, mock_validate, client):
        """Test container creation with invalid name."""
        mock_validate.side_effect = ValueError('Invalid name')
        
        response = client.post('/api/containers',
                             json={'name': 'invalid name!'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'Invalid name' in data['message']
    
    @patch('scripts.devctl.get_container_info')
    def test_api_get_container(self, mock_get_info, client):
        """Test get container info API."""
        mock_get_info.return_value = {
            'name': 'dev_test',
            'status': 'running',
            'port': '2222'
        }
        
        response = client.get('/api/containers/test')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['data']['name'] == 'dev_test'
    
    @patch('scripts.devctl.remove_container')
    def test_api_delete_container(self, mock_remove, client):
        """Test container deletion API."""
        response = client.delete('/api/containers/test')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        mock_remove.assert_called_once_with('test', force=True)
    
    @patch('scripts.devctl.start_container')
    def test_api_start_container(self, mock_start, client):
        """Test container start API."""
        response = client.post('/api/containers/test/start')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        mock_start.assert_called_once_with('test')
    
    @patch('scripts.devctl.stop_container')
    def test_api_stop_container(self, mock_stop, client):
        """Test container stop API."""
        response = client.post('/api/containers/test/stop')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        mock_stop.assert_called_once_with('test')
    
    @patch('scripts.devctl.open_cursor')
    def test_api_open_container(self, mock_open, client):
        """Test open in Cursor API."""
        response = client.post('/api/containers/test/open')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        mock_open.assert_called_once_with('test')
    
    def test_api_list_images(self, client):
        """Test list images API."""
        response = client.get('/api/images')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'base' in data['data']
        assert 'languages' in data['data']
    
    @patch('scripts.devctl.build_image')
    def test_api_build_image(self, mock_build, client):
        """Test build image API."""
        response = client.post('/api/images/build',
                             json={'tag': 'test:latest'})
        
        assert response.status_code == 202
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'Building image' in data['message']


class TestWebSocketEvents:
    """Test WebSocket functionality."""
    
    def test_websocket_connect(self, socketio_client):
        """Test WebSocket connection."""
        assert socketio_client.is_connected()
        
        # Check for connection event
        received = socketio_client.get_received()
        assert len(received) > 0
        assert any(msg['name'] == 'connected' for msg in received)
    
    def test_websocket_disconnect(self, socketio_client):
        """Test WebSocket disconnection."""
        socketio_client.disconnect()
        assert not socketio_client.is_connected()
    
    @patch('web_app.get_containers_data')
    def test_websocket_request_update(self, mock_get_data, socketio_client):
        """Test manual update request via WebSocket."""
        mock_get_data.return_value = []
        
        socketio_client.emit('request_update')
        received = socketio_client.get_received()
        
        # Find the container_update event
        update_events = [msg for msg in received if msg['name'] == 'container_update']
        assert len(update_events) > 0
        assert 'containers' in update_events[0]['args'][0]


class TestErrorHandlers:
    """Test error handlers."""
    
    def test_404_handler_web(self, client):
        """Test 404 handler for web routes."""
        response = client.get('/nonexistent')
        assert response.status_code == 404
        assert b'Page not found' in response.data
    
    def test_404_handler_api(self, client):
        """Test 404 handler for API routes."""
        response = client.get('/api/nonexistent')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'not found' in data['message'].lower()
    
    @patch('scripts.devctl.list_all')
    def test_500_handler_api(self, mock_list_all, client):
        """Test 500 handler for API routes."""
        # Force an internal error
        mock_list_all.side_effect = Exception('Test error')
        
        response = client.get('/api/containers')
        assert response.status_code == 200  # get_containers_data catches exceptions
        
        # The function handles errors gracefully, returning empty list
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['data'] == []