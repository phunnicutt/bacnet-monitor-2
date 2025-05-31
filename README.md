# BACmon - BACnet Protocol Monitor

BACmon is a monitoring tool for BACnet networks. It captures and analyzes BACnet traffic, providing insights into network activity, device behavior, and communication patterns.

## Features

- Captures and decodes BACnet packets from the network
- Analyzes traffic patterns and statistics
- Supports both BACpypes and BACpypes3 libraries
- Compatible with Python 3.6+
- Docker support for easy deployment
- Web interface for data visualization
- Robust Redis client with error handling and connection management

## Installation

See `SETUP.md` for detailed installation instructions.

For Docker-based installation, refer to `DOCKER.md`.

## Python 3 Compatibility

BACmon has been fully migrated to Python 3. See `PYTHON3_MIGRATION.md` for details about the migration process and compatibility considerations.

## BACpypes Library

BACmon uses a compatibility layer that supports both the original BACpypes library and the newer BACpypes3 library. This ensures maximum compatibility across different environments. See `docs/BACPYPES_USAGE.md` for detailed information.

## Redis Client

BACmon uses a custom Redis client abstraction layer that provides improved error handling, connection management, and a consistent interface. See `docs/REDIS_USAGE.md` for detailed information on configuration options and usage examples.

## Configuration

Edit `BACmon.ini` to configure the application. An example configuration file is provided in `BACmon.ini.example`.

The Redis connection can be configured in the `[Redis]` section of the configuration file.

## Testing

Run the tests to verify your installation:

```bash
# Test BACpypes compatibility
./run_bacpypes_tests.sh

# Test Python 3 compatibility
python test_python3_compatibility.py

# Test WSGI compatibility
python test_wsgi_compatibility.py

# Test Redis client
python test_redis_client.py
```

## License

See LICENSE file for details.
