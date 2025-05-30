# Rate Monitoring Configuration

## Overview

The rate monitoring system in BACmon tracks traffic rates across different time intervals and can trigger alerts when thresholds are exceeded. In this updated version, rate monitoring thresholds are fully configurable through the `BACmon.ini` configuration file.

## Configuration

Rate monitoring is configured in the `[RateMonitoring]` section of `BACmon.ini`. This section allows you to define:

1. Multiple rate monitoring thresholds for different metrics
2. Sampling intervals for each threshold
3. Maximum allowed values before triggering alerts
4. Duration requirements (how many consecutive intervals the threshold must be exceeded)
5. Scan interval (how often to check the rates)

### Syntax

Each rate threshold is defined using the following format:

```ini
metric_name = key, interval, max_value, duration
```

Where:
- `metric_name`: A unique identifier for this threshold configuration (e.g., `total_rate`)
- `key`: The monitoring key in Redis (e.g., `total:s` for total traffic per second)
- `interval`: Sampling interval in seconds (e.g., `1` for per-second sampling)
- `max_value`: Maximum allowed value before triggering an alert (e.g., `20` for 20 packets per interval)
- `duration`: Number of consecutive intervals the threshold must be exceeded before triggering an alarm (e.g., `30` for 30 consecutive intervals)

Additionally, you can set the scan interval (in milliseconds) that determines how often the system checks for threshold violations:

```ini
scan_interval = 10000  # Check every 10 seconds
```

### Example Configuration

```ini
[RateMonitoring]
# Total traffic per second (alert if > 20 packets/sec for 30 consecutive seconds)
total_rate = total:s, 1, 20, 30

# IP-specific traffic (alert if > 10 packets/sec from a specific IP for 30 seconds)
ip_specific_rate = 192.168.1.100:s, 1, 10, 30

# Application layer traffic (alert if > 15 packets/sec of application traffic for 20 seconds)
application_layer_rate = apdu:s, 1, 15, 20

# Check rates every 5 seconds (5000 milliseconds)
scan_interval = 5000
```

## Available Monitoring Keys

The following keys are available for monitoring:

- `total:s`: Total traffic per second
- `total:m`: Total traffic per minute
- `total:h`: Total traffic per hour
- `<ip-address>:s`: Traffic from a specific IP address per second
- `<ip-address>:m`: Traffic from a specific IP address per minute
- `<ip-address>:h`: Traffic from a specific IP address per hour
- `<application-key>:s`: Specific application layer traffic per second

## Best Practices

1. **Start with conservative thresholds**: Begin with higher threshold values and adjust downward as you understand your network's normal traffic patterns.

2. **Layer your monitoring**: Configure multiple thresholds with different durations to detect both sudden spikes (short duration) and sustained abnormal traffic (long duration).

3. **Balance sensitivity and false positives**: A threshold that's too low may trigger false alarms. A threshold that's too high might miss important events.

4. **Consider time of day**: Traffic patterns often vary throughout the day. You might need different thresholds for business hours vs. overnight.

5. **Monitor key devices**: Configure IP-specific monitoring for critical devices or potential bottlenecks in your BACnet network.

6. **Adjust scan interval**: The `scan_interval` parameter affects how quickly the system responds to threshold violations, but also affects system load. Values between 5000-10000ms (5-10 seconds) are typically a good balance.

## Troubleshooting

If rate monitoring isn't working as expected:

1. Check the logs for any configuration errors when starting BACmon
2. Verify the Redis server is running and accessible
3. Check that your rate thresholds are appropriate for your network's traffic patterns
4. Use the BACmon web interface to view current traffic rates and historical data
5. Validate that the syntax in your configuration file is correct

## Advanced Configuration

For more advanced scenarios, you can modify the `BACmon.py` source code to add custom rate monitoring logic or additional metrics beyond what's configurable in the `BACmon.ini` file. 