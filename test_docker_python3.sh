#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== BACmon Docker Python 3 Configuration Test ===${NC}"

# Build the Docker image
echo -e "\n${YELLOW}Building Docker image...${NC}"
docker build -t bacmon:python3-test .
if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Docker image built successfully${NC}"
else
  echo -e "${RED}✗ Failed to build Docker image${NC}"
  exit 1
fi

# Clean up any existing test container
docker rm -f bacmon-python3-test 2>/dev/null || true

# Run the container for Python 3 testing (without network ports to avoid conflicts)
echo -e "\n${YELLOW}Starting container for Python 3 tests...${NC}"
docker run -d --name bacmon-python3-test bacmon:python3-test sleep 60
if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Container started successfully${NC}"
else
  echo -e "${RED}✗ Failed to start container${NC}"
  exit 1
fi

# Test 1: Verify Python 3 is installed and working
echo -e "\n${YELLOW}Testing Python 3 installation...${NC}"
PYTHON_VERSION=$(docker exec bacmon-python3-test python --version 2>&1)
echo "Python version: $PYTHON_VERSION"
if [[ "$PYTHON_VERSION" == *"Python 3"* ]]; then
  echo -e "${GREEN}✓ Python 3 is correctly installed${NC}"
else
  echo -e "${RED}✗ Python 3 test failed: $PYTHON_VERSION${NC}"
  docker rm -f bacmon-python3-test
  exit 1
fi

# Test 2: Verify Python 3 packages are installed
echo -e "\n${YELLOW}Testing Python 3 package installations...${NC}"
PACKAGES=("redis" "bacpypes3" "bottle" "simplejson" "lxml")
for package in "${PACKAGES[@]}"; do
  if docker exec bacmon-python3-test python -c "import $package" 2>/dev/null; then
    echo -e "${GREEN}✓ Package '$package' imported successfully${NC}"
  else
    echo -e "${RED}✗ Failed to import package '$package'${NC}"
    docker rm -f bacmon-python3-test
    exit 1
  fi
done

# Test 3: Verify BACmon Python files syntax
echo -e "\n${YELLOW}Testing BACmon Python 3 syntax compatibility...${NC}"
PYTHON_FILES=("BACmon.py" "BACmonWSGI.py" "redis_client.py" "config_validator.py")
for file in "${PYTHON_FILES[@]}"; do
  if docker exec bacmon-python3-test python -m py_compile "$file" 2>/dev/null; then
    echo -e "${GREEN}✓ '$file' syntax is Python 3 compatible${NC}"
  else
    echo -e "${RED}✗ '$file' has Python 3 syntax issues${NC}"
    docker rm -f bacmon-python3-test
    exit 1
  fi
done

# Test 4: Test Redis functionality (without external port)
echo -e "\n${YELLOW}Testing Redis server startup...${NC}"
docker exec bacmon-python3-test redis-server --daemonize yes
sleep 2
if docker exec bacmon-python3-test redis-cli ping >/dev/null 2>&1; then
  echo -e "${GREEN}✓ Redis server is working correctly${NC}"
else
  echo -e "${RED}✗ Redis server test failed${NC}"
  docker rm -f bacmon-python3-test
  exit 1
fi

# Test 5: Test Python 3 Redis client
echo -e "\n${YELLOW}Testing Python 3 Redis client integration...${NC}"
if docker exec bacmon-python3-test python -c "
import redis
import sys
r = redis.Redis(host='localhost', port=6379)
r.set('test_key', 'test_value')
value = r.get('test_key')
if value == b'test_value':
    print('Redis client test passed')
    sys.exit(0)
else:
    print('Redis client test failed')
    sys.exit(1)
" 2>/dev/null; then
  echo -e "${GREEN}✓ Python 3 Redis client working correctly${NC}"
else
  echo -e "${RED}✗ Python 3 Redis client test failed${NC}"
  docker rm -f bacmon-python3-test
  exit 1
fi

# Test 6: Test core BACmon module imports
echo -e "\n${YELLOW}Testing BACmon core module imports...${NC}"
if docker exec bacmon-python3-test python -c "
import sys
sys.path.append('/app')

# Test core imports that should work in Python 3
try:
    import timeutil
    import bacpypes_compat
    print('Core module imports successful')
except Exception as e:
    print(f'Core module import failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
  echo -e "${GREEN}✓ BACmon core modules import successfully${NC}"
else
  echo -e "${RED}✗ BACmon core module import test failed${NC}"
  docker rm -f bacmon-python3-test
  exit 1
fi

# Clean up
echo -e "\n${YELLOW}Cleaning up test container...${NC}"
docker rm -f bacmon-python3-test >/dev/null 2>&1

echo -e "\n${GREEN}=== All Python 3 Docker tests passed! ===${NC}"
echo -e "${GREEN}The BACmon Docker configuration is ready for Python 3.${NC}"

exit 0 