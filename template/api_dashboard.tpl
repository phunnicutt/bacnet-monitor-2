<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    
    <title>BACmon API Dashboard</title>
    <link rel="stylesheet" href="/static/default.css" type="text/css" />
    <link rel="stylesheet" href="/static/pygments.css" type="text/css" />
    <link rel="stylesheet" href="/static/api-dashboard.css" type="text/css" />
    <script type="text/javascript" src="/static/js/jquery.js"></script>
    <script type="text/javascript" src="/static/js/moment.min.js"></script>
    <script type="text/javascript" src="/static/js/chart.min.js"></script>
    <script type="text/javascript" src="/static/js/api-client.js"></script>
    <script type="text/javascript" src="/static/js/api-dashboard.js"></script>
    <link rel="top" title="BACnet VLAN Monitor" href="#" />
  </head>
  <body>
    <div class="related">
      <h3>Navigation</h3>
      <ul>
        <li class="right" style="margin-right: 10px">
          <a href="/" title="Welcome">home</a></li>
        <li class="right" >
          <a href="/help" title="Help">help</a> |</li>
        <li><a href="/">BACnet LAN Monitor</a> &raquo;</li>
        <li><a href="/api-dashboard">API Dashboard</a> &raquo;</li>
      </ul>
    </div>

    <div class="document">
      <div class="documentwrapper">
        <div class="bodywrapper">
          <div class="body">

            <div class="section">
              <h1>{{title}}</h1>
              
              <!-- System Status Panel -->
              <div class="api-panel" id="status-panel">
                <h2>System Status</h2>
                <div class="status-grid">
                  <div class="status-card" id="redis-status">
                    <h3>Redis</h3>
                    <span class="status-indicator" id="redis-indicator">●</span>
                    <span class="status-text" id="redis-text">Checking...</span>
                  </div>
                  <div class="status-card" id="daemon-status">
                    <h3>BACmon Daemon</h3>
                    <span class="status-indicator" id="daemon-indicator">●</span>
                    <span class="status-text" id="daemon-text">Checking...</span>
                  </div>
                  <div class="status-card" id="anomaly-status">
                    <h3>Anomaly Detection</h3>
                    <span class="status-indicator" id="anomaly-indicator">●</span>
                    <span class="status-text" id="anomaly-text">Checking...</span>
                  </div>
                  <div class="status-card" id="alerts-status">
                    <h3>Alert System</h3>
                    <span class="status-indicator" id="alerts-indicator">●</span>
                    <span class="status-text" id="alerts-text">Checking...</span>
                  </div>
                </div>
                <div class="status-details" id="status-details">
                  <h3>System Information</h3>
                  <div id="system-info"></div>
                </div>
              </div>

              <!-- Monitoring Data Panel -->
              <div class="api-panel" id="monitoring-panel">
                <h2>Real-time Monitoring</h2>
                <div class="controls">
                  <div class="control-group">
                    <label for="monitoring-range">Time Range:</label>
                    <select id="monitoring-range">
                      <option value="1h">Last Hour</option>
                      <option value="6h">Last 6 Hours</option>
                      <option value="24h" selected>Last 24 Hours</option>
                      <option value="7d">Last 7 Days</option>
                      <option value="30d">Last 30 Days</option>
                    </select>
                  </div>
                  <div class="control-group">
                    <label for="monitoring-keys">Keys Filter:</label>
                    <input type="text" id="monitoring-keys" placeholder="Enter comma-separated keys (optional)">
                  </div>
                  <button id="refresh-monitoring" class="btn">Refresh Data</button>
                </div>
                <div class="monitoring-content">
                  <div id="monitoring-chart-container">
                    <canvas id="monitoring-chart"></canvas>
                  </div>
                  <div id="monitoring-data-table"></div>
                </div>
              </div>

              <!-- Traffic Analysis Panel -->
              <div class="api-panel" id="traffic-panel">
                <h2>Network Traffic Analysis</h2>
                <div class="controls">
                  <div class="control-group">
                    <label for="traffic-range">Time Range:</label>
                    <select id="traffic-range">
                      <option value="1h">Last Hour</option>
                      <option value="6h">Last 6 Hours</option>
                      <option value="24h" selected>Last 24 Hours</option>
                      <option value="7d">Last 7 Days</option>
                    </select>
                  </div>
                  <div class="control-group">
                    <label for="traffic-type">Traffic Type:</label>
                    <select id="traffic-type">
                      <option value="">All Types</option>
                      <option value="ip">IP Traffic</option>
                      <option value="bvll">BVLL Traffic</option>
                      <option value="network">Network Traffic</option>
                      <option value="application">Application Traffic</option>
                      <option value="error">Error Traffic</option>
                    </select>
                  </div>
                  <button id="refresh-traffic" class="btn">Refresh Data</button>
                </div>
                <div class="traffic-content">
                  <div id="traffic-summary"></div>
                  <div id="traffic-chart-container">
                    <canvas id="traffic-chart"></canvas>
                  </div>
                  <div id="traffic-details"></div>
                </div>
              </div>

              <!-- Devices Panel -->
              <div class="api-panel" id="devices-panel">
                <h2>BACnet Devices</h2>
                <div class="controls">
                  <div class="control-group">
                    <label for="device-search">Search Devices:</label>
                    <input type="text" id="device-search" placeholder="Filter by device ID, name, or IP">
                  </div>
                  <div class="control-group">
                    <label for="device-sort">Sort By:</label>
                    <select id="device-sort">
                      <option value="deviceId">Device ID</option>
                      <option value="lastSeen">Last Seen</option>
                      <option value="name">Device Name</option>
                      <option value="network">Network</option>
                    </select>
                  </div>
                  <button id="refresh-devices" class="btn">Refresh Devices</button>
                </div>
                <div class="devices-content">
                  <div id="device-stats"></div>
                  <div id="devices-table"></div>
                </div>
              </div>

              <!-- Anomalies Panel -->
              <div class="api-panel" id="anomalies-panel">
                <h2>Anomaly Detection</h2>
                <div class="controls">
                  <div class="control-group">
                    <label for="anomaly-range">Time Range:</label>
                    <select id="anomaly-range">
                      <option value="1h">Last Hour</option>
                      <option value="6h">Last 6 Hours</option>
                      <option value="24h" selected>Last 24 Hours</option>
                      <option value="7d">Last 7 Days</option>
                    </select>
                  </div>
                  <div class="control-group">
                    <label for="anomaly-severity">Severity:</label>
                    <select id="anomaly-severity">
                      <option value="">All Severities</option>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>
                  <button id="refresh-anomalies" class="btn">Refresh Anomalies</button>
                </div>
                <div class="anomalies-content">
                  <div id="anomaly-summary"></div>
                  <div id="anomalies-list"></div>
                </div>
              </div>

              <!-- Export Panel -->
              <div class="api-panel" id="export-panel">
                <h2>Data Export</h2>
                <div class="controls">
                  <div class="control-group">
                    <label for="export-type">Export Type:</label>
                    <select id="export-type">
                      <option value="monitoring">Monitoring Data</option>
                      <option value="traffic">Traffic Analysis</option>
                      <option value="devices">Device Information</option>
                      <option value="anomalies">Anomaly Data</option>
                    </select>
                  </div>
                  <div class="control-group">
                    <label for="export-format">Format:</label>
                    <select id="export-format">
                      <option value="json">JSON</option>
                      <option value="csv">CSV</option>
                    </select>
                  </div>
                  <div class="control-group">
                    <label for="export-range">Time Range:</label>
                    <select id="export-range">
                      <option value="1h">Last Hour</option>
                      <option value="6h">Last 6 Hours</option>
                      <option value="24h" selected>Last 24 Hours</option>
                      <option value="7d">Last 7 Days</option>
                      <option value="30d">Last 30 Days</option>
                    </select>
                  </div>
                  <button id="export-data" class="btn btn-primary">Export Data</button>
                </div>
                <div id="export-status"></div>
              </div>

            </div>

          </div>
        </div>
      </div>
      <div class="sphinxsidebar">
        <div class="sphinxsidebarwrapper">
            <h3>API Dashboard</h3>
            <ul>
                <li><a href="#status-panel">System Status</a>
                <li><a href="#monitoring-panel">Monitoring Data</a>
                <li><a href="#traffic-panel">Traffic Analysis</a>
                <li><a href="#devices-panel">BACnet Devices</a>
                <li><a href="#anomalies-panel">Anomalies</a>
                <li><a href="#export-panel">Data Export</a>
            </ul>

            <h3>Traditional Views</h3>
            <ul>
                <li><a class="reference external" href="/rate-monitoring">Rate Monitoring</a>
                <li><a class="reference external" href="/anomaly-summary">Anomaly Summary</a>
                <li><a class="reference external" href="/alerts">Alert Dashboard</a>
                <li><a class="reference external" href="/extended_metrics">Extended Metrics</a>
            </ul>
            
            <h3>Traffic By Type</h3>
            <ul>
                <li><a class="reference external" href="/ip-traffic">IP</a>
                <li><a class="reference external" href="/bvll-traffic">BVLL</a>
                <li><a class="reference external" href="/network-traffic">Network</a>
                <li><a class="reference external" href="/application-traffic">Application</a>
                <li><a class="reference external" href="/who-is-i-am-merged">Who-Is/I-Am Merged</a>
            </ul>

            <h4>Admin</h4>
            <ul>
                <li><a class="reference external" href="/info">Info</a>
                <li><a class="reference external" href="/flush">Flush</a>
                <li><a class="reference external" href="/clear-template">Clear Template</a>
            </ul>
        </div>
      </div>
      <div class="clearer"></div>
    </div>

    <div class="related">
      <h3>Navigation</h3>
      <ul>
        <li class="right" style="margin-right: 10px">
          <a href="/" title="Welcome">home</a></li>
        <li class="right" >
          <a href="/help" title="Help">help</a> |</li>
        <li><a href="/">BACnet LAN Monitor</a> &raquo;</li>
      </ul>
    </div>
    <div class="footer">
      &copy; Copyright 2012, Joel Bender. Enhanced with REST API Dashboard.
    </div>
  </body>
</html> 