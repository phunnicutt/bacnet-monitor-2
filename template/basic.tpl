<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    
    <title>BACnet VLAN Monitor</title>
    <link rel="stylesheet" href="/static/default.css" type="text/css" />
    <link rel="stylesheet" href="/static/pygments.css" type="text/css" />
    <script type="text/javascript" src="/static/js/jquery.js"></script>
    <script type="text/javascript" src="/static/js/jquery.flot.js"></script>
    <script type="text/javascript" src="/static/js/jquery.flot.selection.js"></script>
    <script type="text/javascript" src="/static/js/jquery.strftime.js"></script>
    <!--[if IE]><script type="text/javascript" src="/static/js/excanvas.js"></script><![endif]--> 
    <link rel="top" title="BACnet VLAN Monitor" href="#" />
    <link rel="next" title="Introduction" href="intro.html" /> 
  </head>
  <body>
    <div class="related">
      <h3>Navigation</h3>
      <ul>
        <li class="right" style="margin-right: 10px">
          <a href="/" title="Welcome">home</a></li>
        <li class="right" >
          <a href="/help" title="IP">help</a> |</li>
        % if get('auth_user'):
        <li class="right" >
          <a href="/logout" title="Logout">logout ({{auth_user}})</a> |</li>
        % else:
        <li class="right" >
          <a href="/login" title="Login">login</a> |</li>
        % end
        <li><a href="/">BACnet LAN Monitor</a> &raquo;</li> 
      </ul>
    </div>

    <div class="document">
      <div class="documentwrapper">
        <div class="bodywrapper">
          <div class="body">

            <div class="section">
              <h1>{{title}}</h1>
              {{!body}}
            </div>

          </div>
        </div>
      </div>
      <div class="sphinxsidebar">
        <div class="sphinxsidebarwrapper">
            <h3>Enhanced Monitoring</h3>
            <ul>
                <li><a class="reference external" href="/dashboard">Main Dashboard</a>
                <li><a class="reference external" href="/api-dashboard">API Dashboard</a>
                <li><a class="reference external" href="/rate-monitoring">Rate Monitoring Dashboard</a>
                <li><a class="reference external" href="/anomaly-summary">Anomaly Summary</a>
                <li><a class="reference external" href="/alerts">Alert Dashboard</a>
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
                % if get('auth_user'):
                <li><a class="reference external" href="/auth/info">Auth Status</a>
                <li><a class="reference external" href="/logout">Logout</a>
                % else:
                <li><a class="reference external" href="/login">Login</a>
                % end
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
        % if get('auth_user'):
        <li class="right" >
          <a href="/logout" title="Logout">logout ({{auth_user}})</a> |</li>
        % else:
        <li class="right" >
          <a href="/login" title="Login">login</a> |</li>
        % end
        <li><a href="/">BACnet LAN Monitor</a> &raquo;</li> 
      </ul>
    </div>
    <div class="footer">
      &copy; Copyright 2012, Joel Bender.
    </div>
  </body>
</html>
