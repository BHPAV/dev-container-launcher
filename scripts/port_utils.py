#!/usr/bin/env python3
"""Port management utilities for Flask app."""

import socket
import subprocess
import sys
import os

def is_port_in_use(port):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def get_process_using_port(port):
    """Get process info using a port."""
    try:
        result = subprocess.run(['lsof', '-ti', f':{port}'], 
                              capture_output=True, text=True)
        if result.stdout:
            pid = result.stdout.strip()
            # Get process name
            proc_result = subprocess.run(['ps', '-p', pid, '-o', 'comm='],
                                       capture_output=True, text=True)
            if proc_result.stdout:
                return f"{pid} ({proc_result.stdout.strip()})"
            return pid
    except:
        pass
    return None

def find_free_port(start=5000, end=5100):
    """Find a free port in range."""
    for port in range(start, end):
        if not is_port_in_use(port):
            return port
    raise RuntimeError(f"No free ports found in range {start}-{end}")

def kill_port(port):
    """Kill process using a port."""
    try:
        result = subprocess.run(['lsof', '-ti', f':{port}'], 
                              capture_output=True, text=True)
        if result.stdout:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                subprocess.run(['kill', '-9', pid])
            return True
    except:
        pass
    return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "check":
            port = int(os.environ.get('FLASK_PORT', 5000))
            if is_port_in_use(port):
                process = get_process_using_port(port)
                print(f"Port {port} is in use by process {process}")
                sys.exit(1)
            else:
                print(f"Port {port} is available")
                sys.exit(0)
                
        elif command == "kill":
            port = int(os.environ.get('FLASK_PORT', sys.argv[2] if len(sys.argv) > 2 else 5000))
            if kill_port(port):
                print(f"Killed process using port {port}")
            else:
                print(f"No process found using port {port}")
                
        elif command == "find":
            start = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
            port = find_free_port(start)
            print(port)
            
        else:
            print(f"Unknown command: {command}")
            print("Usage: python port_utils.py [check|kill|find] [port]")
            sys.exit(1)
    else:
        # Default: find and print free port
        port = find_free_port()
        print(port)