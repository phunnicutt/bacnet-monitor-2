<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    
    <title>BACmon Login</title>
    <link rel="stylesheet" href="/static/default.css" type="text/css" />
    <style>
      .login-container {
        max-width: 400px;
        margin: 50px auto;
        padding: 30px;
        border: 1px solid #ddd;
        border-radius: 8px;
        background: #fafafa;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      }
      
      .login-form {
        margin-top: 20px;
      }
      
      .form-group {
        margin-bottom: 15px;
      }
      
      .form-group label {
        display: block;
        margin-bottom: 5px;
        font-weight: bold;
        color: #333;
      }
      
      .form-group input {
        width: 100%;
        padding: 10px;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 14px;
        box-sizing: border-box;
      }
      
      .form-group input:focus {
        outline: none;
        border-color: #007cba;
        box-shadow: 0 0 0 2px rgba(0, 124, 186, 0.2);
      }
      
      .login-button {
        width: 100%;
        padding: 12px;
        background: #007cba;
        color: white;
        border: none;
        border-radius: 4px;
        font-size: 16px;
        cursor: pointer;
        transition: background-color 0.2s;
      }
      
      .login-button:hover {
        background: #005a87;
      }
      
      .error-message {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 10px;
        border-radius: 4px;
        margin-bottom: 15px;
      }
      
      .info-message {
        background: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 10px;
        border-radius: 4px;
        margin-bottom: 15px;
      }
      
      .test-credentials {
        margin-top: 20px;
        padding: 15px;
        background: #e2e3e5;
        border-radius: 4px;
        font-size: 12px;
      }
      
      .test-credentials h4 {
        margin: 0 0 10px 0;
        color: #383d41;
      }
      
      .test-credentials code {
        background: #f8f9fa;
        padding: 2px 4px;
        border-radius: 2px;
        font-family: monospace;
      }
    </style>
    <link rel="top" title="BACnet VLAN Monitor" href="#" />
  </head>
  <body>
    <div class="related">
      <h3>Navigation</h3>
      <ul>
        <li class="right" style="margin-right: 10px">
          <a href="/" title="Welcome">home</a></li>
        <li><a href="/">BACnet LAN Monitor</a> &raquo;</li>
        <li><a href="/login">Login</a> &raquo;</li>
      </ul>
    </div>

    <div class="document">
      <div class="documentwrapper">
        <div class="bodywrapper">
          <div class="body">

            <div class="login-container">
              <h1>BACmon Login</h1>
              <p>Please enter your credentials to access the monitoring system.</p>

              % if error:
                <div class="error-message">{{error}}</div>
              % end
              
              % if message:
                <div class="info-message">{{message}}</div>
              % end

              <form method="POST" action="/login" class="login-form">
                <div class="form-group">
                  <label for="username">Username:</label>
                  <input type="text" id="username" name="username" required 
                         value="{{username if username else ''}}" autocomplete="username">
                </div>

                <div class="form-group">
                  <label for="password">Password:</label>
                  <input type="password" id="password" name="password" required autocomplete="current-password">
                </div>

                <button type="submit" class="login-button">Login</button>
              </form>

              % if show_test_credentials:
              <div class="test-credentials">
                <h4>Test Credentials (Development Mode)</h4>
                <p><strong>Username:</strong> <code>test</code></p>
                <p><strong>Password:</strong> <code>test123</code></p>
                <p><strong>Admin:</strong> <code>admin</code> / <code>admin123</code></p>
                <hr style="margin: 10px 0;">
                <p><strong>API Keys for Testing:</strong></p>
                <p>Read/Write: <code>test_key_123</code></p>
                <p>Admin: <code>admin_key_456</code></p>
                <p><em>Use in X-API-Key header for API access</em></p>
              </div>
              % end
            </div>

          </div>
        </div>
      </div>
      <div class="clearer"></div>
    </div>

    <div class="related">
      <h3>Navigation</h3>
      <ul>
        <li class="right" style="margin-right: 10px">
          <a href="/" title="Welcome">home</a></li>
        <li><a href="/">BACnet LAN Monitor</a> &raquo;</li>
      </ul>
    </div>
    <div class="footer">
      &copy; Copyright 2012, Joel Bender. Enhanced with Authentication.
    </div>
  </body>
</html> 