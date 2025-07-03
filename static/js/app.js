// Dev Container Manager - Main JavaScript

// Initialize Socket.IO connection
const socket = io();

// Connection status management
let isConnected = false;

socket.on('connect', function() {
    console.log('Connected to server');
    isConnected = true;
    updateConnectionStatus(true);
});

socket.on('disconnect', function() {
    console.log('Disconnected from server');
    isConnected = false;
    updateConnectionStatus(false);
});

socket.on('connected', function(data) {
    console.log('Server:', data.data);
});

// Update connection status indicator
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    if (connected) {
        statusElement.textContent = ' Connected';
        statusElement.classList.remove('bg-secondary');
        statusElement.classList.add('bg-success', 'connected');
    } else {
        statusElement.textContent = ' Disconnected';
        statusElement.classList.remove('bg-success', 'connected');
        statusElement.classList.add('bg-secondary');
    }
    
    // Add icon
    const icon = document.createElement('i');
    icon.className = 'bi bi-circle-fill';
    statusElement.prepend(icon);
}

// Toast notification system
function showToast(message, type = 'info') {
    const toastTemplate = document.getElementById('toast-template');
    const toastContainer = document.querySelector('.toast-container');
    
    // Clone the template
    const toast = toastTemplate.cloneNode(true);
    toast.id = 'toast-' + Date.now();
    
    // Set the message
    toast.querySelector('.toast-body').textContent = message;
    
    // Add type-specific class
    toast.classList.add(type);
    
    // Append to container
    toastContainer.appendChild(toast);
    
    // Initialize and show the toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove from DOM after hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// API request helper
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    try {
        const response = await fetch(url, { ...defaultOptions, ...options });
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Container status color mapping
const statusColors = {
    'running': 'success',
    'exited': 'secondary',
    'stopped': 'secondary',
    'paused': 'warning',
    'restarting': 'info',
    'removing': 'danger',
    'dead': 'danger'
};

// Format dates
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Debounce function for search/filter
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Check for system dark mode preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.body.classList.add('dark-mode');
    }
    
    // Listen for dark mode changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
        if (event.matches) {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
    });
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K: Focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Ctrl/Cmd + N: New container
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        window.location.href = '/create';
    }
    
    // Escape: Close modals
    if (e.key === 'Escape') {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
    }
});

// Export functions for use in other scripts
window.showToast = showToast;
window.apiRequest = apiRequest;
window.formatDate = formatDate;
window.debounce = debounce;