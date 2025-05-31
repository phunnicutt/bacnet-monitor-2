# BACmon REST API User Acceptance Testing (UAT) Guide

## Overview

This guide covers the comprehensive User Acceptance Testing (UAT) system for the BACmon REST API. The UAT suite validates that the API system meets production requirements through real-world usage scenarios.

## Test Coverage

The UAT system performs 8 phases of comprehensive testing:

### Phase 1: Server Availability Check
- Basic connectivity to BACmon server
- HTTP response validation
- Service availability confirmation

### Phase 2: Authentication & Security Testing
- API key authentication validation
- Invalid API key rejection
- Web session authentication
- Session-based API access
- Security mechanism verification

### Phase 3: API Versioning & Backward Compatibility
- V1 API endpoint functionality
- V2 API endpoint enhanced features
- Backward compatibility validation
- Version negotiation testing

### Phase 4: Data Access & Export Functionality
- Monitoring data access with time ranges (1h, 6h, 24h)
- Data export functionality (JSON, CSV)
- Pagination and filtering support
- Query parameter validation

### Phase 5: Real-time Features & Streaming
- Server-Sent Events (SSE) monitoring streams
- Alert notification streams
- V2 data aggregation capabilities
- Real-time data processing

### Phase 6: Web Dashboard Integration
- Main dashboard accessibility
- API dashboard functionality
- Static asset loading (CSS, JS)
- User interface integration

### Phase 7: Performance & Reliability Testing
- Concurrent request handling (5 simultaneous requests)
- Large dataset processing (100+ records)
- Response time measurement
- System reliability validation

### Phase 8: Error Handling & Edge Cases
- Invalid parameter handling
- Non-existent endpoint responses
- Structured error message validation
- Rate limiting behavior (when implemented)

## Running the UAT Suite

### Prerequisites

1. **Install Dependencies:**
   ```bash
   # Activate virtual environment
   source bacmon-venv/bin/activate
   
   # Install required packages
   pip install requests
   ```

2. **Ensure BACmon is Running:**
   ```bash
   # Start BACmon server (typical command)
   python BACmon.py
   # or
   python BACmonWSGI.py
   ```

### Command Line Usage

```bash
# Basic UAT run (default: http://localhost:8080)
python test_user_acceptance_api.py

# Custom server URL
python test_user_acceptance_api.py --url http://your-server:8080

# Quiet mode (less verbose output)
python test_user_acceptance_api.py --quiet

# Help information
python test_user_acceptance_api.py --help
```

### Quick Validation

To quickly test if the UAT script is working:

```bash
python quick_uat_test.py
```

## Test Credentials

The UAT system uses predefined test credentials from the BACmon authentication system:

### API Keys
- **Test Key:** `test_key_123` (read/write permissions)
- **Admin Key:** `admin_key_456` (admin permissions)

### Web Login Credentials
- **Test User:** username=`test`, password=`test123` (read/write access)
- **Admin User:** username=`admin`, password=`admin123` (full admin access)

## UAT Report

### Test Results

The UAT system generates comprehensive reports including:

- **Total tests executed**
- **Pass/fail statistics**
- **Success rate percentage**
- **Average response times**
- **Detailed test results by phase**
- **Production readiness recommendations**

### Report Output

1. **Console Output:** Real-time test progress and summary
2. **JSON Report:** Detailed results saved to `uat_report_bacmon_api.json`

### Success Criteria

- **90%+ Success Rate:** System ready for production
- **95%+ Success Rate:** Excellent production readiness
- **<90% Success Rate:** System needs improvement

## Sample UAT Output

```
🚀 Starting BACmon REST API User Acceptance Testing
============================================================

============================================================
UAT Phase 1: Server Availability Check
============================================================
✓ PASS: Server Availability (0.023s) - Server accessible (HTTP 200)

============================================================
UAT Phase 2: Authentication & Security Testing
============================================================
✓ PASS: API Key Authentication (0.045s) - Valid API key accepted
✓ PASS: Invalid API Key Rejection (0.032s) - Invalid API key properly rejected
✓ PASS: Web Session Login (0.087s) - Web login successful
✓ PASS: Session-based API Access (0.041s) - Session authentication working

[... continued for all test phases ...]

============================================================
🎯 USER ACCEPTANCE TESTING COMPLETE
============================================================
📊 TEST SUMMARY:
   Total Tests: 35
   Passed: 33
   Failed: 2
   Success Rate: 94.29%
   Avg Response Time: 0.156s
   Total Test Duration: 15.42s

📋 RECOMMENDATIONS:
   • API system is mostly ready, with minor issues to address

📄 Detailed report saved to: uat_report_bacmon_api.json
✅ UAT RESULT: SYSTEM READY FOR PRODUCTION
```

## Test Phases in Detail

### Authentication Testing
- Validates all authentication mechanisms work correctly
- Ensures proper security boundaries are enforced
- Tests both API key and session-based authentication

### API Versioning Testing
- Confirms V1 and V2 endpoints function correctly
- Validates backward compatibility for existing clients
- Tests version-specific features and enhancements

### Data Access Testing
- Validates time-range filtering (1h, 6h, 24h, custom ranges)
- Tests pagination with limit/offset parameters
- Confirms data export in multiple formats (JSON, CSV)

### Real-time Features Testing
- Tests Server-Sent Events (SSE) streaming endpoints
- Validates real-time monitoring and alert streams
- Tests V2-exclusive data aggregation features

### Performance Testing
- Measures response times under normal conditions
- Tests concurrent request handling capabilities
- Validates large dataset processing performance

### Error Handling Testing
- Tests proper error responses for invalid inputs
- Validates structured error message formats
- Confirms appropriate HTTP status codes

## Integration with CI/CD

The UAT script can be integrated into CI/CD pipelines:

```bash
# Exit code 0 = success, 1 = failure
python test_user_acceptance_api.py --quiet
echo "UAT exit code: $?"
```

## Troubleshooting

### Common Issues

1. **Server Not Available:**
   - Ensure BACmon is running on the expected port
   - Check firewall settings
   - Verify network connectivity

2. **Authentication Failures:**
   - Confirm test credentials are configured in simple_auth.py
   - Check if authentication is enabled (AUTH_ENABLED=true)
   - Verify API keys are properly set up

3. **Missing Dependencies:**
   - Install required packages: `pip install requests`
   - Activate the correct virtual environment

4. **Permission Errors:**
   - Ensure proper file permissions
   - Check if running from the correct directory

### Debugging

Enable detailed logging for troubleshooting:

```bash
# Run with verbose output (default)
python test_user_acceptance_api.py

# Check the detailed JSON report
cat uat_report_bacmon_api.json | python -m json.tool
```

## Customization

### Adding Custom Tests

To add new test scenarios:

1. Create a new test method in the `BACmonUATTester` class
2. Add the test to the `run_full_uat_suite()` method
3. Update the test categorization in `generate_uat_report()`

### Modifying Test Criteria

- Adjust success rate thresholds in `generate_uat_report()`
- Modify timeout values for different test scenarios
- Update test credentials for your environment

## Best Practices

1. **Regular Testing:** Run UAT after significant API changes
2. **Environment Consistency:** Test in environment similar to production
3. **Documentation:** Keep test scenarios updated with API changes
4. **Monitoring:** Track UAT success rates over time
5. **Automation:** Integrate UAT into deployment pipelines

## Production Deployment

Before deploying to production:

1. **Run complete UAT suite** with 90%+ success rate
2. **Review failed test cases** and address issues
3. **Test with production-like data volumes**
4. **Validate security configurations**
5. **Confirm performance requirements are met**

This UAT system ensures the BACmon REST API meets enterprise-grade standards for reliability, security, and functionality before production deployment. 