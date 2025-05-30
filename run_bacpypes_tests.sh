#!/bin/bash

# Run all BACpypes-related tests
echo "Running BACpypes Tests for BACmon"
echo "=================================="

echo -e "\n1. Running BACpypes Compatibility Tests"
echo "---------------------------------------"
python test_bacpypes_compat.py

echo -e "\n2. Running BACpypes Requirements Tests"
echo "---------------------------------------"
python test_bacpypes_requirements.py

echo -e "\n3. Running BACmon BACpypes Integration Tests"
echo "-------------------------------------------"
python test_bacmon_bacpypes.py

echo -e "\nAll tests completed!" 