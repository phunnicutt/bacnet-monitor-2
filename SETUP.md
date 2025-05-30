# BACmon Setup Guide

This document provides instructions for setting up the BACmon project environment for development and deployment.

## Prerequisites

- Python 3.6 or higher
- Git
- Redis server
- (Optional) Docker for containerized deployment

## Deployment Options

### 1. Docker Deployment (Recommended)

The simplest way to deploy BACmon is using Docker. See [DOCKER.md](DOCKER.md) for detailed instructions.

Quick start:
```bash
# Build and start the container
docker-compose up -d
```

### 2. Traditional Installation

If you prefer a traditional installation, follow the steps below.

## Python 3 Compatibility

The BACmon codebase has been fully migrated to support Python 3, while maintaining backward compatibility with Python 2 where possible. For details on the migration process and changes made:

```bash
# View the Python 3 migration documentation
cat PYTHON3_MIGRATION.md
```

To validate Python 3 compatibility in your environment:

```bash
# Run the validation script
./validate_python3_migration.sh
```

See [PYTHON3_MIGRATION.md](PYTHON3_MIGRATION.md) for more details on the changes made during the migration.

## Installing Required Packages

### System Dependencies

Use the install script for Ubuntu/Debian systems:

```bash
sudo ./install_ubuntu.sh
```

Or manually install the following packages:

```bash
sudo apt-get install -y python3 python3-dev python3-pip python3-setuptools gcc redis-server libpcap-dev libxslt1-dev ntp daemonlogger
```

### Python Dependencies

Install the required Python packages:

```bash
pip3 install -r requirements.txt
```

## BACpypes Compatibility Layer

BACmon includes a compatibility layer (`bacpypes_compat.py`) that allows it to work with both the original `bacpypes` library and the newer `bacpypes3` library. This layer abstracts away differences between the libraries, enabling a smooth transition to Python 3 while maintaining backward compatibility.

The compatibility layer handles:
- Module imports
- Class and function differences
- API changes between versions
- Proper initialization based on available libraries

When using BACmon with Python 3, it will attempt to use `bacpypes3` first and fall back to `bacpypes` if needed.

## Redis Client Abstraction Layer

BACmon includes a Redis client abstraction layer (`redis_client.py`) that provides a consistent interface for Redis operations with improved error handling and connection management. This layer:

- Simplifies Redis operations throughout the codebase
- Handles connection errors with configurable retry logic
- Centralizes configuration management
- Provides BACmon-specific helper methods

To use the Redis client in your development:

```python
from redis_client import create_redis_client

# Create a client with default settings
redis_client = create_redis_client()

# Use the client for Redis operations
redis_client.set('key', 'value')
value = redis_client.get('key')
```

See [Redis Usage](docs/REDIS_USAGE.md) for more details on the Redis client abstraction layer.

## Configuration

1. Copy the example configuration file:
   ```bash
   cp BACmon.ini.example BACmon.ini
   ```

2. Edit the configuration file to match your environment:
   ```bash
   nano BACmon.ini
   ```

3. Create the required directories:
   ```bash
   mkdir -p /home/bacmon/log
   mkdir -p /home/bacmon/template
   mkdir -p /home/bacmon/static
   ```

## Running BACmon

### Start the Redis Server

```bash
sudo systemctl start redis-server
```

### Start BACmon

```bash
python3 BACmon.py
```

## Troubleshooting

### Common Issues

1. **bacpypes3 Installation Issues**

   If you encounter problems installing bacpypes3, ensure you're using a compatible version:

   ```bash
   pip3 install bacpypes3==0.0.102
   ```

2. **Redis Connection Issues**

   Verify Redis is running:

   ```bash
   redis-cli ping
   ```

   Make sure your Redis configuration allows connections from BACmon.

   To test the Redis client wrapper specifically:

   ```bash
   python3 test_redis_client.py
   ```

   If you encounter connection issues, check your Redis configuration in `BACmon.ini`:

   ```ini
   [Redis]
   host = localhost
   port = 6379
   db = 0
   ```

3. **Import Errors**

   If you see import errors related to bacpypes modules, ensure both bacpypes and bacpypes3 are installed:

   ```bash
   pip3 install bacpypes bacpypes3
   ```

## Additional Resources

- See [DOCKER.md](DOCKER.md) for containerized deployment details
- For development, check the [Development Guide](docs/DEVELOPMENT.md) if available
- For understanding the BACnet protocol implementation, review the [BACpypes Documentation](https://bacpypes.readthedocs.io/)
- Redis documentation is available at [redis.io](https://redis.io/documentation)
- For Redis client wrapper documentation, see [Redis Usage](docs/REDIS_USAGE.md)

## Support

For issues with BACmon, please submit a detailed description of the problem, including error messages and your environment configuration. 