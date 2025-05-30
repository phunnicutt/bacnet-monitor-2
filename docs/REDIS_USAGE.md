# Redis Client Usage in BACmon

## Overview

BACmon uses Redis as its primary data store for capturing and analyzing BACnet traffic patterns. This document explains how BACmon integrates with Redis through a custom abstraction layer that provides improved error handling, connection management, and a consistent interface.

## Redis Client Abstraction Layer

The `redis_client.py` module provides a wrapper around the standard Redis client to enhance reliability and provide BACmon-specific functionality. This abstraction layer:

1. Simplifies Redis operations throughout the codebase
2. Provides consistent error handling and retry logic
3. Centralizes connection management and configuration
4. Adds BACmon-specific helper methods
5. Includes type hints for better code maintainability

### Key Features

- **Robust Error Handling**: Automatically handles connection errors with configurable retry logic
- **Connection Pooling**: Efficiently manages Redis connections
- **Type Annotations**: Provides Python type hints for better IDE support and code readability
- **Compatibility**: Works with both Python 2 and Python 3 environments
- **BACmon-specific Methods**: Includes specialized methods for common operations in BACmon

## Supported Versions

BACmon has been tested with the following Redis client versions:

- **redis-py**: Version 4.3.4 or higher

This version constraint is specified in the `requirements.txt` file.

## Basic Usage

### Creating a Redis Client

The recommended way to create a Redis client is through the factory function:

```python
from redis_client import create_redis_client

# Create a client with default settings
redis_client = create_redis_client()

# Or provide custom configuration
config = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'socket_timeout': 5.0,
    'password': 'your_password'  # if needed
}
redis_client = create_redis_client(config)
```

### Configuration Options

The Redis client supports the following configuration options:

- `host`: Redis server hostname (default: 'localhost')
- `port`: Redis server port (default: 6379)
- `db`: Redis database number (default: 0)
- `password`: Redis password for authentication (default: None)
- `socket_timeout`: Socket timeout for Redis operations (default: 5.0)
- `socket_connect_timeout`: Socket connection timeout (default: 5.0)
- `retry_on_timeout`: Whether to retry operations on timeout (default: True)
- `max_retries`: Maximum number of retries for operations (default: 3)
- `decode_responses`: Whether to decode Redis responses to strings (default: False)
- `health_check_interval`: Interval for connection health checks (default: 30)

These options can be provided in the `config` dictionary passed to `create_redis_client()`.

### BACmon.ini Configuration

The Redis client can also be configured through the `BACmon.ini` file by adding a `Redis` section:

```ini
[Redis]
host = localhost
port = 6379
db = 0
password = your_password
socket_timeout = 5.0
socket_connect_timeout = 5.0
```

## Common Operations

### Key-Value Operations

```python
# Set a value
redis_client.set('key', 'value')

# Get a value
value = redis_client.get('key')

# Delete a key
redis_client.delete('key')
```

### Set Operations

```python
# Add items to a set
redis_client.sadd('set_key', 'item1', 'item2', 'item3')

# Get all members in a set
members = redis_client.smembers('set_key')
```

### List Operations

```python
# Add items to a list
redis_client.lpush('list_key', 'item1', 'item2', 'item3')

# Get a range of elements from a list
items = redis_client.lrange('list_key', 0, -1)

# Trim a list to a specific range
redis_client.ltrim('list_key', 0, 9)  # Keep only the first 10 items
```

### Counter Operations

```python
# Increment a counter
count = redis_client.incr('counter_key')

# Increment by a specific amount
count = redis_client.incr('counter_key', 5)
```

### BACmon-Specific Methods

```python
# Set the startup time of the BACmon daemon
redis_client.set_startup_time()

# Set the version of the BACmon daemon
redis_client.set_daemon_version('1.0.0')
```

## Testing

A comprehensive test script is provided to verify Redis client functionality:

```bash
python test_redis_client.py
```

This script includes:

1. API verification (checking that all required methods exist)
2. Live Redis server tests (when a Redis server is available)
3. Mock-based tests (that don't require a running Redis server)

## Troubleshooting

If you encounter issues with the Redis client:

1. Verify that the correct Redis client version is installed:
   ```
   pip list | grep redis
   ```

2. Run the tests to identify any issues:
   ```
   python test_redis_client.py
   ```

3. Check Redis server connectivity:
   ```python
   from redis_client import create_redis_client
   client = create_redis_client()
   try:
       client.ping()
       print("Redis server is available")
   except Exception as e:
       print(f"Redis connection error: {e}")
   ```

4. Inspect Redis logs for server-side issues

## Development Guidelines

When making changes to BACmon code that interacts with Redis:

1. Always use the Redis client wrapper instead of direct Redis imports
2. Add comprehensive tests for new functionality
3. Use the retry mechanism for operations that might fail temporarily
4. Add type hints to maintain code quality
5. Document any new methods or changes to existing behavior 