<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BACmon - Network Monitoring Dashboard</title>
    
    <!-- Stylesheets -->
    <link rel="stylesheet" href="/static/default.css" type="text/css" />
    <link rel="stylesheet" href="/static/dashboard.css" type="text/css" />
    
    <!-- JavaScript Libraries -->
    <script src="/static/js/jquery.js"></script>
    <script src="/static/js/chart.min.js"></script>
    <script src="/static/js/moment.min.js"></script>
    <script src="/static/js/api-client.js"></script>
</head>
<body>
    <!-- Header Navigation -->
    <header class="dashboard-header">
        <div class="header-container">
            <div class="logo-section">
                <h1 class="dashboard-title">
                    <i class="icon-network"></i>
                    BACmon
                    <span class="subtitle">BACnet Network Monitor</span>
                </h1>
            </div>
            
            <nav class="main-navigation">
                <a href="/" class="nav-link active">Dashboard</a>
                <a href="/api-dashboard" class="nav-link">API Console</a>
                <a href="/rate-monitoring" class="nav-link">Rate Monitor</a>
                <a href="/alerts" class="nav-link">Alerts</a>
                <div class="nav-dropdown">
                    <span class="nav-link dropdown-toggle">Traffic <i class="arrow-down"></i></span>
                    <div class="dropdown-content">
                        <a href="/ip-traffic">IP Traffic</a>
                        <a href="/bvll-traffic">BVLL Traffic</a>
                        <a href="/network-traffic">Network Traffic</a>
                        <a href="/application-traffic">Application Traffic</a>
                    </div>
                </div>
                <div class="nav-dropdown">
                    <span class="nav-link dropdown-toggle">Admin <i class="arrow-down"></i></span>
                    <div class="dropdown-content">
                        <a href="/info">System Info</a>
                        <a href="/flush">Database Flush</a>
                        % if get('auth_user'):
                        <a href="/logout">Logout ({{auth_user}})</a>
                        % else:
                        <a href="/login">Login</a>
                        % end
                    </div>
                </div>
            </nav>
            
            <div class="status-indicators">
                <div class="status-indicator" id="system-status">
                    <span class="status-dot checking"></span>
                    <span class="status-text">System Status</span>
                </div>
                <div class="status-indicator" id="connection-status">
                    <span class="status-dot checking"></span>
                    <span class="status-text">Redis</span>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Dashboard Content -->
    <main class="dashboard-main">
        <!-- Quick Stats Cards -->
        <section class="stats-section">
            <div class="stats-container">
                <div class="stat-card" id="total-messages">
                    <div class="stat-icon">📊</div>
                    <div class="stat-content">
                        <div class="stat-value" id="total-messages-value">--</div>
                        <div class="stat-label">Total Messages</div>
                        <div class="stat-trend" id="total-messages-trend"></div>
                    </div>
                </div>
                
                <div class="stat-card" id="active-devices">
                    <div class="stat-icon">🔌</div>
                    <div class="stat-content">
                        <div class="stat-value" id="active-devices-value">--</div>
                        <div class="stat-label">Active Devices</div>
                        <div class="stat-trend" id="active-devices-trend"></div>
                    </div>
                </div>
                
                <div class="stat-card" id="alert-count">
                    <div class="stat-icon">🚨</div>
                    <div class="stat-content">
                        <div class="stat-value" id="alert-count-value">--</div>
                        <div class="stat-label">Active Alerts</div>
                        <div class="stat-trend" id="alert-count-trend"></div>
                    </div>
                </div>
                
                <div class="stat-card" id="system-uptime">
                    <div class="stat-icon">⏱️</div>
                    <div class="stat-content">
                        <div class="stat-value" id="system-uptime-value">--</div>
                        <div class="stat-label">System Uptime</div>
                        <div class="stat-trend" id="system-uptime-trend"></div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Main Content Grid -->
        <section class="dashboard-grid">
            <!-- Real-time Traffic Chart -->
            <div class="dashboard-widget large-widget">
                <div class="widget-header">
                    <h3 class="widget-title">Real-time Network Traffic</h3>
                    <div class="widget-controls">
                        <select id="traffic-timerange" class="time-selector">
                            <option value="1h">Last Hour</option>
                            <option value="6h">Last 6 Hours</option>
                            <option value="24h" selected>Last 24 Hours</option>
                            <option value="7d">Last 7 Days</option>
                        </select>
                        <button class="refresh-btn" id="refresh-traffic">🔄</button>
                    </div>
                </div>
                <div class="widget-content">
                    <canvas id="traffic-chart" width="800" height="300"></canvas>
                    <div class="chart-legend" id="traffic-legend"></div>
                </div>
            </div>

            <!-- Traffic by Type Breakdown -->
            <div class="dashboard-widget">
                <div class="widget-header">
                    <h3 class="widget-title">Traffic by Type</h3>
                    <button class="refresh-btn" id="refresh-traffic-breakdown">🔄</button>
                </div>
                <div class="widget-content">
                    <canvas id="traffic-breakdown-chart" width="400" height="250"></canvas>
                    <div class="traffic-stats" id="traffic-stats"></div>
                </div>
            </div>

            <!-- Recent Alerts -->
            <div class="dashboard-widget">
                <div class="widget-header">
                    <h3 class="widget-title">Recent Alerts</h3>
                    <a href="/alerts" class="view-all-link">View All</a>
                </div>
                <div class="widget-content">
                    <div class="alerts-list" id="recent-alerts">
                        <!-- Alerts will be populated here -->
                    </div>
                </div>
            </div>

            <!-- System Health -->
            <div class="dashboard-widget">
                <div class="widget-header">
                    <h3 class="widget-title">System Health</h3>
                    <button class="refresh-btn" id="refresh-system-health">🔄</button>
                </div>
                <div class="widget-content">
                    <div class="health-metrics" id="health-metrics">
                        <div class="health-item">
                            <span class="health-label">Redis Connection</span>
                            <span class="health-status" id="redis-health">Checking...</span>
                        </div>
                        <div class="health-item">
                            <span class="health-label">BACmon Daemon</span>
                            <span class="health-status" id="daemon-health">Checking...</span>
                        </div>
                        <div class="health-item">
                            <span class="health-label">Alert System</span>
                            <span class="health-status" id="alert-system-health">Checking...</span>
                        </div>
                        <div class="health-item">
                            <span class="health-label">Memory Usage</span>
                            <span class="health-status" id="memory-health">Checking...</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Top Devices -->
            <div class="dashboard-widget">
                <div class="widget-header">
                    <h3 class="widget-title">Top Active Devices</h3>
                    <a href="/devices" class="view-all-link">View All</a>
                </div>
                <div class="widget-content">
                    <div class="devices-list" id="top-devices">
                        <!-- Top devices will be populated here -->
                    </div>
                </div>
            </div>

            <!-- Monitoring Keys Activity -->
            <div class="dashboard-widget">
                <div class="widget-header">
                    <h3 class="widget-title">Monitoring Activity</h3>
                    <button class="refresh-btn" id="refresh-monitoring">🔄</button>
                </div>
                <div class="widget-content">
                    <div class="monitoring-list" id="monitoring-activity">
                        <!-- Monitoring keys will be populated here -->
                    </div>
                </div>
            </div>
        </section>

        <!-- Quick Actions Panel -->
        <section class="quick-actions">
            <div class="actions-container">
                <h3>Quick Actions</h3>
                <div class="action-buttons">
                    <button class="action-btn primary" onclick="window.location.href='/api-dashboard'">
                        <i class="icon">🔧</i>
                        API Console
                    </button>
                    <button class="action-btn secondary" onclick="window.location.href='/rate-monitoring'">
                        <i class="icon">📈</i>
                        Rate Monitor
                    </button>
                    <button class="action-btn secondary" onclick="window.location.href='/alerts'">
                        <i class="icon">🚨</i>
                        Alerts
                    </button>
                    <button class="action-btn secondary" onclick="exportData()">
                        <i class="icon">💾</i>
                        Export Data
                    </button>
                </div>
            </div>
        </section>
    </main>

    <!-- Footer -->
    <footer class="dashboard-footer">
        <div class="footer-content">
            <div class="footer-left">
                <span>BACmon v{{version or '1.0.0'}} - Enhanced BACnet Network Monitor</span>
            </div>
            <div class="footer-right">
                <span>Last Updated: <span id="last-updated">--</span></span>
                <span class="separator">|</span>
                <span>Auto-refresh: <span id="auto-refresh-status">ON</span></span>
            </div>
        </div>
    </footer>

    <!-- Dashboard JavaScript -->
    <script src="/static/js/dashboard.js"></script>
</body>
</html> 