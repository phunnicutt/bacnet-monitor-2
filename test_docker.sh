#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== BACmon Docker Container Test ===${NC}"

# Build the Docker image
echo -e "\n${YELLOW}Building Docker image...${NC}"
docker build -t bacmon:latest .
if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Docker image built successfully${NC}"
else
  echo -e "${RED}✗ Failed to build Docker image${NC}"
  exit 1
fi

# Check if the container is already running
CONTAINER_ID=$(docker ps -q --filter "name=bacmon-test")
if [ ! -z "$CONTAINER_ID" ]; then
  echo -e "\n${YELLOW}Stopping existing container...${NC}"
  docker stop bacmon-test
  docker rm bacmon-test
fi

# Run the container in detached mode with different port to avoid conflicts
echo -e "\n${YELLOW}Starting container...${NC}"
docker run -d --name bacmon-test -p 6380:6379 -p 47809:47808/udp bacmon:latest
if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Container started successfully${NC}"
else
  echo -e "${RED}✗ Failed to start container${NC}"
  exit 1
fi

# Wait for services to start up
echo -e "\n${YELLOW}Waiting for services to initialize...${NC}"
sleep 5

# Check if Redis is running
echo -e "\n${YELLOW}Testing Redis connection...${NC}"
docker exec bacmon-test redis-cli ping
if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Redis is running correctly${NC}"
else
  echo -e "${RED}✗ Redis test failed${NC}"
  docker logs bacmon-test
  docker stop bacmon-test
  docker rm bacmon-test
  exit 1
fi

# Check if BACmon is running
echo -e "\n${YELLOW}Checking BACmon process...${NC}"
docker exec bacmon-test ps aux | grep -v grep | grep "python3 BACmon.py"
if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ BACmon process is running${NC}"
else
  echo -e "${RED}✗ BACmon process is not running${NC}"
  docker logs bacmon-test
  docker stop bacmon-test
  docker rm bacmon-test
  exit 1
fi

# Display container logs
echo -e "\n${YELLOW}Container logs:${NC}"
docker logs bacmon-test

echo -e "\n${GREEN}=== All tests passed! ===${NC}"
echo -e "${YELLOW}The container is still running for manual testing. To stop it:${NC}"
echo -e "docker stop bacmon-test && docker rm bacmon-test"

exit 0 