<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    
    <title>BACnet Rate Monitoring</title>
    <link rel="stylesheet" href="/static/default.css" type="text/css" />
    <link rel="stylesheet" href="/static/pygments.css" type="text/css" />
    
    <!-- Include standard jQuery -->
    <script type="text/javascript" src="/static/js/jquery.js"></script>
    
    <!-- Include Chart.js and Moment.js for modern visualizations -->
    <script type="text/javascript" src="/static/js/chart.min.js"></script>
    <script type="text/javascript" src="/static/js/moment.min.js"></script>
    
    <!-- Include custom rate monitoring visualization script -->
    <script type="text/javascript" src="/static/js/rate-monitoring.js"></script>
    
    <!-- Legacy scripts for compatibility -->
    <script type="text/javascript" src="/static/js/jquery.flot.js"></script>
    <script type="text/javascript" src="/static/js/jquery.flot.selection.js"></script>
    <script type="text/javascript" src="/static/js/jquery.strftime.js"></script>
    <!--[if IE]><script type="text/javascript" src="/static/js/excanvas.js"></script><![endif]-->
    
    <link rel="top" title="BACnet Rate Monitoring" href="#" />
    <link rel="next" title="Introduction" href="intro.html" /> 
    
    <style>
      /* Additional styles for enhanced visualization */
      .chart-container {
        width: 100%;
        height: 400px;
        margin-bottom: 30px;
        position: relative;
      }
      
      .chart-row {
        display: flex;
        flex-wrap: wrap;
        margin: 0 -15px;
      }
      
      .chart-column {
        flex: 1;
        padding: 0 15px;
        min-width: 300px;
      }
      
      .chart-container canvas {
        width: 100% !important;
        height: 100% !important;
      }
      
      .chart-info {
        margin: 10px 0;
        padding: 10px;
        background-color: #f5f5f5;
        border-radius: 4px;
      }
      
      .anomaly-indicator {
        display: inline-block;
        padding: 3px 8px;
        margin-right: 5px;
        margin-bottom: 5px;
        border-radius: 4px;
        background-color: rgba(255, 99, 132, 0.6);
        color: #fff;
      }
      
      .anomaly-indicator.threshold {
        background-color: rgba(255, 159, 64, 0.8);
      }
      
      .anomaly-indicator.statistical {
        background-color: rgba(153, 102, 255, 0.6);
      }
      
      .anomaly-indicator.trend {
        background-color: rgba(54, 162, 235, 0.6);
      }
      
      .anomaly-indicator.time-pattern {
        background-color: rgba(255, 206, 86, 0.6);
      }
      
      .data-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
      }
      
      .data-table th, .data-table td {
        padding: 8px;
        border: 1px solid #ddd;
        text-align: left;
      }
      
      .data-table th {
        background-color: #f2f2f2;
      }
      
      .data-table tr:nth-child(even) {
        background-color: #f9f9f9;
      }
      
      .data-table tr.anomaly {
        background-color: rgba(255, 99, 132, 0.1);
      }
      
      .controls {
        margin-bottom: 20px;
      }
      
      .controls select, .controls input, .controls button {
        padding: 5px 10px;
        margin-right: 10px;
      }
      
      .summary-box {
        background-color: #f8f9fa;
        border-radius: 4px;
        padding: 15px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      }
      
      .summary-value {
        font-size: 24px;
        font-weight: bold;
        margin: 10px 0;
      }
      
      .summary-label {
        font-size: 14px;
        color: #666;
      }
      
      /* Hide data elements */
      .chart-data {
        display: none;
      }
    </style>
  </head>
  <body>
    <div class="related">
      <h3>Navigation</h3>
      <ul>
        <li class="right" style="margin-right: 10px">
          <a href="/" title="Welcome">home</a></li>
        <li class="right" >
          <a href="/help" title="IP">help</a> |</li>
        <li><a href="/">BACnet LAN Monitor</a> &raquo;</li> 
      </ul>
    </div>

    <div class="document">
      <div class="documentwrapper">
        <div class="bodywrapper">
          <div class="body">

            <div class="section">
              <h1>{{title}}</h1>
              
              <!-- Summary statistics -->
              <div class="chart-row">
                <div class="chart-column">
                  <div class="summary-box">
                    <div class="summary-label">Total Samples</div>
                    <div class="summary-value">{{summary.total_samples}}</div>
                  </div>
                </div>
                <div class="chart-column">
                  <div class="summary-box">
                    <div class="summary-label">Anomalies Detected</div>
                    <div class="summary-value">{{summary.total_anomalies}}</div>
                  </div>
                </div>
                <div class="chart-column">
                  <div class="summary-box">
                    <div class="summary-label">Current Status</div>
                    <div class="summary-value" style="color: {{summary.status_color}}">{{summary.status}}</div>
                  </div>
                </div>
                <div class="chart-column">
                  <div class="summary-box">
                    <div class="summary-label">Last Anomaly</div>
                    <div class="summary-value">{{summary.last_anomaly_time}}</div>
                  </div>
                </div>
              </div>
              
              <!-- Controls for time range and key selection -->
              <div class="controls">
                <form action="/rate-monitoring" method="get">
                  <label for="key">Monitoring Key:</label>
                  <select name="key" id="key">
                    % for k in available_keys:
                    <option value="{{k}}" {{'selected' if k == key else ''}}>{{k}}</option>
                    % end
                  </select>
                  
                  <label for="timerange">Time Range:</label>
                  <select name="timerange" id="timerange">
                    <option value="1h" {{'selected' if timerange == '1h' else ''}}>Last Hour</option>
                    <option value="6h" {{'selected' if timerange == '6h' else ''}}>Last 6 Hours</option>
                    <option value="12h" {{'selected' if timerange == '12h' else ''}}>Last 12 Hours</option>
                    <option value="24h" {{'selected' if timerange == '24h' else ''}}>Last 24 Hours</option>
                    <option value="7d" {{'selected' if timerange == '7d' else ''}}>Last 7 Days</option>
                  </select>
                  
                  <button type="submit">Update</button>
                </form>
              </div>
              
              <!-- Main rate chart -->
              <h2>Rate Monitoring Chart</h2>
              <div class="chart-container">
                <canvas id="rate-chart"></canvas>
              </div>
              
              <!-- JSON data for the rate chart -->
              <script id="rate-chart-data" type="application/json" class="chart-data">
                {{rate_chart_data}}
              </script>
              
              <!-- Anomaly history chart -->
              <h2>Anomaly History</h2>
              % if len(anomalies) > 0:
              <div class="chart-container">
                <canvas id="anomaly-chart"></canvas>
              </div>
              
              <!-- JSON data for the anomaly chart -->
              <script id="anomaly-chart-data" type="application/json" class="chart-data">
                {{anomaly_chart_data}}
              </script>
              
              <!-- Anomaly distribution charts -->
              <div class="chart-row">
                <div class="chart-column">
                  <h3>Anomaly Type Distribution</h3>
                  <div class="chart-container" style="height: 300px;">
                    <canvas id="anomaly-type-chart"></canvas>
                  </div>
                  
                  <!-- JSON data for the anomaly type chart -->
                  <script id="anomaly-type-chart-data" type="application/json" class="chart-data">
                    {{anomaly_type_data}}
                  </script>
                </div>
                
                <div class="chart-column">
                  <h3>Time of Day Distribution</h3>
                  <div class="chart-container" style="height: 300px;">
                    <canvas id="time-distribution-chart"></canvas>
                  </div>
                  
                  <!-- JSON data for the time distribution chart -->
                  <script id="time-distribution-chart-data" type="application/json" class="chart-data">
                    {{time_distribution_data}}
                  </script>
                </div>
              </div>
              
              <!-- Anomaly list -->
              <h3>Recent Anomalies</h3>
              <div class="chart-info">
                <p>Legend:</p>
                <span class="anomaly-indicator threshold">Threshold</span>
                <span class="anomaly-indicator">Spike</span>
                <span class="anomaly-indicator statistical">Statistical (Z-score)</span>
                <span class="anomaly-indicator trend">Trend</span>
                <span class="anomaly-indicator time-pattern">Time Pattern</span>
              </div>
              
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Value</th>
                    <th>Anomaly Types</th>
                    <th>Score</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  % for anomaly in anomalies:
                  <tr class="anomaly">
                    <td>{{anomaly.time_str}}</td>
                    <td>{{anomaly.value}}</td>
                    <td>
                      % for atype in anomaly.types:
                      <span class="anomaly-indicator {{atype if atype in ['threshold', 'statistical', 'trend', 'time-pattern'] else ''}}">{{atype}}</span>
                      % end
                    </td>
                    <td>{{anomaly.score}}</td>
                    <td>
                      <a href="/anomaly-detail/{{key}}/{{anomaly.timestamp}}">Details</a>
                    </td>
                  </tr>
                  % end
                </tbody>
              </table>
              % else:
              <p>No anomalies detected in the selected time period.</p>
              % end
              
              <!-- Recent data samples -->
              <h3>Recent Data Samples</h3>
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Value</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  % for sample in recent_samples:
                  <tr class="{{'anomaly' if sample.is_anomaly else ''}}">
                    <td>{{sample.time_str}}</td>
                    <td>{{sample.value}}</td>
                    <td>{{sample.status}}</td>
                  </tr>
                  % end
                </tbody>
              </table>
              
              <!-- Include any additional content from the body -->
              {{!body}}
            </div>

          </div>
        </div>
      </div>
      <div class="sphinxsidebar">
        <div class="sphinxsidebarwrapper">
            <h3>Enhanced Monitoring</h3>
            <ul>
                <li><a class="reference external" href="/rate-monitoring">Rate Monitoring Dashboard</a>
                <li><a class="reference external" href="/anomaly-summary">Anomaly Summary</a>
            </ul>
            
            <h3>Traffic By Type</h3>
            <ul>
                <li><a class="reference external" href="/ip-traffic">IP</a>
                <li><a class="reference external" href="/bvll-traffic">BVLL</a>
                <li><a class="reference external" href="/network-traffic">Network</a>
                <li><a class="reference external" href="/application-traffic">Application</a>
                <li><a class="reference external" href="/who-is-i-am-merged">Who-Is/I-Am Merged</a>
            </ul>

            <h3>Messages</h3>
            <ul>
                <li><a class="reference external" href="/critical-messages">Critical</a>
                <li><a class="reference external" href="/alert-messages">Alert</a>
                <li><a class="reference external" href="/warning-messages">Warning</a>
            </ul>

            <h4>Other</h4>
            <ul>
                <li><a class="reference external" href="/undefined-devices">Undefined devices</a>
                <li><a class="reference external" href="/error-traffic">Errors</a>
                <li><a class="reference external" href="/log">Capture Files</a>
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
          <a href="/help" title="IP">help</a> |</li>
        <li><a href="/">BACnet LAN Monitor</a> &raquo;</li> 
      </ul>
    </div>
    <div class="footer">
      &copy; Copyright 2023, BACmon Team.
    </div>
  </body>
</html> 