# BACpypes Compatibility Guide

This document describes BACmon's compatibility layer for working with both bacpypes and bacpypes3 libraries.

## Overview

BACmon supports both the traditional bacpypes library and the newer asyncio-based bacpypes3 library through a compatibility layer (`bacpypes_compat.py`). This allows the application to work with either library seamlessly.

## Supported Versions

### bacpypes (Traditional)
- **Version**: 0.19.0 (latest Python 3 compatible)
- **Release Date**: January 22, 2025
- **Architecture**: Traditional event loop with core.run
- **Python Support**: 3.9+

### bacpypes3 (Asyncio-based)
- **Version**: 0.0.102 (latest)
- **Architecture**: Modern asyncio with async/await patterns
- **Python Support**: 3.9+

## Compatibility Layer Features

### 1. Automatic Library Detection
The compatibility layer automatically detects which libraries are available:

```python
from bacpypes_compat import BACPYPES_AVAILABLE, BACPYPES3_AVAILABLE

print(f"bacpypes available: {BACPYPES_AVAILABLE}")
print(f"bacpypes3 available: {BACPYPES3_AVAILABLE}")
```

### 2. Version Switching
Runtime switching between libraries:

```python
from bacpypes_compat import set_bacpypes_version

# Use traditional bacpypes
set_bacpypes_version(False)

# Use asyncio-based bacpypes3
set_bacpypes_version(True)
```

### 3. Unified Import Interface
All BACnet functionality is accessed through consistent functions:

```python
from bacpypes_compat import (
    get_debugging, get_console_logging, get_core, get_task,
    get_comm, get_udp, get_pdu, get_bvll, get_npdu, get_apdu
)

# Get components regardless of underlying library
PDU, Client, bind = get_comm()
Address, LocalBroadcast = get_pdu()
run, deferred = get_core()
```

## Architecture Differences Handled

### Core Event Loop
- **bacpypes**: Uses `bacpypes.core.run()` and `bacpypes.core.deferred()`
- **bacpypes3**: Uses asyncio event loop with compatibility wrappers

### Task Management
- **bacpypes**: Uses `bacpypes.task.RecurringTask`
- **bacpypes3**: Uses asyncio-based `RecurringTaskWrapper`

### BVLL Module Location
- **bacpypes**: `bacpypes.bvll`
- **bacpypes3**: `bacpypes3.ipv4.bvll`

### Console Logging
- **bacpypes**: `bacpypes.consolelogging.ConsoleLogHandler`
- **bacpypes3**: Custom adapter using `bacpypes3.debugging.LoggingFormatter`

## Testing

### Compatibility Layer Test
```bash
python3 test_bacpypes_compat.py
```

This test validates:
- Import functionality for both libraries
- Version switching capabilities
- Basic functionality (PDU creation, address handling)
- Debugging component availability

### Requirements Verification Test
```bash
python3 test_bacpypes_requirements.py
```

This test validates:
- Python version compatibility (3.9+)
- Library installation and versions
- Dependency availability
- Import functionality for critical modules

## Usage Examples

### Basic PDU Operations
```python
from bacpypes_compat import set_bacpypes_version, get_comm, get_pdu

# Set library preference
set_bacpypes_version(False)  # Use bacpypes

# Get components
PDU, Client, bind = get_comm()
Address, LocalBroadcast = get_pdu()

# Create objects
pdu = PDU()
broadcast_addr = LocalBroadcast()
```

### Debugging Setup
```python
from bacpypes_compat import get_debugging, get_console_logging

# Get debugging components
function_debugging, ModuleLogger, DebugContents = get_debugging()
ConsoleLogHandler = get_console_logging()

# Set up debugging
function_debugging("module_name")
console_handler = ConsoleLogHandler()
```

## Installation

### Install Both Libraries
```bash
pip install bacpypes>=0.19.0,<0.20.0
pip install bacpypes3>=0.0.102,<0.1.0
```

### Install Individual Libraries
```bash
# Traditional bacpypes only
pip install bacpypes>=0.19.0,<0.20.0

# Asyncio bacpypes3 only
pip install bacpypes3>=0.0.102,<0.1.0
```

## Configuration

The compatibility layer uses bacpypes by default but will automatically fall back to bacpypes3 if bacpypes is not available. You can explicitly set the preference:

```python
from bacpypes_compat import set_bacpypes_version

# Prefer bacpypes3 (asyncio-based)
set_bacpypes_version(True)

# Prefer bacpypes (traditional)
set_bacpypes_version(False)
```

## Troubleshooting

### Import Errors
If you encounter import errors, verify library installation:

```bash
python3 -c "import bacpypes; print('bacpypes version:', bacpypes.__version__)"
python3 -c "import bacpypes3; print('bacpypes3 version:', bacpypes3.__version__)"
```

### Compatibility Issues
Run the compatibility test to diagnose issues:

```bash
python3 test_bacpypes_compat.py
```

### Version Conflicts
Ensure you have compatible versions:
- bacpypes: 0.19.0
- bacpypes3: 0.0.102
- Python: 3.9.6 or higher

## Future Considerations

1. **Performance**: bacpypes3 may offer better performance for high-throughput applications due to asyncio
2. **Maintenance**: bacpypes3 is actively developed with modern Python patterns
3. **Migration**: Consider gradually migrating to bacpypes3 for new features
4. **Compatibility**: The compatibility layer ensures smooth transition between libraries

## Support

For issues related to:
- **bacpypes**: Check the original bacpypes documentation
- **bacpypes3**: Check the bacpypes3 project documentation
- **Compatibility Layer**: Review `bacpypes_compat.py` and run test scripts 