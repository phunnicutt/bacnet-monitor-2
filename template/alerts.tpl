%include basic title="BACmon Alerts", scripts=scripts, stylesheets=stylesheets

<div class="container-fluid">
  <div class="row">
    <div class="col-lg-12">
      <h1 class="mt-4">Rate Alerts Dashboard</h1>
      <p class="lead">Monitor and manage alerts for network traffic anomalies</p>
      
      <!-- Alert Summary Cards -->
      <div class="row mb-4">
        <div class="col-xl-3 col-md-6">
          <div class="card bg-primary text-white mb-4">
            <div class="card-body">
              <h5>Active Alerts</h5>
              <h2 class="display-4">{{active_count}}</h2>
            </div>
            <div class="card-footer d-flex align-items-center justify-content-between">
              <a class="small text-white stretched-link" href="#active-alerts">View Details</a>
              <div class="small text-white"><i class="fas fa-angle-right"></i></div>
            </div>
          </div>
        </div>
        <div class="col-xl-3 col-md-6">
          <div class="card bg-warning text-white mb-4">
            <div class="card-body">
              <h5>Warnings</h5>
              <h2 class="display-4">{{warning_count}}</h2>
            </div>
            <div class="card-footer d-flex align-items-center justify-content-between">
              <a class="small text-white stretched-link" href="#warning-alerts">View Details</a>
              <div class="small text-white"><i class="fas fa-angle-right"></i></div>
            </div>
          </div>
        </div>
        <div class="col-xl-3 col-md-6">
          <div class="card bg-danger text-white mb-4">
            <div class="card-body">
              <h5>Critical</h5>
              <h2 class="display-4">{{critical_count}}</h2>
            </div>
            <div class="card-footer d-flex align-items-center justify-content-between">
              <a class="small text-white stretched-link" href="#critical-alerts">View Details</a>
              <div class="small text-white"><i class="fas fa-angle-right"></i></div>
            </div>
          </div>
        </div>
        <div class="col-xl-3 col-md-6">
          <div class="card bg-success text-white mb-4">
            <div class="card-body">
              <h5>Resolved</h5>
              <h2 class="display-4">{{resolved_count}}</h2>
            </div>
            <div class="card-footer d-flex align-items-center justify-content-between">
              <a class="small text-white stretched-link" href="#alert-history">View History</a>
              <div class="small text-white"><i class="fas fa-angle-right"></i></div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Alert Controls -->
      <div class="card mb-4">
        <div class="card-header">
          <i class="fas fa-cogs me-1"></i>
          Alert Management
        </div>
        <div class="card-body">
          <div class="row mb-3">
            <div class="col-md-6">
              <h5>Create Maintenance Window</h5>
              <form id="maintenance-form" method="post" action="/alerts/maintenance">
                <div class="mb-3">
                  <label for="maintenance-name" class="form-label">Name</label>
                  <input type="text" class="form-control" id="maintenance-name" name="name" required placeholder="Planned Maintenance">
                </div>
                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label for="start-time" class="form-label">Start Time</label>
                    <input type="datetime-local" class="form-control" id="start-time" name="start_time" required>
                  </div>
                  <div class="col-md-6 mb-3">
                    <label for="end-time" class="form-label">End Time</label>
                    <input type="datetime-local" class="form-control" id="end-time" name="end_time" required>
                  </div>
                </div>
                <div class="mb-3">
                  <label for="entity-patterns" class="form-label">Entity Patterns (optional)</label>
                  <input type="text" class="form-control" id="entity-patterns" name="entity_patterns" placeholder="ip-192.168,device-">
                  <div class="form-text">Comma-separated patterns to match entities</div>
                </div>
                <button type="submit" class="btn btn-primary">Create Maintenance Window</button>
              </form>
            </div>
            <div class="col-md-6">
              <h5>Active Maintenance Windows</h5>
              <div class="table-responsive">
                <table class="table table-striped">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Start</th>
                      <th>End</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    %for window in maintenance_windows:
                    <tr>
                      <td>{{window['name']}}</td>
                      <td>{{window['start_time_str']}}</td>
                      <td>{{window['end_time_str']}}</td>
                      <td>
                        %if window['active']:
                        <span class="badge bg-success">Active</span>
                        %else:
                        <span class="badge bg-secondary">Inactive</span>
                        %end
                      </td>
                      <td>
                        <form method="post" action="/alerts/maintenance/delete" style="display:inline;">
                          <input type="hidden" name="name" value="{{window['name']}}">
                          <button type="submit" class="btn btn-sm btn-danger">Delete</button>
                        </form>
                      </td>
                    </tr>
                    %end
                    %if not maintenance_windows:
                    <tr>
                      <td colspan="5" class="text-center">No active maintenance windows</td>
                    </tr>
                    %end
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  
  <!-- Active Alerts -->
  <div class="row">
    <div class="col-lg-12">
      <div class="card mb-4" id="active-alerts">
        <div class="card-header">
          <i class="fas fa-bell me-1"></i>
          Active Alerts
        </div>
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover" id="alerts-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Entity</th>
                  <th>Alert</th>
                  <th>Message</th>
                  <th>Level</th>
                  <th>Details</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                %for alert in active_alerts:
                <tr class="alert-row {{alert['level_str'].lower()}}">
                  <td>{{alert['time_str']}}</td>
                  <td>{{alert['entity'] or '-'}}</td>
                  <td>{{alert['key']}}</td>
                  <td>{{alert['message']}}</td>
                  <td>
                    <span class="badge {{alert['level_class']}}">{{alert['level_str']}}</span>
                  </td>
                  <td>
                    <button class="btn btn-sm btn-info view-details" data-alert-id="{{alert['uuid']}}">View</button>
                  </td>
                  <td>
                    %if not alert['acknowledged']:
                    <form method="post" action="/alerts/acknowledge" style="display:inline;">
                      <input type="hidden" name="uuid" value="{{alert['uuid']}}">
                      <button type="submit" class="btn btn-sm btn-warning">Acknowledge</button>
                    </form>
                    %else:
                    <span class="badge bg-info">Acknowledged</span>
                    %end
                    <form method="post" action="/alerts/resolve" style="display:inline;">
                      <input type="hidden" name="uuid" value="{{alert['uuid']}}">
                      <button type="submit" class="btn btn-sm btn-success">Resolve</button>
                    </form>
                  </td>
                </tr>
                %end
                %if not active_alerts:
                <tr>
                  <td colspan="7" class="text-center">No active alerts</td>
                </tr>
                %end
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
  
  <!-- Alert History -->
  <div class="row">
    <div class="col-lg-12">
      <div class="card mb-4" id="alert-history">
        <div class="card-header">
          <i class="fas fa-history me-1"></i>
          Alert History
        </div>
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover" id="history-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Entity</th>
                  <th>Alert</th>
                  <th>Message</th>
                  <th>Level</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                %for alert in alert_history:
                <tr>
                  <td>{{alert['time_str']}}</td>
                  <td>{{alert['entity'] or '-'}}</td>
                  <td>{{alert['key']}}</td>
                  <td>{{alert['message']}}</td>
                  <td>
                    <span class="badge {{alert['level_class']}}">{{alert['level_str']}}</span>
                  </td>
                  <td>
                    <button class="btn btn-sm btn-info view-details" data-alert-id="{{alert['uuid']}}">View</button>
                  </td>
                </tr>
                %end
                %if not alert_history:
                <tr>
                  <td colspan="6" class="text-center">No alert history available</td>
                </tr>
                %end
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Alert Details Modal -->
<div class="modal fade" id="alertDetailsModal" tabindex="-1" aria-labelledby="alertDetailsModalLabel" aria-hidden="true">
  <div class="modal-dialog modal-lg">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="alertDetailsModalLabel">Alert Details</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body" id="alert-details-content">
        <!-- Content loaded via JavaScript -->
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
      </div>
    </div>
  </div>
</div>

<script>
  document.addEventListener('DOMContentLoaded', function() {
    // Initialize current date/time for the maintenance window form
    const now = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(now.getDate() + 1);
    
    // Format dates for datetime-local input
    document.getElementById('start-time').value = formatDateForInput(now);
    document.getElementById('end-time').value = formatDateForInput(tomorrow);
    
    // Set up detail view buttons
    const detailButtons = document.querySelectorAll('.view-details');
    detailButtons.forEach(button => {
      button.addEventListener('click', function() {
        const alertId = this.getAttribute('data-alert-id');
        fetchAlertDetails(alertId);
      });
    });
  });
  
  function formatDateForInput(date) {
    return date.toISOString().slice(0, 16);
  }
  
  function fetchAlertDetails(alertId) {
    fetch(`/alerts/details/${alertId}`)
      .then(response => response.json())
      .then(data => {
        displayAlertDetails(data);
        new bootstrap.Modal(document.getElementById('alertDetailsModal')).show();
      })
      .catch(error => {
        console.error('Error fetching alert details:', error);
      });
  }
  
  function displayAlertDetails(alert) {
    const container = document.getElementById('alert-details-content');
    const details = alert.details || {};
    
    // Build detail HTML
    let html = `
      <div class="alert alert-${alert.level_class.replace('bg-', '')}">
        <h4>${alert.message}</h4>
        <p><strong>Level:</strong> ${alert.level_str}</p>
        <p><strong>Time:</strong> ${alert.time_str}</p>
        <p><strong>Entity:</strong> ${alert.entity || 'N/A'}</p>
        <p><strong>Source:</strong> ${alert.source}</p>
      </div>
      
      <h5>Alert Details</h5>
      <table class="table table-bordered">
        <tbody>
    `;
    
    // Add general properties
    html += `
      <tr>
        <th>Alert ID</th>
        <td>${alert.uuid}</td>
      </tr>
      <tr>
        <th>Status</th>
        <td>${alert.acknowledged ? 'Acknowledged' : 'New'} | ${alert.resolved ? 'Resolved' : 'Active'}</td>
      </tr>
      <tr>
        <th>Notifications Sent</th>
        <td>${alert.notifications_sent}</td>
      </tr>
    `;
    
    // Add rate specific details if available
    if (details.rate_type) {
      html += `
        <tr>
          <th>Rate Type</th>
          <td>${details.rate_type}</td>
        </tr>
        <tr>
          <th>Threshold</th>
          <td>${details.threshold}</td>
        </tr>
        <tr>
          <th>Actual Value</th>
          <td>${details.actual_value}</td>
        </tr>
      `;
    }
    
    html += `
        </tbody>
      </table>
    `;
    
    // Add anomaly specific sections if available
    if (details.anomaly_type) {
      html += `
        <h5>Anomaly Information</h5>
        <div class="card mb-3">
          <div class="card-header">
            <strong>Type:</strong> ${details.anomaly_type}
          </div>
          <div class="card-body">
      `;
      
      // Add configuration
      if (details.config) {
        html += '<h6>Configuration:</h6><ul>';
        for (const [key, value] of Object.entries(details.config)) {
          html += `<li><strong>${key}:</strong> ${value}</li>`;
        }
        html += '</ul>';
      }
      
      // Add statistics
      if (details.statistics) {
        html += '<h6>Statistics:</h6><ul>';
        for (const [key, value] of Object.entries(details.statistics)) {
          html += `<li><strong>${key}:</strong> ${value}</li>`;
        }
        html += '</ul>';
      }
      
      html += `
          </div>
        </div>
      `;
    }
    
    container.innerHTML = html;
  }
</script>

<style>
  /* Alert level colors for table rows */
  .alert-row.critical {
    background-color: rgba(220, 53, 69, 0.1);
  }
  .alert-row.alert {
    background-color: rgba(255, 193, 7, 0.1);
  }
  .alert-row.warning {
    background-color: rgba(255, 193, 7, 0.05);
  }
  
  /* Badge color classes */
  .bg-emergency {
    background-color: #6610f2 !important;
  }
  .bg-critical {
    background-color: #dc3545 !important;
  }
  .bg-alert {
    background-color: #fd7e14 !important;
  }
  .bg-warning {
    background-color: #ffc107 !important;
  }
  .bg-info {
    background-color: #0dcaf0 !important;
  }
  .bg-debug {
    background-color: #6c757d !important;
  }
</style> 