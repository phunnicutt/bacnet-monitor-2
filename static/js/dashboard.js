/**
 * BACmon Dashboard Controller
 * Handles real-time data updates, chart rendering, and user interactions
 */

class BACmonDashboard {
    constructor() {
        this.apiClient = new BACmonAPIClient();
        this.charts = {};
        this.updateIntervals = {};
        this.lastDataUpdate = null;
        this.autoRefresh = true;
        
        // Initialize dashboard
        this.init();
    }

    /**
     * Initialize the dashboard
     */
    async init() {
        try {
            console.log('Initializing BACmon Dashboard...');
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Initialize charts
            this.initializeCharts();
            
            // Load initial data
            await this.loadInitialData();
            
            // Start auto-refresh
            this.startAutoRefresh();
            
            console.log('Dashboard initialized successfully');
        } catch (error) {
            console.error('Failed to initialize dashboard:', error);
            this.showError('Failed to initialize dashboard. Please refresh the page.');
        }
    }

    /**
     * Setup event listeners for user interactions
     */
    setupEventListeners() {
        // Refresh buttons
        document.querySelectorAll('.refresh-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const btnId = e.target.id;
                switch (btnId) {
                    case 'refresh-traffic':
                        this.refreshTrafficData();
                        break;
                    case 'refresh-traffic-breakdown':
                        this.refreshTrafficBreakdown();
                        break;
                    case 'refresh-system-health':
                        this.refreshSystemHealth();
                        break;
                    case 'refresh-monitoring':
                        this.refreshMonitoringActivity();
                        break;
                }
            });
        });

        // Time range selector
        const trafficTimeRange = document.getElementById('traffic-timerange');
        if (trafficTimeRange) {
            trafficTimeRange.addEventListener('change', (e) => {
                this.refreshTrafficData(e.target.value);
            });
        }

        // Auto-refresh toggle (if implemented)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'r' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                this.refreshAllData();
            }
        });
    }

    /**
     * Initialize Chart.js charts
     */
    initializeCharts() {
        // Traffic Chart
        const trafficCtx = document.getElementById('traffic-chart');
        if (trafficCtx) {
            this.charts.traffic = new Chart(trafficCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'IP Traffic',
                            borderColor: '#2563eb',
                            backgroundColor: 'rgba(37, 99, 235, 0.1)',
                            data: [],
                            tension: 0.4
                        },
                        {
                            label: 'BVLL Traffic',
                            borderColor: '#06b6d4',
                            backgroundColor: 'rgba(6, 182, 212, 0.1)',
                            data: [],
                            tension: 0.4
                        },
                        {
                            label: 'Network Traffic',
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            data: [],
                            tension: 0.4
                        },
                        {
                            label: 'Application Traffic',
                            borderColor: '#f59e0b',
                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                            data: [],
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: 'rgba(51, 65, 85, 0.5)'
                            },
                            ticks: {
                                color: '#cbd5e1'
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(51, 65, 85, 0.5)'
                            },
                            ticks: {
                                color: '#cbd5e1'
                            }
                        }
                    },
                    elements: {
                        point: {
                            radius: 0,
                            hoverRadius: 6
                        }
                    }
                }
            });
        }

        // Traffic Breakdown Chart (Doughnut)
        const breakdownCtx = document.getElementById('traffic-breakdown-chart');
        if (breakdownCtx) {
            this.charts.breakdown = new Chart(breakdownCtx, {
                type: 'doughnut',
                data: {
                    labels: ['IP', 'BVLL', 'Network', 'Application', 'Error'],
                    datasets: [{
                        data: [],
                        backgroundColor: [
                            '#2563eb',
                            '#06b6d4',
                            '#10b981',
                            '#f59e0b',
                            '#ef4444'
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }
    }

    /**
     * Load initial data for all dashboard components
     */
    async loadInitialData() {
        console.log('Loading initial dashboard data...');
        
        // Load all data in parallel for faster initial load
        await Promise.allSettled([
            this.updateSystemStatus(),
            this.updateQuickStats(),
            this.refreshTrafficData(),
            this.refreshTrafficBreakdown(),
            this.updateRecentAlerts(),
            this.refreshSystemHealth(),
            this.updateTopDevices(),
            this.refreshMonitoringActivity()
        ]);

        this.updateLastUpdatedTime();
    }

    /**
     * Update system status indicators
     */
    async updateSystemStatus() {
        try {
            const status = await this.apiClient.getSystemStatus();
            
            // Update system status indicator
            const systemStatus = document.getElementById('system-status');
            const systemDot = systemStatus?.querySelector('.status-dot');
            if (systemDot) {
                systemDot.className = 'status-dot ' + (status.overall_status === 'healthy' ? 'online' : 
                                      status.overall_status === 'degraded' ? 'warning' : 'offline');
            }

            // Update Redis status indicator
            const connectionStatus = document.getElementById('connection-status');
            const redisDot = connectionStatus?.querySelector('.status-dot');
            if (redisDot) {
                redisDot.className = 'status-dot ' + (status.redis?.connected ? 'online' : 'offline');
            }

        } catch (error) {
            console.error('Failed to update system status:', error);
            this.setStatusIndicator('system-status', 'offline');
            this.setStatusIndicator('connection-status', 'offline');
        }
    }

    /**
     * Update quick stats cards
     */
    async updateQuickStats() {
        try {
            // Get monitoring data for stats
            const monitoring = await this.apiClient.getMonitoringData({ time_range: '24h' });
            const devices = await this.apiClient.getDevicesInfo();
            const status = await this.apiClient.getSystemStatus();

            // Total Messages
            const totalMessages = monitoring?.data?.length || 0;
            this.updateStatCard('total-messages', totalMessages, this.formatNumber);

            // Active Devices
            const activeDevices = devices?.devices?.length || 0;
            this.updateStatCard('active-devices', activeDevices, this.formatNumber);

            // System Uptime
            if (status?.system?.uptime) {
                this.updateStatCard('system-uptime', status.system.uptime, this.formatUptime);
            }

            // Alert Count (would be from anomalies or alerts endpoint)
            try {
                const anomalies = await this.apiClient.getAnomaliesData({ severity: 'high,critical' });
                const alertCount = anomalies?.anomalies?.length || 0;
                this.updateStatCard('alert-count', alertCount, this.formatNumber);
            } catch (e) {
                this.updateStatCard('alert-count', 0, this.formatNumber);
            }

        } catch (error) {
            console.error('Failed to update quick stats:', error);
        }
    }

    /**
     * Update stat card with value and trend
     */
    updateStatCard(cardId, value, formatter = null) {
        const valueElement = document.getElementById(`${cardId}-value`);
        const trendElement = document.getElementById(`${cardId}-trend`);

        if (valueElement) {
            valueElement.textContent = formatter ? formatter(value) : value;
        }

        // Add trend calculation if we have previous values stored
        if (trendElement && this.previousStats && this.previousStats[cardId] !== undefined) {
            const previousValue = this.previousStats[cardId];
            const change = value - previousValue;
            const percent = previousValue > 0 ? ((change / previousValue) * 100).toFixed(1) : 0;
            
            if (change > 0) {
                trendElement.textContent = `↗ +${percent}%`;
                trendElement.className = 'stat-trend up';
            } else if (change < 0) {
                trendElement.textContent = `↘ ${percent}%`;
                trendElement.className = 'stat-trend down';
            } else {
                trendElement.textContent = '→ 0%';
                trendElement.className = 'stat-trend neutral';
            }
        }

        // Store current value for next trend calculation
        if (!this.previousStats) this.previousStats = {};
        this.previousStats[cardId] = value;
    }

    /**
     * Refresh traffic data and update chart
     */
    async refreshTrafficData(timeRange = '24h') {
        try {
            this.setLoadingState('traffic-chart', true);
            
            const trafficData = await this.apiClient.getTrafficAnalysis({ time_range: timeRange });
            
            if (trafficData && this.charts.traffic) {
                // Process data for chart
                const labels = this.generateTimeLabels(timeRange);
                const datasets = this.processTrafficDataForChart(trafficData, labels);
                
                this.charts.traffic.data.labels = labels;
                this.charts.traffic.data.datasets.forEach((dataset, index) => {
                    if (datasets[index]) {
                        dataset.data = datasets[index];
                    }
                });
                
                this.charts.traffic.update('none');
                this.updateTrafficLegend();
            }
            
        } catch (error) {
            console.error('Failed to refresh traffic data:', error);
        } finally {
            this.setLoadingState('traffic-chart', false);
        }
    }

    /**
     * Refresh traffic breakdown chart
     */
    async refreshTrafficBreakdown() {
        try {
            this.setLoadingState('traffic-breakdown-chart', true);
            
            const trafficData = await this.apiClient.getTrafficAnalysis({ time_range: '24h' });
            
            if (trafficData && this.charts.breakdown) {
                const summary = trafficData.summary || {};
                const data = [
                    summary.ip_traffic || 0,
                    summary.bvll_traffic || 0,
                    summary.network_traffic || 0,
                    summary.application_traffic || 0,
                    summary.error_traffic || 0
                ];
                
                this.charts.breakdown.data.datasets[0].data = data;
                this.charts.breakdown.update('none');
                
                // Update traffic stats
                this.updateTrafficStats(summary);
            }
            
        } catch (error) {
            console.error('Failed to refresh traffic breakdown:', error);
        } finally {
            this.setLoadingState('traffic-breakdown-chart', false);
        }
    }

    /**
     * Update recent alerts section
     */
    async updateRecentAlerts() {
        try {
            const alertsList = document.getElementById('recent-alerts');
            if (!alertsList) return;

            // Try to get anomalies as alerts
            try {
                const anomalies = await this.apiClient.getAnomaliesData({ limit: 5 });
                if (anomalies?.anomalies && anomalies.anomalies.length > 0) {
                    this.renderAlerts(alertsList, anomalies.anomalies);
                } else {
                    this.renderEmptyAlerts(alertsList);
                }
            } catch (e) {
                // If no anomalies endpoint, show sample alerts or empty state
                this.renderEmptyAlerts(alertsList);
            }
            
        } catch (error) {
            console.error('Failed to update recent alerts:', error);
            this.renderEmptyAlerts(document.getElementById('recent-alerts'));
        }
    }

    /**
     * Refresh system health metrics
     */
    async refreshSystemHealth() {
        try {
            const status = await this.apiClient.getSystemStatus();
            
            // Update Redis health
            this.updateHealthStatus('redis-health', 
                status.redis?.connected ? 'healthy' : 'critical',
                status.redis?.connected ? 'Connected' : 'Disconnected'
            );

            // Update daemon health
            this.updateHealthStatus('daemon-health',
                status.system?.daemon_running ? 'healthy' : 'critical',
                status.system?.daemon_running ? 'Running' : 'Stopped'
            );

            // Update alert system health
            this.updateHealthStatus('alert-system-health',
                status.services?.alert_manager ? 'healthy' : 'warning',
                status.services?.alert_manager ? 'Active' : 'Inactive'
            );

            // Update memory usage
            if (status.system?.memory_usage) {
                const memoryPercent = parseFloat(status.system.memory_usage);
                const memoryStatus = memoryPercent > 90 ? 'critical' : memoryPercent > 75 ? 'warning' : 'healthy';
                this.updateHealthStatus('memory-health', memoryStatus, `${memoryPercent.toFixed(1)}%`);
            }

        } catch (error) {
            console.error('Failed to refresh system health:', error);
            this.updateHealthStatus('redis-health', 'critical', 'Error');
            this.updateHealthStatus('daemon-health', 'critical', 'Error');
            this.updateHealthStatus('alert-system-health', 'critical', 'Error');
            this.updateHealthStatus('memory-health', 'critical', 'Error');
        }
    }

    /**
     * Update top devices section
     */
    async updateTopDevices() {
        try {
            const devicesList = document.getElementById('top-devices');
            if (!devicesList) return;

            const devices = await this.apiClient.getDevicesInfo({ limit: 5 });
            if (devices?.devices && devices.devices.length > 0) {
                this.renderTopDevices(devicesList, devices.devices);
            } else {
                this.renderEmptyDevices(devicesList);
            }

        } catch (error) {
            console.error('Failed to update top devices:', error);
            this.renderEmptyDevices(document.getElementById('top-devices'));
        }
    }

    /**
     * Refresh monitoring activity
     */
    async refreshMonitoringActivity() {
        try {
            const monitoringList = document.getElementById('monitoring-activity');
            if (!monitoringList) return;

            const monitoring = await this.apiClient.getMonitoringData({ limit: 10 });
            if (monitoring?.data && monitoring.data.length > 0) {
                this.renderMonitoringActivity(monitoringList, monitoring.data);
            } else {
                this.renderEmptyMonitoring(monitoringList);
            }

        } catch (error) {
            console.error('Failed to refresh monitoring activity:', error);
            this.renderEmptyMonitoring(document.getElementById('monitoring-activity'));
        }
    }

    /**
     * Helper Methods for Rendering
     */
    renderAlerts(container, alerts) {
        container.innerHTML = alerts.map(alert => `
            <div class="alert-item ${this.getAlertSeverityClass(alert.severity)}">
                <div class="alert-header">
                    <span class="alert-title">${this.escapeHtml(alert.type || 'Alert')}</span>
                    <span class="alert-time">${this.formatTimeAgo(alert.timestamp)}</span>
                </div>
                <div class="alert-message">${this.escapeHtml(alert.description || alert.message || 'No details available')}</div>
            </div>
        `).join('');
    }

    renderEmptyAlerts(container) {
        container.innerHTML = `
            <div class="alert-item info">
                <div class="alert-header">
                    <span class="alert-title">No Recent Alerts</span>
                    <span class="alert-time">Now</span>
                </div>
                <div class="alert-message">System is running normally</div>
            </div>
        `;
    }

    renderTopDevices(container, devices) {
        container.innerHTML = devices.slice(0, 5).map(device => `
            <div class="device-item">
                <div class="device-info">
                    <div class="device-name">${this.escapeHtml(device.name || device.device_id || 'Unknown Device')}</div>
                    <div class="device-id">${this.escapeHtml(device.device_id || device.ip_address || 'N/A')}</div>
                </div>
                <div class="device-activity">
                    <div class="device-messages">${this.formatNumber(device.message_count || 0)}</div>
                    <div class="device-last-seen">${this.formatTimeAgo(device.last_seen)}</div>
                </div>
            </div>
        `).join('');
    }

    renderEmptyDevices(container) {
        container.innerHTML = `
            <div class="device-item">
                <div class="device-info">
                    <div class="device-name">No Devices Found</div>
                    <div class="device-id">Check network connection</div>
                </div>
                <div class="device-activity">
                    <div class="device-messages">0</div>
                    <div class="device-last-seen">Never</div>
                </div>
            </div>
        `;
    }

    renderMonitoringActivity(container, data) {
        container.innerHTML = data.slice(0, 8).map(item => `
            <div class="monitoring-item">
                <span class="monitoring-key">${this.escapeHtml(item.key || 'unknown')}</span>
                <span class="monitoring-value">${this.escapeHtml(item.value || 'N/A')}</span>
            </div>
        `).join('');
    }

    renderEmptyMonitoring(container) {
        container.innerHTML = `
            <div class="monitoring-item">
                <span class="monitoring-key">No monitoring data</span>
                <span class="monitoring-value">--</span>
            </div>
        `;
    }

    /**
     * Update health status indicator
     */
    updateHealthStatus(elementId, status, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text;
            element.className = `health-status ${status}`;
        }
    }

    /**
     * Update traffic stats section
     */
    updateTrafficStats(summary) {
        const statsContainer = document.getElementById('traffic-stats');
        if (!statsContainer) return;

        const stats = [
            { label: 'IP Traffic', value: this.formatNumber(summary.ip_traffic || 0) },
            { label: 'BVLL Traffic', value: this.formatNumber(summary.bvll_traffic || 0) },
            { label: 'Network Traffic', value: this.formatNumber(summary.network_traffic || 0) },
            { label: 'Application Traffic', value: this.formatNumber(summary.application_traffic || 0) },
            { label: 'Error Traffic', value: this.formatNumber(summary.error_traffic || 0) }
        ];

        statsContainer.innerHTML = stats.map(stat => `
            <div class="traffic-stat-item">
                <span class="traffic-stat-label">${stat.label}</span>
                <span class="traffic-stat-value">${stat.value}</span>
            </div>
        `).join('');
    }

    /**
     * Update traffic chart legend
     */
    updateTrafficLegend() {
        const legendContainer = document.getElementById('traffic-legend');
        if (!legendContainer || !this.charts.traffic) return;

        const datasets = this.charts.traffic.data.datasets;
        legendContainer.innerHTML = datasets.map(dataset => `
            <div class="legend-item">
                <div class="legend-color" style="background-color: ${dataset.borderColor}"></div>
                <span>${dataset.label}</span>
            </div>
        `).join('');
    }

    /**
     * Auto-refresh functionality
     */
    startAutoRefresh() {
        // System status every 30 seconds
        this.updateIntervals.systemStatus = setInterval(() => {
            this.updateSystemStatus();
        }, 30000);

        // Quick stats every minute
        this.updateIntervals.quickStats = setInterval(() => {
            this.updateQuickStats();
        }, 60000);

        // Full refresh every 5 minutes
        this.updateIntervals.fullRefresh = setInterval(() => {
            this.refreshAllData();
        }, 300000);

        // Update timestamp every 30 seconds
        this.updateIntervals.timestamp = setInterval(() => {
            this.updateLastUpdatedTime();
        }, 30000);
    }

    /**
     * Refresh all dashboard data
     */
    async refreshAllData() {
        console.log('Refreshing all dashboard data...');
        await this.loadInitialData();
    }

    /**
     * Update last updated timestamp
     */
    updateLastUpdatedTime() {
        const element = document.getElementById('last-updated');
        if (element) {
            element.textContent = new Date().toLocaleTimeString();
        }
    }

    /**
     * Utility Methods
     */
    setLoadingState(elementId, loading) {
        const element = document.getElementById(elementId);
        if (element) {
            if (loading) {
                element.classList.add('loading');
            } else {
                element.classList.remove('loading');
            }
        }
    }

    setStatusIndicator(containerId, status) {
        const container = document.getElementById(containerId);
        const dot = container?.querySelector('.status-dot');
        if (dot) {
            dot.className = `status-dot ${status}`;
        }
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) {
            return `${days}d ${hours}h`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }

    formatTimeAgo(timestamp) {
        if (!timestamp) return 'Never';
        
        const now = new Date();
        const time = new Date(timestamp * 1000); // Assuming Unix timestamp
        const diff = now - time;
        const seconds = Math.floor(diff / 1000);
        
        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        return `${Math.floor(seconds / 86400)}d ago`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getAlertSeverityClass(severity) {
        switch (severity?.toLowerCase()) {
            case 'critical':
            case 'high':
                return 'critical';
            case 'warning':
            case 'medium':
                return 'warning';
            default:
                return 'info';
        }
    }

    generateTimeLabels(timeRange) {
        // Generate appropriate time labels based on time range
        const now = new Date();
        const labels = [];
        let interval, count;
        
        switch (timeRange) {
            case '1h':
                interval = 5 * 60 * 1000; // 5 minutes
                count = 12;
                break;
            case '6h':
                interval = 30 * 60 * 1000; // 30 minutes
                count = 12;
                break;
            case '24h':
                interval = 2 * 60 * 60 * 1000; // 2 hours
                count = 12;
                break;
            case '7d':
                interval = 24 * 60 * 60 * 1000; // 1 day
                count = 7;
                break;
            default:
                interval = 60 * 60 * 1000; // 1 hour
                count = 24;
        }
        
        for (let i = count - 1; i >= 0; i--) {
            const time = new Date(now.getTime() - (i * interval));
            labels.push(time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
        }
        
        return labels;
    }

    processTrafficDataForChart(trafficData, labels) {
        // Process traffic data to match chart labels
        // This is a simplified version - in reality, you'd match actual data points to time labels
        const datasets = [[], [], [], []];
        
        if (trafficData?.details) {
            // Simulate data processing - replace with actual data mapping
            labels.forEach((label, index) => {
                datasets[0].push(Math.floor(Math.random() * 100)); // IP traffic
                datasets[1].push(Math.floor(Math.random() * 80));  // BVLL traffic
                datasets[2].push(Math.floor(Math.random() * 60));  // Network traffic
                datasets[3].push(Math.floor(Math.random() * 40));  // Application traffic
            });
        } else {
            // Fill with zeros if no data
            labels.forEach(() => {
                datasets.forEach(dataset => dataset.push(0));
            });
        }
        
        return datasets;
    }

    showError(message) {
        // Simple error display - could be enhanced with a toast system
        console.error(message);
        // You could add a toast notification system here
    }

    /**
     * Cleanup method
     */
    destroy() {
        // Clear all intervals
        Object.values(this.updateIntervals).forEach(interval => {
            clearInterval(interval);
        });
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
    }
}

// Global export function for quick actions
function exportData() {
    // Use the API client to export data
    if (window.dashboardInstance && window.dashboardInstance.apiClient) {
        window.dashboardInstance.apiClient.exportData('json')
            .then(response => {
                console.log('Data exported successfully');
            })
            .catch(error => {
                console.error('Export failed:', error);
            });
    } else {
        window.location.href = '/api/export?format=json&time_range=24h';
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardInstance = new BACmonDashboard();
    
    // Handle page visibility changes for performance
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            // Pause auto-refresh when tab is not visible
            console.log('Dashboard paused (tab not visible)');
        } else {
            // Resume auto-refresh when tab becomes visible
            console.log('Dashboard resumed (tab visible)');
            if (window.dashboardInstance) {
                window.dashboardInstance.refreshAllData();
            }
        }
    });
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboardInstance) {
        window.dashboardInstance.destroy();
    }
}); 