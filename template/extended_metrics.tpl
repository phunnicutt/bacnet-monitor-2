<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BACmon Extended Metrics - {{key}}</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js"></script>
    <!-- Custom styles -->
    <style>
        body {
            padding-top: 20px;
            background-color: #f8f9fa;
        }
        .metric-card {
            transition: all 0.3s ease;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.1);
        }
        .card-header {
            border-radius: 10px 10px 0 0 !important;
        }
        .metric-value {
            font-size: 1.5rem;
            font-weight: bold;
        }
        .trend-indicator {
            font-size: 1.2rem;
            margin-left: 10px;
        }
        .trend-up {
            color: #dc3545;
        }
        .trend-down {
            color: #198754;
        }
        .trend-neutral {
            color: #6c757d;
        }
        .chart-container {
            position: relative;
            height: 300px;
            margin: 20px 0;
        }
        .table-responsive {
            margin-top: 20px;
        }
        .bg-warning-light {
            background-color: #fff3cd;
        }
        .bg-danger-light {
            background-color: #f8d7da;
        }
        .nav-tabs .nav-link.active {
            font-weight: bold;
            border-bottom: 3px solid #0d6efd;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="row mb-4">
            <div class="col-12">
                <nav aria-label="breadcrumb">
                    <ol class="breadcrumb">
                        <li class="breadcrumb-item"><a href="/">Home</a></li>
                        <li class="breadcrumb-item"><a href="/metrics">Metrics</a></li>
                        <li class="breadcrumb-item active" aria-current="page">{{key}}</li>
                    </ol>
                </nav>
                <h1 class="display-5 mb-4">
                    <i class="fas fa-chart-line me-2"></i> Extended Metrics: {{key}}
                </h1>
            </div>
        </div>

        <!-- Summary Cards -->
        <div class="row mb-4">
            <!-- Packet Count -->
            <div class="col-md-4">
                <div class="card metric-card bg-primary text-white">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-envelope me-2"></i> Packet Count
                        </h5>
                        <div class="d-flex align-items-center">
                            <span class="metric-value" id="packet-count-value">--</span>
                            <span class="trend-indicator" id="packet-count-trend">
                                <i class="fas fa-minus"></i>
                            </span>
                        </div>
                        <div class="small mt-2">Last 10 minutes</div>
                    </div>
                </div>
            </div>
            
            <!-- Error Rate -->
            <div class="col-md-4">
                <div class="card metric-card bg-danger text-white">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-exclamation-triangle me-2"></i> Error Rate
                        </h5>
                        <div class="d-flex align-items-center">
                            <span class="metric-value" id="error-rate-value">--</span>
                            <span class="trend-indicator" id="error-rate-trend">
                                <i class="fas fa-minus"></i>
                            </span>
                        </div>
                        <div class="small mt-2">% of total traffic</div>
                    </div>
                </div>
            </div>
            
            <!-- Avg Response Time -->
            <div class="col-md-4">
                <div class="card metric-card bg-success text-white">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-stopwatch me-2"></i> Avg Response Time
                        </h5>
                        <div class="d-flex align-items-center">
                            <span class="metric-value" id="response-time-value">--</span>
                            <span class="trend-indicator" id="response-time-trend">
                                <i class="fas fa-minus"></i>
                            </span>
                        </div>
                        <div class="small mt-2">milliseconds</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Chart Tabs -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card metric-card">
                    <div class="card-header bg-light">
                        <ul class="nav nav-tabs card-header-tabs" id="chartTabs" role="tablist">
                            <li class="nav-item" role="presentation">
                                <button class="nav-link active" id="count-tab" data-bs-toggle="tab" 
                                        data-bs-target="#count-chart" type="button" role="tab" 
                                        aria-controls="count-chart" aria-selected="true">
                                    Packet Count
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="size-tab" data-bs-toggle="tab" 
                                        data-bs-target="#size-chart" type="button" role="tab" 
                                        aria-controls="size-chart" aria-selected="false">
                                    Packet Size
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="error-tab" data-bs-toggle="tab" 
                                        data-bs-target="#error-chart" type="button" role="tab" 
                                        aria-controls="error-chart" aria-selected="false">
                                    Error Rate
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="response-tab" data-bs-toggle="tab" 
                                        data-bs-target="#response-chart" type="button" role="tab" 
                                        aria-controls="response-chart" aria-selected="false">
                                    Response Time
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="protocol-tab" data-bs-toggle="tab" 
                                        data-bs-target="#protocol-chart" type="button" role="tab" 
                                        aria-controls="protocol-chart" aria-selected="false">
                                    Protocol Distribution
                                </button>
                            </li>
                        </ul>
                    </div>
                    <div class="card-body">
                        <div class="tab-content" id="chartTabContent">
                            <!-- Count Chart -->
                            <div class="tab-pane fade show active" id="count-chart" role="tabpanel" aria-labelledby="count-tab">
                                <div class="chart-container">
                                    <canvas id="countChart"></canvas>
                                </div>
                            </div>
                            
                            <!-- Size Chart -->
                            <div class="tab-pane fade" id="size-chart" role="tabpanel" aria-labelledby="size-tab">
                                <div class="chart-container">
                                    <canvas id="sizeChart"></canvas>
                                </div>
                            </div>
                            
                            <!-- Error Chart -->
                            <div class="tab-pane fade" id="error-chart" role="tabpanel" aria-labelledby="error-tab">
                                <div class="chart-container">
                                    <canvas id="errorChart"></canvas>
                                </div>
                            </div>
                            
                            <!-- Response Time Chart -->
                            <div class="tab-pane fade" id="response-chart" role="tabpanel" aria-labelledby="response-tab">
                                <div class="chart-container">
                                    <canvas id="responseChart"></canvas>
                                </div>
                            </div>
                            
                            <!-- Protocol Distribution Chart -->
                            <div class="tab-pane fade" id="protocol-chart" role="tabpanel" aria-labelledby="protocol-tab">
                                <div class="chart-container">
                                    <canvas id="protocolChart"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Metrics Detail Table -->
        <div class="row">
            <div class="col-12">
                <div class="card metric-card">
                    <div class="card-header bg-light">
                        <h5 class="mb-0">
                            <i class="fas fa-table me-2"></i> Detailed Metrics
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>Metric</th>
                                        <th>Current Value</th>
                                        <th>Min</th>
                                        <th>Max</th>
                                        <th>Average</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody id="metrics-table-body">
                                    <!-- Populated by JavaScript -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Bootstrap Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <!-- Custom JavaScript -->
    <script>
        // Constants and variables
        const KEY = "{{key}}";
        const REFRESH_INTERVAL = 10000; // 10 seconds
        let charts = {};
        let lastData = {};
        
        // Initialize charts when page loads
        document.addEventListener('DOMContentLoaded', function() {
            initCharts();
            loadData();
            
            // Set up auto-refresh
            setInterval(loadData, REFRESH_INTERVAL);
        });
        
        // Initialize all charts
        function initCharts() {
            // Packet Count Chart
            charts.count = new Chart(
                document.getElementById('countChart'),
                {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [{
                            label: 'Packet Count',
                            data: [],
                            borderColor: 'rgba(13, 110, 253, 1)',
                            backgroundColor: 'rgba(13, 110, 253, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: { display: true, text: 'Packet Count Over Time' }
                        },
                        scales: {
                            y: { beginAtZero: true }
                        }
                    }
                }
            );
            
            // Packet Size Chart
            charts.size = new Chart(
                document.getElementById('sizeChart'),
                {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [
                            {
                                label: 'Average Size',
                                data: [],
                                borderColor: 'rgba(40, 167, 69, 1)',
                                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                                borderWidth: 2,
                                fill: false,
                                tension: 0.4
                            },
                            {
                                label: 'Min Size',
                                data: [],
                                borderColor: 'rgba(23, 162, 184, 1)',
                                backgroundColor: 'rgba(23, 162, 184, 0.1)',
                                borderWidth: 1,
                                fill: false,
                                tension: 0.4
                            },
                            {
                                label: 'Max Size',
                                data: [],
                                borderColor: 'rgba(220, 53, 69, 1)',
                                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                                borderWidth: 1,
                                fill: false,
                                tension: 0.4
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: { display: true, text: 'Packet Size Over Time (Bytes)' }
                        },
                        scales: {
                            y: { beginAtZero: true }
                        }
                    }
                }
            );
            
            // Error Rate Chart
            charts.error = new Chart(
                document.getElementById('errorChart'),
                {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [{
                            label: 'Error Rate (%)',
                            data: [],
                            borderColor: 'rgba(220, 53, 69, 1)',
                            backgroundColor: 'rgba(220, 53, 69, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: { display: true, text: 'Error Rate Over Time (%)' }
                        },
                        scales: {
                            y: { 
                                beginAtZero: true,
                                max: 100
                            }
                        }
                    }
                }
            );
            
            // Response Time Chart
            charts.response = new Chart(
                document.getElementById('responseChart'),
                {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [
                            {
                                label: 'Average Response Time',
                                data: [],
                                borderColor: 'rgba(40, 167, 69, 1)',
                                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                                borderWidth: 2,
                                fill: false,
                                tension: 0.4
                            },
                            {
                                label: '95th Percentile',
                                data: [],
                                borderColor: 'rgba(255, 193, 7, 1)',
                                backgroundColor: 'rgba(255, 193, 7, 0.1)',
                                borderWidth: 1,
                                fill: false,
                                tension: 0.4
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: { display: true, text: 'Response Time (ms)' }
                        },
                        scales: {
                            y: { beginAtZero: true }
                        }
                    }
                }
            );
            
            // Protocol Distribution Chart
            charts.protocol = new Chart(
                document.getElementById('protocolChart'),
                {
                    type: 'doughnut',
                    data: {
                        labels: [],
                        datasets: [{
                            data: [],
                            backgroundColor: [
                                'rgba(13, 110, 253, 0.7)',
                                'rgba(40, 167, 69, 0.7)',
                                'rgba(220, 53, 69, 0.7)',
                                'rgba(255, 193, 7, 0.7)',
                                'rgba(23, 162, 184, 0.7)',
                                'rgba(111, 66, 193, 0.7)',
                                'rgba(102, 16, 242, 0.7)',
                                'rgba(0, 123, 255, 0.7)',
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: { 
                                display: true, 
                                text: 'Protocol Distribution' 
                            },
                            legend: {
                                position: 'right'
                            }
                        }
                    }
                }
            );
        }
        
        // Load data from API
        function loadData() {
            fetch(`/api/metrics/${KEY}`)
                .then(response => response.json())
                .then(data => {
                    updateCharts(data);
                    updateSummaryCards(data);
                    updateMetricsTable(data);
                    lastData = data;
                })
                .catch(error => {
                    console.error('Error fetching metrics data:', error);
                });
        }
        
        // Update charts with new data
        function updateCharts(data) {
            // Common function to format timestamps
            const formatTimestamp = (timestamp) => {
                const date = new Date(timestamp * 1000);
                return date.toLocaleTimeString();
            };
            
            // Update Count Chart
            if (data.count && data.count.samples) {
                const samples = data.count.samples;
                const timestamps = samples.map(s => formatTimestamp(s[0]));
                const values = samples.map(s => s[1]);
                
                charts.count.data.labels = timestamps;
                charts.count.data.datasets[0].data = values;
                charts.count.update();
            }
            
            // Update Size Chart
            if (data.size && data.size.samples) {
                const samples = data.size.samples;
                const timestamps = samples.map(s => formatTimestamp(s[0]));
                const avgValues = samples.map(s => s[1].avg || 0);
                const minValues = samples.map(s => s[1].min || 0);
                const maxValues = samples.map(s => s[1].max || 0);
                
                charts.size.data.labels = timestamps;
                charts.size.data.datasets[0].data = avgValues;
                charts.size.data.datasets[1].data = minValues;
                charts.size.data.datasets[2].data = maxValues;
                charts.size.update();
            }
            
            // Update Error Rate Chart
            if (data.error_rate && data.error_rate.samples) {
                const samples = data.error_rate.samples;
                const timestamps = samples.map(s => formatTimestamp(s[0]));
                const values = samples.map(s => s[1].rate || 0);
                
                charts.error.data.labels = timestamps;
                charts.error.data.datasets[0].data = values;
                charts.error.update();
            }
            
            // Update Response Time Chart
            if (data.response_time && data.response_time.samples) {
                const samples = data.response_time.samples;
                const timestamps = samples.map(s => formatTimestamp(s[0]));
                const avgValues = samples.map(s => s[1].avg || 0);
                const p95Values = samples.map(s => s[1].p95 || 0);
                
                charts.response.data.labels = timestamps;
                charts.response.data.datasets[0].data = avgValues;
                charts.response.data.datasets[1].data = p95Values;
                charts.response.update();
            }
            
            // Update Protocol Distribution Chart
            if (data.protocol && data.protocol.current) {
                const protocolData = data.protocol.current;
                if (protocolData.protocols) {
                    const labels = Object.keys(protocolData.protocols);
                    const values = labels.map(label => protocolData.protocols[label].percentage || 0);
                    
                    charts.protocol.data.labels = labels;
                    charts.protocol.data.datasets[0].data = values;
                    charts.protocol.update();
                }
            }
        }
        
        // Update summary cards with latest values
        function updateSummaryCards(data) {
            // Packet Count
            if (data.count && data.count.current) {
                document.getElementById('packet-count-value').textContent = data.count.current;
                updateTrendIndicator('packet-count-trend', getTrend(data.count.samples, 'count'));
            }
            
            // Error Rate
            if (data.error_rate && data.error_rate.current) {
                const errorRate = data.error_rate.current.rate || 0;
                document.getElementById('error-rate-value').textContent = errorRate.toFixed(2) + '%';
                updateTrendIndicator('error-rate-trend', getTrend(data.error_rate.samples, 'error_rate'), true);
            }
            
            // Response Time
            if (data.response_time && data.response_time.current) {
                const avgResponseTime = data.response_time.current.avg || 0;
                document.getElementById('response-time-value').textContent = avgResponseTime.toFixed(2) + 'ms';
                updateTrendIndicator('response-time-trend', getTrend(data.response_time.samples, 'response_time'), true);
            }
        }
        
        // Update metrics table with detailed information
        function updateMetricsTable(data) {
            const tableBody = document.getElementById('metrics-table-body');
            tableBody.innerHTML = '';
            
            // Add packet count
            if (data.count) {
                addMetricRow(tableBody, 'Packet Count', data.count.current, null, null, null, 'count');
            }
            
            // Add size metrics
            if (data.size && data.size.current) {
                const size = data.size.current;
                addMetricRow(tableBody, 'Avg Packet Size', size.avg, size.min, size.max, null, 'size');
            }
            
            // Add error rate
            if (data.error_rate && data.error_rate.current) {
                const errorRate = data.error_rate.current;
                addMetricRow(tableBody, 'Error Rate', errorRate.rate + '%', null, null, 
                            `${errorRate.errors} errors / ${errorRate.total} packets`, 'error_rate');
            }
            
            // Add response time
            if (data.response_time && data.response_time.current) {
                const responseTime = data.response_time.current;
                addMetricRow(tableBody, 'Avg Response Time', responseTime.avg + 'ms', 
                            responseTime.min + 'ms', responseTime.max + 'ms', null, 'response_time');
                
                if (responseTime.p95) {
                    addMetricRow(tableBody, '95th Percentile Response Time', responseTime.p95 + 'ms', null, null, null, 'response_time');
                }
            }
            
            // Add protocol distribution
            if (data.protocol && data.protocol.current && data.protocol.current.protocols) {
                const protocols = data.protocol.current.protocols;
                Object.keys(protocols).forEach(protocol => {
                    const protocolData = protocols[protocol];
                    addMetricRow(tableBody, `Protocol: ${protocol}`, 
                                protocolData.percentage.toFixed(2) + '%', null, null, 
                                `${protocolData.count} packets`, 'protocol');
                });
            }
            
            // Add connection metrics
            if (data.connection && data.connection.current) {
                const connection = data.connection.current;
                addMetricRow(tableBody, 'New Connections', connection.new_connections, null, null, null, 'connection');
                addMetricRow(tableBody, 'Active Connections', connection.active_connections, null, null, null, 'connection');
                if (connection.avg_duration) {
                    addMetricRow(tableBody, 'Avg Connection Duration', connection.avg_duration.toFixed(2) + 's', null, null, null, 'connection');
                }
            }
        }
        
        // Helper function to add a row to the metrics table
        function addMetricRow(tableBody, name, value, min, max, details, metricType) {
            const row = document.createElement('tr');
            
            // Determine status based on thresholds (simplified example)
            let status = 'Normal';
            let statusClass = 'success';
            
            // Add cells to the row
            row.innerHTML = `
                <td>${name}</td>
                <td>${value || '-'}</td>
                <td>${min || '-'}</td>
                <td>${max || '-'}</td>
                <td>${details || '-'}</td>
                <td><span class="badge bg-${statusClass}">${status}</span></td>
            `;
            
            tableBody.appendChild(row);
        }
        
        // Calculate trend from samples
        function getTrend(samples, metricType) {
            if (!samples || samples.length < 2) {
                return 'neutral';
            }
            
            // Get the last two samples
            const lastSample = samples[samples.length - 1];
            const previousSample = samples[samples.length - 2];
            
            // Extract values based on metric type
            let lastValue, previousValue;
            
            if (metricType === 'count') {
                lastValue = lastSample[1];
                previousValue = previousSample[1];
            } else if (metricType === 'error_rate') {
                lastValue = lastSample[1].rate || 0;
                previousValue = previousSample[1].rate || 0;
            } else if (metricType === 'response_time') {
                lastValue = lastSample[1].avg || 0;
                previousValue = previousSample[1].avg || 0;
            } else {
                return 'neutral';
            }
            
            // Calculate percentage change
            const change = lastValue - previousValue;
            const percentChange = previousValue !== 0 ? (change / previousValue) * 100 : 0;
            
            // Determine trend direction (using 5% threshold for significance)
            if (percentChange > 5) {
                return 'up';
            } else if (percentChange < -5) {
                return 'down';
            } else {
                return 'neutral';
            }
        }
        
        // Update trend indicator icon and color
        function updateTrendIndicator(elementId, trend, inverse = false) {
            const element = document.getElementById(elementId);
            if (!element) return;
            
            let iconClass, colorClass;
            
            if (trend === 'up') {
                iconClass = 'fa-arrow-up';
                colorClass = inverse ? 'trend-down' : 'trend-up';
            } else if (trend === 'down') {
                iconClass = 'fa-arrow-down';
                colorClass = inverse ? 'trend-up' : 'trend-down';
            } else {
                iconClass = 'fa-minus';
                colorClass = 'trend-neutral';
            }
            
            element.innerHTML = `<i class="fas ${iconClass}"></i>`;
            element.className = `trend-indicator ${colorClass}`;
        }
    </script>
</body>
</html> 