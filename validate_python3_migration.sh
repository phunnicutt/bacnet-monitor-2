#!/bin/bash

# Python 3 Migration Validation Script
# This script runs a series of tests to validate Python 3 compatibility

# Set colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting Python 3 Migration Validation${NC}"
echo "============================================="
echo

# Track overall success
OVERALL_SUCCESS=true

# Function to run a test and check its exit code
run_test() {
    TEST_NAME=$1
    TEST_CMD=$2
    
    echo -e "${YELLOW}Running Test: ${TEST_NAME}${NC}"
    echo "${TEST_CMD}"
    echo "---------------------------------------------"
    
    # Run the test command
    eval $TEST_CMD
    
    # Check the exit code
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${TEST_NAME} - PASSED${NC}"
    else
        echo -e "${RED}❌ ${TEST_NAME} - FAILED${NC}"
        OVERALL_SUCCESS=false
    fi
    
    echo
}

# 1. Check Python version
run_test "Python Version Check" "python3 --version"

# 2. Syntax Check - Check all Python files for syntax errors
echo -e "${YELLOW}Running Test: Python 3 Syntax Check${NC}"
echo "Find all .py files and check for syntax errors"
echo "---------------------------------------------"

SYNTAX_SUCCESS=true
for file in $(find . -name "*.py" -type f -not -path "./env/*"); do
    echo -n "Checking $file: "
    python3 -m py_compile $file 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}SYNTAX ERROR${NC}"
        SYNTAX_SUCCESS=false
        OVERALL_SUCCESS=false
    fi
done

if $SYNTAX_SUCCESS; then
    echo -e "${GREEN}✅ Python 3 Syntax Check - PASSED${NC}"
else
    echo -e "${RED}❌ Python 3 Syntax Check - FAILED${NC}"
fi
echo

# 3. Run the compatibility test script
run_test "General Python 3 Compatibility" "python3 test_python3_compatibility.py"

# 4. Run the WSGI compatibility test script
run_test "WSGI Compatibility" "python3 test_wsgi_compatibility.py"

# 5. Check for common Python 2 patterns that might have been missed
echo -e "${YELLOW}Running Test: Python 2 Pattern Check${NC}"
echo "Checking for remaining Python 2 patterns"
echo "---------------------------------------------"

PY2_PATTERNS_FOUND=false

check_pattern() {
    PATTERN=$1
    DESCRIPTION=$2
    
    echo -n "Checking for $DESCRIPTION: "
    MATCHES=$(grep -r "$PATTERN" --include="*.py" . --exclude-dir=env 2>/dev/null)
    
    if [ -z "$MATCHES" ]; then
        echo -e "${GREEN}None found${NC}"
    else
        echo -e "${RED}Found${NC}"
        echo "$MATCHES" | head -n 5
        if [ $(echo "$MATCHES" | wc -l) -gt 5 ]; then
            echo "... and more"
        fi
        PY2_PATTERNS_FOUND=true
        OVERALL_SUCCESS=false
    fi
}

# Check for common Python 2 patterns
check_pattern "print \S" "print statements (not functions)"
check_pattern "\.has_key" "has_key method"
check_pattern "iteritems\(\)" "iteritems() method"
check_pattern "iterkeys\(\)" "iterkeys() method"
check_pattern "itervalues\(\)" "itervalues() method"
check_pattern "except \S+ *, *\S+ *:" "old exception syntax"
check_pattern "__cmp__" "__cmp__ method"
check_pattern "raw_input" "raw_input function"
check_pattern "xrange" "xrange function"

if $PY2_PATTERNS_FOUND; then
    echo -e "${RED}❌ Python 2 Pattern Check - FAILED${NC}"
else
    echo -e "${GREEN}✅ Python 2 Pattern Check - PASSED${NC}"
fi
echo

# 6. Check Redis compatibility
echo -e "${YELLOW}Running Test: Redis Module Compatibility${NC}"
echo "Checking if the Redis module imports correctly"
echo "---------------------------------------------"

python3 -c "
try:
    import redis
    print('✅ Redis module imported successfully')
    print('Redis version:', redis.__version__)
except ImportError as e:
    print('❌ Failed to import Redis module:', str(e))
    print('You may need to install it: pip install redis')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Redis Module Compatibility - PASSED${NC}"
else
    echo -e "${RED}❌ Redis Module Compatibility - FAILED${NC}"
    OVERALL_SUCCESS=false
fi
echo

# 7. Check BACpypes compatibility
echo -e "${YELLOW}Running Test: BACpypes Module Compatibility${NC}"
echo "Checking if the BACpypes module imports correctly"
echo "---------------------------------------------"

python3 -c "
try:
    import bacpypes
    print('✅ BACpypes module imported successfully')
    print('BACpypes version:', bacpypes.__version__)
except ImportError as e:
    print('❌ Failed to import BACpypes module:', str(e))
    print('You may need to install it: pip install bacpypes')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ BACpypes Module Compatibility - PASSED${NC}"
else
    echo -e "${RED}❌ BACpypes Module Compatibility - FAILED${NC}"
    OVERALL_SUCCESS=false
fi
echo

# 8. Show final summary
echo "============================================="
if $OVERALL_SUCCESS; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED - Python 3 Migration Validated! 🎉${NC}"
    echo "The codebase appears to be compatible with Python 3."
else
    echo -e "${RED}❌ SOME TESTS FAILED - Python 3 Migration Needs More Work${NC}"
    echo "Please review the failed tests and fix the remaining issues."
fi
echo

# Exit with appropriate status code
if $OVERALL_SUCCESS; then
    exit 0
else
    exit 1
fi 