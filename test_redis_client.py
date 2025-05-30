#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for the Redis client wrapper

This script tests the RedisClient class to ensure it works correctly
with BACmon.py. It includes three test strategies:
1. API verification (checking that all required methods exist)
2. Live Redis server tests (when a Redis server is available)
3. Mock-based tests (that don't require a running Redis server)
"""

import sys
import logging
import time
import os
import unittest
from typing import List, Dict, Any, Optional, Set, Callable, Tuple, Union, cast, Type, TypeVar, NoReturn
from unittest.mock import patch, MagicMock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_redis_client')

# Import the RedisClient
try:
    from redis_client import RedisClient, create_redis_client
    import redis
except ImportError as e:
    logger.error(f"Cannot import required modules: {e}")
    logger.error("Make sure redis_client.py is in the current directory and redis package is installed.")
    sys.exit(1)

def is_redis_available() -> bool:
    """Check if Redis server is available."""
    try:
        r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
        return r.ping()
    except (redis.ConnectionError, redis.TimeoutError):
        return False

def test_redis_client_api() -> bool:
    """Test only the RedisClient API without connecting to an actual Redis server."""
    logger.info("Testing Redis client API without server connection...")
    
    # Verify the class exists and has the required methods
    required_methods: List[str] = [
        'get', 'set', 'delete', 'exists', 'sadd', 'smembers', 'srem',
        'lpush', 'lrange', 'ltrim', 'incr', 'set_startup_time', 'set_daemon_version'
    ]
    
    missing_methods: List[str] = []
    for method in required_methods:
        if not hasattr(RedisClient, method):
            missing_methods.append(method)
    
    if missing_methods:
        logger.error(f"✗ Missing required methods in RedisClient: {', '.join(missing_methods)}")
        return False
    else:
        logger.info("✓ All required methods are present in RedisClient")
    
    # Verify the factory function exists
    if not callable(create_redis_client):
        logger.error("✗ create_redis_client is not callable")
        return False
    else:
        logger.info("✓ create_redis_client function is available")
    
    logger.info("Redis client API tests passed!")
    return True

def test_redis_client_with_server() -> bool:
    """Test the RedisClient functionality using a live Redis server."""
    logger.info("Starting Redis client functional tests with actual server...")
    
    # Create a client with default settings
    try:
        r = create_redis_client()
        logger.info("✓ Successfully created Redis client")
    except Exception as e:
        logger.error(f"✗ Failed to create Redis client: {e}")
        return False
    
    # Test ping
    try:
        r.ping()
        logger.info("✓ Successfully pinged Redis server")
    except Exception as e:
        logger.error(f"✗ Failed to ping Redis server: {e}")
        return False
    
    # Create a test key prefix to avoid interference with other data
    test_prefix: str = f"test:redis:client:{int(time.time())}"
    
    # Test basic key-value operations
    try:
        # Set and Get
        key: str = f"{test_prefix}:key"
        r.set(key, "test-value")
        value: Optional[bytes] = r.get(key)
        if value == b"test-value":
            logger.info("✓ Successfully set and retrieved key-value pair")
        else:
            logger.error(f"✗ Failed to retrieve correct value. Expected 'test-value', got '{value}'")
            return False
            
        # Delete
        r.delete(key)
        if r.get(key) is None:
            logger.info("✓ Successfully deleted key")
        else:
            logger.error("✗ Failed to delete key")
            return False
    except Exception as e:
        logger.error(f"✗ Error during key-value tests: {e}")
        return False
    
    # Test set operations
    try:
        set_key: str = f"{test_prefix}:set"
        r.sadd(set_key, "item1", "item2", "item3")
        members: Set[bytes] = r.smembers(set_key)
        if len(members) == 3 and b"item1" in members and b"item2" in members and b"item3" in members:
            logger.info("✓ Successfully added items to set")
        else:
            logger.error(f"✗ Failed to add items to set correctly. Got: {members}")
            return False
            
        r.srem(set_key, "item2")
        members = r.smembers(set_key)
        if len(members) == 2 and b"item1" in members and b"item3" in members:
            logger.info("✓ Successfully removed item from set")
        else:
            logger.error(f"✗ Failed to remove item from set correctly. Got: {members}")
            return False
            
        r.delete(set_key)
    except Exception as e:
        logger.error(f"✗ Error during set tests: {e}")
        return False
    
    # Test list operations
    try:
        list_key: str = f"{test_prefix}:list"
        r.lpush(list_key, "item3", "item2", "item1")
        items: List[bytes] = r.lrange(list_key, 0, -1)
        if len(items) == 3 and items[0] == b"item1" and items[1] == b"item2" and items[2] == b"item3":
            logger.info("✓ Successfully added items to list")
        else:
            logger.error(f"✗ Failed to add items to list correctly. Got: {items}")
            return False
            
        r.ltrim(list_key, 0, 1)
        items = r.lrange(list_key, 0, -1)
        if len(items) == 2 and items[0] == b"item1" and items[1] == b"item2":
            logger.info("✓ Successfully trimmed list")
        else:
            logger.error(f"✗ Failed to trim list correctly. Got: {items}")
            return False
            
        r.delete(list_key)
    except Exception as e:
        logger.error(f"✗ Error during list tests: {e}")
        return False
    
    # Test counter operations
    try:
        counter_key: str = f"{test_prefix}:counter"
        r.set(counter_key, 0)
        r.incr(counter_key)
        r.incr(counter_key, 2)
        count: int = int(r.get(counter_key))
        if count == 3:
            logger.info("✓ Successfully incremented counter")
        else:
            logger.error(f"✗ Failed to increment counter correctly. Expected 3, got {count}")
            return False
            
        r.delete(counter_key)
    except Exception as e:
        logger.error(f"✗ Error during counter tests: {e}")
        return False
    
    # Test BACmon specific methods
    try:
        r.set_startup_time()
        startup_time: Optional[bytes] = r.get("startup_time")
        if startup_time and int(startup_time) > 0:
            logger.info("✓ Successfully set startup time")
        else:
            logger.error(f"✗ Failed to set startup time correctly. Got: {startup_time}")
            return False
        
        version: str = "1.0.0-test"
        r.set_daemon_version(version)
        stored_version: Optional[bytes] = r.get("daemon_version")
        if stored_version == version.encode():
            logger.info("✓ Successfully set daemon version")
        else:
            logger.error(f"✗ Failed to set daemon version correctly. Expected {version}, got {stored_version}")
            return False
        
        # Clean up
        r.delete("startup_time", "daemon_version")
    except Exception as e:
        logger.error(f"✗ Error during BACmon specific tests: {e}")
        return False
    
    logger.info("All Redis client functional tests passed successfully!")
    return True

class TestRedisClientWithMocks(unittest.TestCase):
    """Unit tests for RedisClient using mocks to avoid needing a real Redis server."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.redis_mock_patcher = patch('redis_client.redis.Redis')
        self.redis_mock = self.redis_mock_patcher.start()
        
        # Create a mock Redis client instance
        self.mock_client = MagicMock()
        self.redis_mock.return_value = self.mock_client
        
        # Make ping return True by default
        self.mock_client.ping.return_value = True
        
        # Create RedisClient with the mock
        self.client = RedisClient()
    
    def tearDown(self) -> None:
        """Tear down test fixtures."""
        self.redis_mock_patcher.stop()
    
    def test_connection_init(self) -> None:
        """Test that RedisClient initializes with correct parameters."""
        self.redis_mock.assert_called_once()
        # Verify connection_pool was used
        self.assertIn('connection_pool', self.redis_mock.call_args[1])
    
    def test_ping(self) -> None:
        """Test ping operation."""
        result: bool = self.client.ping()
        # Note: We expect two calls because ping is called during initialization
        # and then called again in this test
        self.assertEqual(self.mock_client.ping.call_count, 2)
        self.assertTrue(result)
    
    def test_get(self) -> None:
        """Test get operation."""
        self.mock_client.get.return_value = b"test-value"
        result: Optional[bytes] = self.client.get("test-key")
        self.mock_client.get.assert_called_once_with("test-key")
        self.assertEqual(result, b"test-value")
    
    def test_set(self) -> None:
        """Test set operation."""
        self.mock_client.set.return_value = True
        result: bool = self.client.set("test-key", "test-value")
        self.mock_client.set.assert_called_once()
        self.assertTrue(result)
    
    def test_delete(self) -> None:
        """Test delete operation."""
        self.mock_client.delete.return_value = 1
        result: int = self.client.delete("test-key")
        self.mock_client.delete.assert_called_once_with("test-key")
        self.assertEqual(result, 1)
    
    def test_sadd(self) -> None:
        """Test sadd operation."""
        self.mock_client.sadd.return_value = 3
        result: int = self.client.sadd("test-set", "item1", "item2", "item3")
        self.mock_client.sadd.assert_called_once_with("test-set", "item1", "item2", "item3")
        self.assertEqual(result, 3)
    
    def test_smembers(self) -> None:
        """Test smembers operation."""
        self.mock_client.smembers.return_value = {b"item1", b"item2", b"item3"}
        result: Set[bytes] = self.client.smembers("test-set")
        self.mock_client.smembers.assert_called_once_with("test-set")
        self.assertEqual(result, {b"item1", b"item2", b"item3"})
    
    def test_lpush(self) -> None:
        """Test lpush operation."""
        self.mock_client.lpush.return_value = 3
        result: int = self.client.lpush("test-list", "item1", "item2", "item3")
        self.mock_client.lpush.assert_called_once_with("test-list", "item1", "item2", "item3")
        self.assertEqual(result, 3)
    
    def test_lrange(self) -> None:
        """Test lrange operation."""
        self.mock_client.lrange.return_value = [b"item1", b"item2", b"item3"]
        result: List[bytes] = self.client.lrange("test-list", 0, -1)
        self.mock_client.lrange.assert_called_once_with("test-list", 0, -1)
        self.assertEqual(result, [b"item1", b"item2", b"item3"])
    
    def test_ltrim(self) -> None:
        """Test ltrim operation."""
        self.mock_client.ltrim.return_value = True
        result: bool = self.client.ltrim("test-list", 0, 1)
        self.mock_client.ltrim.assert_called_once_with("test-list", 0, 1)
        self.assertTrue(result)
    
    def test_incr(self) -> None:
        """Test incr operation."""
        self.mock_client.incr.return_value = 3
        result: int = self.client.incr("test-counter", 3)
        self.mock_client.incr.assert_called_once_with("test-counter", 3)
        self.assertEqual(result, 3)
    
    def test_retry_mechanism(self) -> None:
        """Test that retry mechanism works."""
        # Make the mock raise ConnectionError on first call, then succeed
        self.mock_client.get.side_effect = [redis.ConnectionError("Test error"), b"test-value"]
        
        # Should retry and succeed
        result: Optional[bytes] = self.client.get("test-key")
        self.assertEqual(self.mock_client.get.call_count, 2)
        self.assertEqual(result, b"test-value")
    
    def test_set_startup_time(self) -> None:
        """Test set_startup_time method."""
        self.mock_client.set.return_value = True
        with patch('redis_client.time.time', return_value=12345):
            result: bool = self.client.set_startup_time()
            # Include all expected parameters
            self.mock_client.set.assert_called_once_with('startup_time', 12345, ex=None, px=None, nx=False, xx=False)
            self.assertTrue(result)
    
    def test_set_daemon_version(self) -> None:
        """Test set_daemon_version method."""
        self.mock_client.set.return_value = True
        result: bool = self.client.set_daemon_version("1.0.0")
        # Include all expected parameters
        self.mock_client.set.assert_called_once_with('daemon_version', "1.0.0", ex=None, px=None, nx=False, xx=False)
        self.assertTrue(result)

def run_mock_tests() -> bool:
    """Run the mock-based unit tests."""
    logger.info("Running mock-based Redis client tests...")
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestRedisClientWithMocks)
    test_result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return test_result.wasSuccessful()

if __name__ == "__main__":
    # Always test the API
    api_ok: bool = test_redis_client_api()
    
    # Run mock-based tests (don't require Redis server)
    mock_tests_ok: bool = run_mock_tests()
    
    # Test with server only if available
    redis_available: bool = is_redis_available()
    if redis_available:
        logger.info("Redis server is available, proceeding with functional tests...")
        server_tests_ok: bool = test_redis_client_with_server()
    else:
        logger.warning("Redis server is not available. Skipping functional tests.")
        logger.warning("To run complete tests, ensure Redis server is running on localhost:6379")
        server_tests_ok: bool = True  # Skip server tests if Redis is not available
    
    # Exit with appropriate status
    if api_ok and server_tests_ok and mock_tests_ok:
        logger.info("SUCCESS: All Redis client wrapper tests passed.")
        sys.exit(0)
    else:
        if not api_ok:
            logger.error("FAILURE: Redis client API tests failed.")
        if not mock_tests_ok:
            logger.error("FAILURE: Redis client mock tests failed.")
        if redis_available and not server_tests_ok:
            logger.error("FAILURE: Redis client functional tests failed.")
        sys.exit(1) 