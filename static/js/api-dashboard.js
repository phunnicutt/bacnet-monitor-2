/**
 * BACmon API Dashboard
 * Main dashboard functionality for interacting with the REST API
 */

class APIDashboard {
    constructor() {
        this.charts = {};
        this.updateIntervals = {};
        this.autoRefresh = false;
        this.refreshInterval = 30000; // 30 seconds
        
        this.init();
    }

    /**
     * Initialize the dashboard
     */
    init() {
        this.bindEvents();
        this.loadInitialData();
        this.setupAutoRefresh();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // System status refresh
        document.getElementById('refresh-monitoring')?.addEventListener('click', () => {
            this.loadMonitoringData();
        });

        // Traffic analysis refresh
        document.getElementById('refresh-traffic')?.addEventListener('click', () => {
            this.loadTrafficData();
        });

        // Devices refresh
        document.getElementById('refresh-devices')?.addEventListener('click', () => {
            this.loadDevicesData();
        });

        // Anomalies refresh
        document.getElementById('refresh-anomalies')?.addEventListener('click', () => {
            this.loadAnomaliesData();
        });

        // Export functionality
        document.getElementById('export-data')?.addEventListener('click', () => {
            this.handleExport();
        });

        // Time range changes
        document.getElementById('monitoring-range')?.addEventListener('change', () => {
            this.loadMonitoringData();
        });

        document.getElementById('traffic-range')?.addEventListener('change', () => {
            this.loadTrafficData();
        });

        document.getElementById('anomaly-range')?.addEventListener('change', () => {
            this.loadAnomaliesData();
        });

        // Filter changes with debouncing
        const debouncedDeviceSearch = BACmonUtils.debounce(() => {
            this.loadDevicesData();
        }, 500);

        document.getElementById('device-search')?.addEventListener('input', debouncedDeviceSearch);
        document.getElementById('device-sort')?.addEventListener('change', () => {
            this.loadDevicesData();
        });

        document.getElementById('traffic-type')?.addEventListener('change', () => {
            this.loadTrafficData();
        });

        document.getElementById('anomaly-severity')?.addEventListener('change', () => {
            this.loadAnomaliesData();
        });

        const debouncedMonitoringKeys = BACmonUtils.debounce(() => {
            this.loadMonitoringData();
        }, 500);

        document.getElementById('monitoring-keys')?.addEventListener('input', debouncedMonitoringKeys);
    }

    /**
     * Load initial data for all panels
     */
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadSystemStatus(),
                this.loadMonitoringData(),
                this.loadTrafficData(),
                this.loadDevicesData(),
                this.loadAnomaliesData()
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load initial dashboard data');
        }
    }

    /**
     * Setup auto-refresh functionality
     */
    setupAutoRefresh() {
        // Auto-refresh system status every 30 seconds
        setInterval(() => {
            if (this.autoRefresh) {
                this.loadSystemStatus();
            }
        }, this.refreshInterval);

        // Enable auto-refresh by default for status
        this.autoRefresh = true;
    }

    // ===== System Status Panel =====

    /**
     * Load and display system status
     */
    async loadSystemStatus() {
        try {
            const response = await BACmonAPI.getSystemStatus();
            this.renderSystemStatus(response.data);
        } catch (error) {
            console.error('Error loading system status:', error);
            this.renderSystemStatusError();
        }
    }

    /**
     * Render system status data
     */
    renderSystemStatus(data) {
        // Update status indicators
        this.updateStatusIndicator('redis', data.services?.redis);
        this.updateStatusIndicator('daemon', data.services?.bacmon_daemon);
        this.updateStatusIndicator('anomaly', data.services?.anomaly_detection);
        this.updateStatusIndicator('alerts', data.services?.alert_system);

        // Update system information
        const systemInfo = document.getElementById('system-info');
        if (systemInfo && data.system) {
            systemInfo.innerHTML = `
                <div class="summary-cards">
                    <div class="summary-card">
                        <h4>Uptime</h4>
                        <div class="value">${BACmonUtils.formatDuration(data.system.uptime || 0)}</div>
                    </div>
                    <div class="summary-card">
                        <h4>Version</h4>
                        <div class="value">${data.system.version || 'Unknown'}</div>
                    </div>
                    <div class="summary-card">
                        <h4>Redis Keys</h4>
                        <div class="value">${(data.system.redis_info?.total_keys || 0).toLocaleString()}</div>
                    </div>
                    <div class="summary-card">
                        <h4>Memory Usage</h4>
                        <div class="value">${BACmonUtils.formatBytes(data.system.redis_info?.memory_usage || 0)}</div>
                    </div>
                </div>
            `;
        }
    }

    /**
     * Update individual status indicator
     */
    updateStatusIndicator(service, serviceData) {
        const indicator = document.getElementById(`${service}-indicator`);
        const text = document.getElementById(`${service}-text`);
        
        if (indicator && text) {
            const status = serviceData?.status || 'unknown';
            const statusClass = BACmonUtils.getStatusClass(status);
            
            indicator.className = `status-indicator ${statusClass}`;
            text.textContent = serviceData?.message || status;
        }
    }

    /**
     * Render system status error
     */
    renderSystemStatusError() {
        ['redis', 'daemon', 'anomaly', 'alerts'].forEach(service => {
            this.updateStatusIndicator(service, { status: 'error', message: 'Connection failed' });
        });

        const systemInfo = document.getElementById('system-info');
        if (systemInfo) {
            systemInfo.innerHTML = '<div class="error-message">Unable to load system information</div>';
        }
    }

    // ===== Monitoring Data Panel =====

    /**
     * Load and display monitoring data
     */
    async loadMonitoringData() {
        const container = document.getElementById('monitoring-data-table');
        if (container) {
            container.innerHTML = '<div class="loading">Loading monitoring data</div>';
        }

        try {
            const params = this.getMonitoringParams();
            const response = await BACmonAPI.getMonitoringData(params);
            this.renderMonitoringData(response.data);
        } catch (error) {
            console.error('Error loading monitoring data:', error);
            if (container) {
                container.innerHTML = '<div class="error-message">Failed to load monitoring data</div>';
            }
        }
    }

    /**
     * Get monitoring parameters from form
     */
    getMonitoringParams() {
        return {
            range: document.getElementById('monitoring-range')?.value || '24h',
            keys: document.getElementById('monitoring-keys')?.value || '',
            limit: 100
        };
    }

    /**
     * Render monitoring data
     */
    renderMonitoringData(data) {
        this.renderMonitoringChart(data.time_series || []);
        this.renderMonitoringTable(data.keys || []);
    }

    /**
     * Render monitoring chart
     */
    renderMonitoringChart(timeSeries) {
        const canvas = document.getElementById('monitoring-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        if (this.charts.monitoring) {
            this.charts.monitoring.destroy();
        }

        if (timeSeries.length === 0) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#666';
            ctx.textAlign = 'center';
            ctx.fillText('No monitoring data available', canvas.width / 2, canvas.height / 2);
            return;
        }

        // Prepare data for Chart.js
        const datasets = this.prepareChartDatasets(timeSeries);

        this.charts.monitoring = new Chart(ctx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                hour: 'HH:mm',
                                day: 'MMM DD'
                            }
                        }
                    },
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                }
            }
        });
    }

    /**
     * Prepare chart datasets from time series data
     */
    prepareChartDatasets(timeSeries) {
        const colors = [
            'rgb(255, 99, 132)',
            'rgb(54, 162, 235)',
            'rgb(255, 205, 86)',
            'rgb(75, 192, 192)',
            'rgb(153, 102, 255)',
            'rgb(255, 159, 64)'
        ];

        return timeSeries.map((series, index) => ({
            label: series.key,
            data: series.data.map(point => ({
                x: new Date(point.timestamp * 1000),
                y: point.value
            })),
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length] + '20',
            tension: 0.1
        }));
    }

    /**
     * Render monitoring data table
     */
    renderMonitoringTable(keys) {
        const container = document.getElementById('monitoring-data-table');
        if (!container) return;

        if (keys.length === 0) {
            container.innerHTML = '<div class="empty-state">No monitoring keys found</div>';
            return;
        }

        const table = document.createElement('table');
        table.className = 'data-table';

        table.innerHTML = `
            <thead>
                <tr>
                    <th>Key</th>
                    <th>Current Value</th>
                    <th>Last Updated</th>
                    <th>24h Change</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${keys.map(key => `
                    <tr>
                        <td>${key.name}</td>
                        <td>${key.current_value?.toLocaleString() || 'N/A'}</td>
                        <td>${key.last_updated ? BACmonUtils.formatTimestamp(key.last_updated) : 'N/A'}</td>
                        <td class="change ${this.getChangeClass(key.change_24h)}">
                            ${key.change_24h !== undefined ? this.formatChange(key.change_24h) : 'N/A'}
                        </td>
                        <td><span class="status-indicator ${BACmonUtils.getStatusClass(key.status || 'unknown')}">●</span> ${key.status || 'Unknown'}</td>
                    </tr>
                `).join('')}
            </tbody>
        `;

        container.innerHTML = '';
        container.appendChild(table);
    }

    // ===== Traffic Analysis Panel =====

    /**
     * Load and display traffic data
     */
    async loadTrafficData() {
        const summaryContainer = document.getElementById('traffic-summary');
        const detailsContainer = document.getElementById('traffic-details');
        
        if (summaryContainer) {
            summaryContainer.innerHTML = '<div class="loading">Loading traffic data</div>';
        }

        try {
            const params = this.getTrafficParams();
            const response = await BACmonAPI.getTrafficAnalysis(params);
            this.renderTrafficData(response.data);
        } catch (error) {
            console.error('Error loading traffic data:', error);
            if (summaryContainer) {
                summaryContainer.innerHTML = '<div class="error-message">Failed to load traffic data</div>';
            }
        }
    }

    /**
     * Get traffic parameters from form
     */
    getTrafficParams() {
        return {
            range: document.getElementById('traffic-range')?.value || '24h',
            type: document.getElementById('traffic-type')?.value || '',
            limit: 100
        };
    }

    /**
     * Render traffic data
     */
    renderTrafficData(data) {
        this.renderTrafficSummary(data.summary || {});
        this.renderTrafficChart(data.time_series || []);
        this.renderTrafficDetails(data.details || []);
    }

    /**
     * Render traffic summary cards
     */
    renderTrafficSummary(summary) {
        const container = document.getElementById('traffic-summary');
        if (!container) return;

        container.innerHTML = `
            <div class="summary-cards">
                <div class="summary-card">
                    <h4>Total Packets</h4>
                    <div class="value">${(summary.total_packets || 0).toLocaleString()}</div>
                    <div class="change ${this.getChangeClass(summary.packets_change)}">
                        ${this.formatChange(summary.packets_change)}
                    </div>
                </div>
                <div class="summary-card">
                    <h4>Total Bytes</h4>
                    <div class="value">${BACmonUtils.formatBytes(summary.total_bytes || 0)}</div>
                    <div class="change ${this.getChangeClass(summary.bytes_change)}">
                        ${this.formatChange(summary.bytes_change)}
                    </div>
                </div>
                <div class="summary-card">
                    <h4>Average Rate</h4>
                    <div class="value">${(summary.avg_rate || 0).toFixed(1)} pps</div>
                </div>
                <div class="summary-card">
                    <h4>Peak Rate</h4>
                    <div class="value">${(summary.peak_rate || 0).toFixed(1)} pps</div>
                </div>
            </div>
        `;
    }

    /**
     * Render traffic chart
     */
    renderTrafficChart(timeSeries) {
        const canvas = document.getElementById('traffic-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        if (this.charts.traffic) {
            this.charts.traffic.destroy();
        }

        if (timeSeries.length === 0) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#666';
            ctx.textAlign = 'center';
            ctx.fillText('No traffic data available', canvas.width / 2, canvas.height / 2);
            return;
        }

        const datasets = this.prepareChartDatasets(timeSeries);

        this.charts.traffic = new Chart(ctx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                hour: 'HH:mm',
                                day: 'MMM DD'
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Packets per Second'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                }
            }
        });
    }

    /**
     * Render traffic details table
     */
    renderTrafficDetails(details) {
        const container = document.getElementById('traffic-details');
        if (!container) return;

        if (details.length === 0) {
            container.innerHTML = '<div class="empty-state">No traffic details available</div>';
            return;
        }

        const table = document.createElement('table');
        table.className = 'data-table';

        table.innerHTML = `
            <thead>
                <tr>
                    <th>Traffic Type</th>
                    <th>Packets</th>
                    <th>Bytes</th>
                    <th>Rate (pps)</th>
                    <th>Percentage</th>
                </tr>
            </thead>
            <tbody>
                ${details.map(detail => `
                    <tr>
                        <td>${detail.type}</td>
                        <td>${(detail.packets || 0).toLocaleString()}</td>
                        <td>${BACmonUtils.formatBytes(detail.bytes || 0)}</td>
                        <td>${(detail.rate || 0).toFixed(2)}</td>
                        <td>${(detail.percentage || 0).toFixed(1)}%</td>
                    </tr>
                `).join('')}
            </tbody>
        `;

        container.innerHTML = '';
        container.appendChild(table);
    }

    // ===== Devices Panel =====

    /**
     * Load and display devices data
     */
    async loadDevicesData() {
        const statsContainer = document.getElementById('device-stats');
        const tableContainer = document.getElementById('devices-table');
        
        if (tableContainer) {
            tableContainer.innerHTML = '<div class="loading">Loading devices data</div>';
        }

        try {
            const params = this.getDevicesParams();
            const response = await BACmonAPI.getDevices(params);
            this.renderDevicesData(response.data);
        } catch (error) {
            console.error('Error loading devices data:', error);
            if (tableContainer) {
                tableContainer.innerHTML = '<div class="error-message">Failed to load devices data</div>';
            }
        }
    }

    /**
     * Get devices parameters from form
     */
    getDevicesParams() {
        return {
            search: document.getElementById('device-search')?.value || '',
            sort: document.getElementById('device-sort')?.value || 'deviceId',
            limit: 100
        };
    }

    /**
     * Render devices data
     */
    renderDevicesData(data) {
        this.renderDeviceStats(data.summary || {});
        this.renderDevicesTable(data.devices || []);
    }

    /**
     * Render device statistics
     */
    renderDeviceStats(summary) {
        const container = document.getElementById('device-stats');
        if (!container) return;

        container.innerHTML = `
            <div class="device-stats">
                <div class="device-stat">
                    <div class="label">Total Devices</div>
                    <div class="value">${summary.total || 0}</div>
                </div>
                <div class="device-stat">
                    <div class="label">Online</div>
                    <div class="value">${summary.online || 0}</div>
                </div>
                <div class="device-stat">
                    <div class="label">Offline</div>
                    <div class="value">${summary.offline || 0}</div>
                </div>
                <div class="device-stat">
                    <div class="label">New (24h)</div>
                    <div class="value">${summary.new_24h || 0}</div>
                </div>
            </div>
        `;
    }

    /**
     * Render devices table
     */
    renderDevicesTable(devices) {
        const container = document.getElementById('devices-table');
        if (!container) return;

        if (devices.length === 0) {
            container.innerHTML = '<div class="empty-state">No devices found</div>';
            return;
        }

        const table = document.createElement('table');
        table.className = 'data-table';

        table.innerHTML = `
            <thead>
                <tr>
                    <th>Device ID</th>
                    <th>Name</th>
                    <th>IP Address</th>
                    <th>Network</th>
                    <th>Last Seen</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${devices.map(device => `
                    <tr>
                        <td>${device.device_id || 'N/A'}</td>
                        <td>${device.name || 'Unknown'}</td>
                        <td>${device.ip_address || 'N/A'}</td>
                        <td>${device.network || 'N/A'}</td>
                        <td>${device.last_seen ? BACmonUtils.formatTimestamp(device.last_seen) : 'N/A'}</td>
                        <td><span class="status-indicator ${BACmonUtils.getStatusClass(device.status || 'unknown')}">●</span> ${device.status || 'Unknown'}</td>
                    </tr>
                `).join('')}
            </tbody>
        `;

        container.innerHTML = '';
        container.appendChild(table);
    }

    // ===== Anomalies Panel =====

    /**
     * Load and display anomalies data
     */
    async loadAnomaliesData() {
        const summaryContainer = document.getElementById('anomaly-summary');
        const listContainer = document.getElementById('anomalies-list');
        
        if (listContainer) {
            listContainer.innerHTML = '<div class="loading">Loading anomalies data</div>';
        }

        try {
            const params = this.getAnomaliesParams();
            const response = await BACmonAPI.getAnomalies(params);
            this.renderAnomaliesData(response.data);
        } catch (error) {
            console.error('Error loading anomalies data:', error);
            if (listContainer) {
                listContainer.innerHTML = '<div class="error-message">Failed to load anomalies data</div>';
            }
        }
    }

    /**
     * Get anomalies parameters from form
     */
    getAnomaliesParams() {
        return {
            range: document.getElementById('anomaly-range')?.value || '24h',
            severity: document.getElementById('anomaly-severity')?.value || '',
            limit: 50
        };
    }

    /**
     * Render anomalies data
     */
    renderAnomaliesData(data) {
        this.renderAnomalySummary(data.summary || {});
        this.renderAnomaliesList(data.anomalies || []);
    }

    /**
     * Render anomaly summary
     */
    renderAnomalySummary(summary) {
        const container = document.getElementById('anomaly-summary');
        if (!container) return;

        container.innerHTML = `
            <div class="summary-cards">
                <div class="summary-card">
                    <h4>Total Anomalies</h4>
                    <div class="value">${summary.total || 0}</div>
                </div>
                <div class="summary-card">
                    <h4>Critical</h4>
                    <div class="value" style="color: #dc3545">${summary.critical || 0}</div>
                </div>
                <div class="summary-card">
                    <h4>High</h4>
                    <div class="value" style="color: #fd7e14">${summary.high || 0}</div>
                </div>
                <div class="summary-card">
                    <h4>Medium</h4>
                    <div class="value" style="color: #ffc107">${summary.medium || 0}</div>
                </div>
                <div class="summary-card">
                    <h4>Low</h4>
                    <div class="value" style="color: #28a745">${summary.low || 0}</div>
                </div>
            </div>
        `;
    }

    /**
     * Render anomalies list
     */
    renderAnomaliesList(anomalies) {
        const container = document.getElementById('anomalies-list');
        if (!container) return;

        if (anomalies.length === 0) {
            container.innerHTML = '<div class="empty-state">No anomalies found</div>';
            return;
        }

        container.innerHTML = anomalies.map(anomaly => `
            <div class="anomaly-item severity-${anomaly.severity || 'unknown'}">
                <div class="anomaly-header">
                    <span class="anomaly-title">${anomaly.key || 'Unknown Key'}</span>
                    <span class="anomaly-time">${BACmonUtils.formatTimestamp(anomaly.timestamp)}</span>
                </div>
                <div class="anomaly-content">
                    <span class="anomaly-severity ${anomaly.severity || 'unknown'}">${anomaly.severity || 'Unknown'}</span>
                    <p>${anomaly.description || 'No description available'}</p>
                    ${anomaly.details ? `<div class="anomaly-details"><strong>Details:</strong> ${anomaly.details}</div>` : ''}
                </div>
            </div>
        `).join('');
    }

    // ===== Export Panel =====

    /**
     * Handle data export
     */
    async handleExport() {
        const statusContainer = document.getElementById('export-status');
        const button = document.getElementById('export-data');
        
        if (button) {
            button.disabled = true;
            button.textContent = 'Exporting...';
        }

        try {
            const params = this.getExportParams();
            
            if (statusContainer) {
                statusContainer.className = 'export-status info';
                statusContainer.style.display = 'block';
                statusContainer.textContent = 'Preparing export...';
            }

            await BACmonAPI.downloadExport(params);

            if (statusContainer) {
                statusContainer.className = 'export-status success';
                statusContainer.textContent = 'Export completed successfully!';
                setTimeout(() => {
                    statusContainer.style.display = 'none';
                }, 3000);
            }
        } catch (error) {
            console.error('Export error:', error);
            if (statusContainer) {
                statusContainer.className = 'export-status error';
                statusContainer.style.display = 'block';
                statusContainer.textContent = `Export failed: ${error.message}`;
            }
        } finally {
            if (button) {
                button.disabled = false;
                button.textContent = 'Export Data';
            }
        }
    }

    /**
     * Get export parameters from form
     */
    getExportParams() {
        return {
            type: document.getElementById('export-type')?.value || 'monitoring',
            format: document.getElementById('export-format')?.value || 'json',
            range: document.getElementById('export-range')?.value || '24h'
        };
    }

    // ===== Utility Methods =====

    /**
     * Get CSS class for change indicators
     */
    getChangeClass(change) {
        if (change === undefined || change === null) return 'neutral';
        return change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral';
    }

    /**
     * Format change percentage
     */
    formatChange(change) {
        if (change === undefined || change === null) return 'N/A';
        const sign = change > 0 ? '+' : '';
        return `${sign}${change.toFixed(1)}%`;
    }

    /**
     * Show error message
     */
    showError(message) {
        console.error(message);
        // Could add a toast notification system here
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new APIDashboard();
}); 