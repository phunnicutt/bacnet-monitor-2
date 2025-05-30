# BACpypes Library Usage in BACmon

## Overview

BACmon uses the BACpypes library for BACnet protocol communication. This document explains how BACmon integrates with both the original BACpypes library and the newer BACpypes3 library, providing compatibility across different Python versions.

## Compatibility Layer

The `bacpypes_compat.py` module provides a compatibility layer that allows BACmon to work with either BACpypes or BACpypes3. This approach ensures:

1. Maximum compatibility across different deployment environments
2. Smooth transition path from legacy to modern versions
3. Future-proofing as the libraries continue to evolve

### How it Works

The compatibility layer:

- Detects which libraries are available
- Provides a consistent API regardless of which library is used
- Handles differences in module structure and naming
- Adapts to API changes between versions

## Supported Versions

BACmon has been tested with the following BACpypes library versions:

- **bacpypes**: Version 0.18.6 or higher (but less than 0.19.0)
- **bacpypes3**: Version 0.0.102 or higher (but less than 0.1.0)

These version constraints are specified in the `requirements.txt` file.

## Library Selection

By default, BACmon will use the original BACpypes library if available. If not available, it will automatically fall back to BACpypes3. This behavior can be controlled by calling:

```python
from bacpypes_compat import set_bacpypes_version

# To use BACpypes (default)
set_bacpypes_version(False)

# To use BACpypes3
set_bacpypes_version(True)
```

## Testing

Three test scripts are provided to verify BACpypes compatibility:

1. `test_bacpypes_compat.py` - Tests the compatibility layer with both libraries
2. `test_bacpypes_requirements.py` - Verifies that installed library versions meet requirements
3. `test_bacmon_bacpypes.py` - Tests BACmon integration with the libraries

You can run all tests at once using the provided shell script:

```bash
./run_bacpypes_tests.sh
```

## Troubleshooting

If you encounter issues with BACpypes libraries:

1. Verify that the correct versions are installed:
   ```
   pip list | grep bacpypes
   ```

2. Run the tests to identify any compatibility issues:
   ```
   python test_bacpypes_compat.py
   ```

3. Check if your environment has conflicting installations:
   ```
   pip show bacpypes
   pip show bacpypes3
   ```

4. If you need to force a specific version:
   ```
   pip install bacpypes==0.18.6
   pip install bacpypes3==0.0.102
   ```

## Development Guidelines

When making changes to BACmon code that interacts with BACpypes:

1. Always use the compatibility layer functions instead of direct imports
2. Test changes with both BACpypes and BACpypes3
3. Add tests for new functionality to ensure compatibility
4. Update version constraints if new features require newer library versions 