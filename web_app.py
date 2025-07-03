#!/usr/bin/env python3
"""Flask web application for dev-container management."""

from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging
from pathlib import Path
import json
from threading import Thread
import time
import os
import sys

from scripts import devctl
import config
from config import CONTAINER_PREFIX, IMAGE_TAG, LANGUAGE_IMAGES
from utils import validate_container_name, logger

# Flask app configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-container-secret-key'  # Change in production
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Configure logging for Flask
logging.getLogger('werkzeug').setLevel(logging.WARNING)


# Background thread for container monitoring
def background_monitor():
    """Monitor container status changes and emit updates."""
    last_state = {}
    while True:
        try:
            containers = devctl.list_all()
            current_state = {c.name: c.status for c in containers}
            
            # Check for changes
            if current_state != last_state:
                socketio.emit('container_update', {
                    'containers': get_containers_data()
                })
                last_state = current_state
                
        except Exception as e:
            logger.error(f"Background monitor error: {e}")
        
        time.sleep(2)  # Check every 2 seconds


# Helper functions
def get_containers_data():
    """Get formatted container data for API responses."""
    containers = []
    try:
        for c in devctl.list_all():
            port = "N/A"
            if "22/tcp" in c.ports and c.ports["22/tcp"]:
                port = c.ports["22/tcp"][0]["HostPort"]
            
            containers.append({
                'name': c.name.replace(CONTAINER_PREFIX, ""),
                'status': c.status,
                'port': port,
                'image': c.image.tags[0] if c.image.tags else c.image.short_id,
                'id': c.short_id
            })
    except Exception as e:
        logger.error(f"Error getting containers: {e}")
    
    return containers


# Web Routes
@app.route('/')
def index():
    """Main container list view."""
    return render_template('index.html')


@app.route('/create')
def create_form():
    """Container creation form."""
    return render_template('create_container.html', 
                         default_image=IMAGE_TAG,
                         language_images=LANGUAGE_IMAGES)


@app.route('/container/<name>')
def container_detail(name):
    """Container detail view."""
    try:
        info = devctl.get_container_info(name)
        return render_template('container_detail.html', 
                             name=name, 
                             info=info)
    except ValueError as e:
        return render_template('error.html', error=str(e)), 404


# API Routes
@app.route('/api/containers', methods=['GET'])
def api_list_containers():
    """List all containers."""
    return jsonify({
        'status': 'success',
        'data': get_containers_data()
    })


@app.route('/api/containers', methods=['POST'])
def api_create_container():
    """Create a new container."""
    try:
        data = request.get_json()
        name = data.get('name')
        image = data.get('image', IMAGE_TAG)
        volume = data.get('volume')
        
        # Validate inputs
        validate_container_name(name)
        
        # Create container
        volume_path = Path(volume) if volume else None
        container, port = devctl.create(name, image=image, volume=volume_path)
        
        # Emit update via WebSocket
        socketio.emit('container_created', {
            'name': name,
            'port': port
        })
        
        return jsonify({
            'status': 'success',
            'data': {
                'name': name,
                'port': port,
                'id': container.short_id
            }
        }), 201
        
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error creating container: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to create container: {str(e)}"
        }), 500


@app.route('/api/containers/<name>', methods=['GET'])
def api_get_container(name):
    """Get container details."""
    try:
        info = devctl.get_container_info(name)
        return jsonify({
            'status': 'success',
            'data': info
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error getting container info: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to get container info: {str(e)}"
        }), 500


@app.route('/api/containers/<name>', methods=['DELETE'])
def api_delete_container(name):
    """Delete a container."""
    try:
        force = request.args.get('force', 'true').lower() == 'true'
        devctl.remove_container(name, force=force)
        
        # Emit update via WebSocket
        socketio.emit('container_deleted', {'name': name})
        
        return jsonify({
            'status': 'success',
            'message': f'Container {name} deleted'
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error deleting container: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to delete container: {str(e)}"
        }), 500


@app.route('/api/containers/<name>/start', methods=['POST'])
def api_start_container(name):
    """Start a container."""
    try:
        devctl.start_container(name)
        
        # Emit update via WebSocket
        socketio.emit('container_started', {'name': name})
        
        return jsonify({
            'status': 'success',
            'message': f'Container {name} started'
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error starting container: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to start container: {str(e)}"
        }), 500


@app.route('/api/containers/<name>/stop', methods=['POST'])
def api_stop_container(name):
    """Stop a container."""
    try:
        devctl.stop_container(name)
        
        # Emit update via WebSocket
        socketio.emit('container_stopped', {'name': name})
        
        return jsonify({
            'status': 'success',
            'message': f'Container {name} stopped'
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error stopping container: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to stop container: {str(e)}"
        }), 500


@app.route('/api/containers/<name>/open', methods=['POST'])
def api_open_container(name):
    """Open container in Cursor."""
    try:
        devctl.open_cursor(name)
        return jsonify({
            'status': 'success',
            'message': f'Opening {name} in Cursor'
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error opening container: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to open container: {str(e)}"
        }), 500


@app.route('/api/images', methods=['GET'])
def api_list_images():
    """List available images."""
    images = {
        'base': IMAGE_TAG,
        'languages': LANGUAGE_IMAGES
    }
    return jsonify({
        'status': 'success',
        'data': images
    })


@app.route('/api/images/build', methods=['POST'])
def api_build_image():
    """Build a Docker image."""
    try:
        data = request.get_json()
        tag = data.get('tag', IMAGE_TAG)
        dockerfile = data.get('dockerfile', 'docker/Dockerfile')
        
        # Run build in background thread
        def build_async():
            try:
                devctl.build_image(tag=tag, dockerfile=dockerfile)
                socketio.emit('image_built', {'tag': tag})
            except Exception as e:
                socketio.emit('build_error', {'error': str(e)})
        
        thread = Thread(target=build_async)
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': f'Building image {tag}'
        }), 202
        
    except Exception as e:
        logger.error(f"Error building image: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to build image: {str(e)}"
        }), 500


# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info('Client connected')
    emit('connected', {'data': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info('Client disconnected')


@socketio.on('request_update')
def handle_update_request():
    """Handle manual update request."""
    emit('container_update', {
        'containers': get_containers_data()
    })


# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error',
            'message': 'Resource not found'
        }), 404
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal error: {error}")
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500
    return render_template('error.html', error='Internal server error'), 500


if __name__ == '__main__':
    # Start background monitoring thread
    monitor_thread = Thread(target=background_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Get port from config or environment
    port = int(os.environ.get('FLASK_PORT', config.FLASK_PORT))
    host = os.environ.get('FLASK_HOST', config.FLASK_HOST)
    debug = os.environ.get('FLASK_DEBUG', str(config.FLASK_DEBUG)).lower() == 'true'
    
    # Run Flask app with error handling
    try:
        logger.info(f"Starting Flask app on {host}:{port}")
        socketio.run(app, host=host, port=port, debug=debug)
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"Port {port} is already in use!")
            logger.error("Try: make kill-flask-port or use FLASK_PORT=5001 make web")
            print(f"\nError: Port {port} is already in use!")
            print("Solutions:")
            print("  1. Kill the process: lsof -ti:5000 | xargs kill -9")
            print("  2. Use different port: FLASK_PORT=5001 make web")
            sys.exit(1)
        else:
            raise