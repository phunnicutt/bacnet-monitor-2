/**
 * BACmon API Client
 * Provides a clean interface for interacting with the BACmon REST API
 */

class BACmonAPIClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.version = '1.0.0';
    }

    /**
     * Generic method for making API requests
     * @param {string} endpoint - API endpoint path
     * @param {Object} options - Request options
     * @returns {Promise<Object>} - API response
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const defaults = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        };

        const config = { ...defaults, ...options };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            // Check if the response follows the standardized format
            if (data.status && data.timestamp && data.version !== undefined) {
                if (data.status === 'error') {
                    throw new Error(data.error || 'Unknown API error');
                }
                return data;
            } else {
                // Legacy format, wrap it
                return {
                    status: 'success',
                    timestamp: new Date().toISOString(),
                    version: this.version,
                    code: 200,
                    data: data
                };
            }
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    }

    /**
     * Build query string from parameters
     * @param {Object} params - Query parameters
     * @returns {string} - Query string
     */
    buildQueryString(params) {
        const filtered = Object.entries(params)
            .filter(([key, value]) => value !== null && value !== undefined && value !== '')
            .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`);
        
        return filtered.length > 0 ? `?${filtered.join('&')}` : '';
    }

    // ===== System Status API =====

    /**
     * Get system status information
     * @returns {Promise<Object>} - System status data
     */
    async getSystemStatus() {
        return await this.request('/api/status');
    }

    // ===== Monitoring Data API =====

    /**
     * Get monitoring data with optional filtering
     * @param {Object} params - Query parameters
     * @param {string} params.range - Time range (1h, 6h, 24h, 7d, 30d)
     * @param {number} params.start - Start timestamp
     * @param {number} params.end - End timestamp
     * @param {string} params.keys - Comma-separated keys to filter
     * @param {number} params.offset - Pagination offset
     * @param {number} params.limit - Pagination limit
     * @returns {Promise<Object>} - Monitoring data
     */
    async getMonitoringData(params = {}) {
        const queryString = this.buildQueryString(params);
        return await this.request(`/api/monitoring${queryString}`);
    }

    // ===== Traffic Analysis API =====

    /**
     * Get traffic analysis data
     * @param {Object} params - Query parameters
     * @param {string} params.range - Time range (1h, 6h, 24h, 7d)
     * @param {number} params.start - Start timestamp
     * @param {number} params.end - End timestamp
     * @param {string} params.type - Traffic type filter
     * @param {number} params.offset - Pagination offset
     * @param {number} params.limit - Pagination limit
     * @returns {Promise<Object>} - Traffic analysis data
     */
    async getTrafficAnalysis(params = {}) {
        const queryString = this.buildQueryString(params);
        return await this.request(`/api/traffic${queryString}`);
    }

    // ===== Devices API =====

    /**
     * Get BACnet device information
     * @param {Object} params - Query parameters
     * @param {string} params.search - Search term for filtering devices
     * @param {string} params.sort - Sort field
     * @param {number} params.offset - Pagination offset
     * @param {number} params.limit - Pagination limit
     * @returns {Promise<Object>} - Device information
     */
    async getDevices(params = {}) {
        const queryString = this.buildQueryString(params);
        return await this.request(`/api/devices${queryString}`);
    }

    // ===== Anomalies API =====

    /**
     * Get anomaly detection data
     * @param {Object} params - Query parameters
     * @param {string} params.range - Time range (1h, 6h, 24h, 7d)
     * @param {number} params.start - Start timestamp
     * @param {number} params.end - End timestamp
     * @param {string} params.severity - Severity filter (low, medium, high, critical)
     * @param {number} params.offset - Pagination offset
     * @param {number} params.limit - Pagination limit
     * @returns {Promise<Object>} - Anomaly data
     */
    async getAnomalies(params = {}) {
        const queryString = this.buildQueryString(params);
        return await this.request(`/api/anomalies${queryString}`);
    }

    // ===== Export API =====

    /**
     * Export data in specified format
     * @param {Object} params - Query parameters
     * @param {string} params.type - Export type (monitoring, traffic, devices, anomalies)
     * @param {string} params.format - Export format (json, csv)
     * @param {string} params.range - Time range
     * @param {number} params.start - Start timestamp
     * @param {number} params.end - End timestamp
     * @returns {Promise<Blob|Object>} - Export data or download response
     */
    async exportData(params = {}) {
        const queryString = this.buildQueryString(params);
        const url = `${this.baseUrl}/api/export${queryString}`;
        
        try {
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const contentType = response.headers.get('Content-Type');
            
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                // For CSV downloads, return blob
                const blob = await response.blob();
                return blob;
            }
        } catch (error) {
            console.error('Export Error:', error);
            throw error;
        }
    }

    /**
     * Download exported data as file
     * @param {Object} params - Export parameters
     * @param {string} filename - Optional filename
     */
    async downloadExport(params = {}, filename = null) {
        const blob = await this.exportData(params);
        
        if (blob instanceof Blob) {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            if (!filename) {
                const timestamp = new Date().toISOString().split('T')[0];
                const extension = params.format === 'csv' ? 'csv' : 'json';
                filename = `bacmon-${params.type || 'export'}-${timestamp}.${extension}`;
            }
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            throw new Error('Export did not return downloadable data');
        }
    }

    // ===== Legacy API Support =====

    /**
     * Get alerts data (legacy endpoint)
     * @param {Object} params - Query parameters
     * @returns {Promise<Object>} - Alerts data
     */
    async getAlerts(params = {}) {
        const queryString = this.buildQueryString(params);
        return await this.request(`/api/alerts${queryString}`);
    }

    /**
     * Get metrics data (legacy endpoint)
     * @param {string} key - Optional metric key
     * @param {Object} params - Query parameters
     * @returns {Promise<Object>} - Metrics data
     */
    async getMetrics(key = null, params = {}) {
        const endpoint = key ? `/api/metrics/${key}` : '/api/metrics';
        const queryString = this.buildQueryString(params);
        return await this.request(`${endpoint}${queryString}`);
    }

    /**
     * Get extended metrics data
     * @param {Object} params - Query parameters
     * @returns {Promise<Object>} - Extended metrics data
     */
    async getExtendedMetrics(params = {}) {
        const queryString = this.buildQueryString(params);
        return await this.request(`/api/extended_metrics${queryString}`);
    }
}

// ===== Utility Functions =====

/**
 * Format timestamp for display
 * @param {number|string} timestamp - Unix timestamp or ISO string
 * @param {boolean} includeTime - Whether to include time
 * @returns {string} - Formatted date string
 */
function formatTimestamp(timestamp, includeTime = true) {
    const date = new Date(typeof timestamp === 'number' ? timestamp * 1000 : timestamp);
    
    if (includeTime) {
        return date.toLocaleString();
    } else {
        return date.toLocaleDateString();
    }
}

/**
 * Format bytes for human readable display
 * @param {number} bytes - Number of bytes
 * @param {number} decimals - Number of decimal places
 * @returns {string} - Formatted string
 */
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Format duration in seconds to human readable format
 * @param {number} seconds - Duration in seconds
 * @returns {string} - Formatted duration
 */
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

/**
 * Get status indicator class based on status
 * @param {string} status - Status string
 * @returns {string} - CSS class name
 */
function getStatusClass(status) {
    const statusMap = {
        'online': 'online',
        'active': 'online',
        'running': 'online',
        'healthy': 'online',
        'ok': 'online',
        'offline': 'offline',
        'inactive': 'offline',
        'stopped': 'offline',
        'error': 'offline',
        'failed': 'offline',
        'warning': 'warning',
        'degraded': 'warning',
        'unknown': 'checking',
        'checking': 'checking'
    };

    return statusMap[status.toLowerCase()] || 'checking';
}

/**
 * Debounce function to limit rapid function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} - Debounced function
 */
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

// Create global API client instance
window.BACmonAPI = new BACmonAPIClient();

// Export utility functions to global scope
window.BACmonUtils = {
    formatTimestamp,
    formatBytes,
    formatDuration,
    getStatusClass,
    debounce
}; 