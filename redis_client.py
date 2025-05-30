#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Redis Client Abstraction Layer for BACmon

This module provides a unified interface for Redis operations used in BACmon.
It encapsulates Redis client interactions and handles version differences and error
handling in a consistent way.
"""

import logging
import os
import redis
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Set up logging
logger = logging.getLogger(__name__)

# Type aliases
KeyT = Union[str, bytes]
ValueT = Union[str, bytes, int, float]


class RedisClient:
    """
    A wrapper around the Redis client to provide consistent interface and error handling.
    
    This class encapsulates all Redis operations used in BACmon and handles
    connection management, retries, and error handling uniformly.
    """
    
    def __init__(
        self, 
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        retry_on_timeout: bool = True,
        max_retries: int = 3,
        decode_responses: bool = False,
        health_check_interval: int = 30
    ):
        """
        Initialize the Redis client with the given parameters.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number
            password: Redis password for authentication
            socket_timeout: Socket timeout for Redis operations
            socket_connect_timeout: Socket connection timeout
            retry_on_timeout: Whether to retry operations on timeout
            max_retries: Maximum number of retries for operations
            decode_responses: Whether to decode Redis responses to strings
            health_check_interval: Interval for connection health checks
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.max_retries = max_retries
        self.decode_responses = decode_responses
        self.health_check_interval = health_check_interval
        
        # Initialize Redis connection pool
        self.connection_pool = redis.ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            socket_timeout=self.socket_timeout,
            socket_connect_timeout=self.socket_connect_timeout,
            health_check_interval=self.health_check_interval,
            decode_responses=self.decode_responses
        )
        
        # Initialize Redis client
        self._client = redis.Redis(
            connection_pool=self.connection_pool,
            retry_on_timeout=self.retry_on_timeout,
            max_retries=self.max_retries
        )
        
        # Test connection
        self.ping()
        logger.debug(f"Redis connection established to {self.host}:{self.port}/{self.db}")

    def __del__(self):
        """Clean up resources when the object is destroyed."""
        try:
            self.connection_pool.disconnect()
        except Exception:
            pass

    def _execute_with_retry(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute a Redis command with retry logic.
        
        Args:
            method_name: Name of the Redis method to execute
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method
            
        Returns:
            The result of the Redis command
        
        Raises:
            redis.RedisError: If the command fails after all retries
        """
        method = getattr(self._client, method_name)
        retries = 0
        last_error = None
        
        while retries <= self.max_retries:
            try:
                return method(*args, **kwargs)
            except (redis.ConnectionError, redis.TimeoutError) as e:
                retries += 1
                last_error = e
                if retries <= self.max_retries:
                    sleep_time = 0.1 * (2 ** retries)  # Exponential backoff
                    logger.warning(f"Redis operation failed, retrying in {sleep_time:.2f}s: {e}")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Redis operation failed after {retries} retries: {e}")
                    raise
            except redis.RedisError as e:
                logger.error(f"Redis error during {method_name}: {e}")
                raise
        
        # This should never happen, but just in case
        if last_error:
            raise last_error
        else:
            raise redis.RedisError(f"Unknown error in Redis operation {method_name}")

    def ping(self) -> bool:
        """
        Test connection to Redis server.
        
        Returns:
            True if the connection is alive
            
        Raises:
            redis.ConnectionError: If connection cannot be established
        """
        return self._execute_with_retry('ping')

    # Key-value operations
    def get(self, key: KeyT) -> Optional[bytes]:
        """Get the value of a key."""
        return self._execute_with_retry('get', key)
    
    def set(self, key: KeyT, value: ValueT, ex: Optional[int] = None, 
            px: Optional[int] = None, nx: bool = False, xx: bool = False) -> bool:
        """Set the value of a key with optional expiration."""
        return self._execute_with_retry('set', key, value, ex=ex, px=px, nx=nx, xx=xx)
    
    def delete(self, *keys: KeyT) -> int:
        """Delete one or more keys."""
        return self._execute_with_retry('delete', *keys)
    
    def exists(self, *keys: KeyT) -> int:
        """Check if one or more keys exist."""
        return self._execute_with_retry('exists', *keys)
    
    def expire(self, key: KeyT, time: int) -> bool:
        """Set a key's time to live in seconds."""
        return self._execute_with_retry('expire', key, time)
    
    def ttl(self, key: KeyT) -> int:
        """Get the time to live for a key in seconds."""
        return self._execute_with_retry('ttl', key)

    # Set operations
    def sadd(self, key: KeyT, *members: ValueT) -> int:
        """Add one or more members to a set."""
        return self._execute_with_retry('sadd', key, *members)
    
    def smembers(self, key: KeyT) -> Set[bytes]:
        """Get all members in a set."""
        return self._execute_with_retry('smembers', key)
    
    def srem(self, key: KeyT, *members: ValueT) -> int:
        """Remove one or more members from a set."""
        return self._execute_with_retry('srem', key, *members)
    
    def sismember(self, key: KeyT, member: ValueT) -> bool:
        """Check if member is in set."""
        return self._execute_with_retry('sismember', key, member)

    # List operations
    def lpush(self, key: KeyT, *values: ValueT) -> int:
        """Prepend one or more values to a list."""
        return self._execute_with_retry('lpush', key, *values)
    
    def rpush(self, key: KeyT, *values: ValueT) -> int:
        """Append one or more values to a list."""
        return self._execute_with_retry('rpush', key, *values)
    
    def lrange(self, key: KeyT, start: int, end: int) -> List[bytes]:
        """Get a range of elements from a list."""
        return self._execute_with_retry('lrange', key, start, end)
    
    def llen(self, key: KeyT) -> int:
        """Get the length of a list."""
        return self._execute_with_retry('llen', key)
    
    def ltrim(self, key: KeyT, start: int, end: int) -> bool:
        """Trim a list to the specified range."""
        return self._execute_with_retry('ltrim', key, start, end)

    # Hash operations
    def hset(self, key: KeyT, field: ValueT, value: ValueT) -> int:
        """Set the string value of a hash field."""
        return self._execute_with_retry('hset', key, field, value)
    
    def hget(self, key: KeyT, field: ValueT) -> Optional[bytes]:
        """Get the value of a hash field."""
        return self._execute_with_retry('hget', key, field)
    
    def hmset(self, key: KeyT, mapping: Dict[ValueT, ValueT]) -> bool:
        """Set multiple hash fields to multiple values."""
        return self._execute_with_retry('hmset', key, mapping)
    
    def hgetall(self, key: KeyT) -> Dict[bytes, bytes]:
        """Get all the fields and values in a hash."""
        return self._execute_with_retry('hgetall', key)

    # Counter operations
    def incr(self, key: KeyT, amount: int = 1) -> int:
        """Increment the integer value of a key by the given amount."""
        return self._execute_with_retry('incr', key, amount)
    
    def decr(self, key: KeyT, amount: int = 1) -> int:
        """Decrement the integer value of a key by the given amount."""
        return self._execute_with_retry('decr', key, amount)

    # Server operations
    def info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Get information and statistics about the server."""
        return self._execute_with_retry('info', section)
    
    def dbsize(self) -> int:
        """Get the number of keys in the selected database."""
        return self._execute_with_retry('dbsize')
    
    def flushdb(self) -> bool:
        """Remove all keys from the current database."""
        return self._execute_with_retry('flushdb')
    
    def type(self, key: KeyT) -> str:
        """Get the type stored at key."""
        return self._execute_with_retry('type', key)
    
    def get_timestamp(self) -> int:
        """Get the current timestamp."""
        return int(time.time())
    
    def set_startup_time(self) -> bool:
        """Set the startup time of the BACmon daemon."""
        return self.set('startup_time', self.get_timestamp())
    
    def set_daemon_version(self, version: str) -> bool:
        """Set the version of the BACmon daemon."""
        return self.set('daemon_version', version)

    # Optimization operations (optional integration with redis_optimizer)
    def get_memory_usage(self, key: KeyT) -> Optional[int]:
        """
        Get the memory usage of a key in bytes.
        
        Args:
            key: Redis key to check
            
        Returns:
            Memory usage in bytes, or None if not available
        """
        try:
            return self._execute_with_retry('memory_usage', key)
        except (redis.RedisError, AttributeError):
            # MEMORY USAGE command not available in older Redis versions
            return None
    
    def scan_keys(self, pattern: str = "*", count: int = 1000) -> List[str]:
        """
        Scan for keys matching a pattern.
        
        Args:
            pattern: Pattern to match keys against
            count: Hint for number of elements to return per iteration
            
        Returns:
            List of matching keys
        """
        try:
            cursor = 0
            keys = []
            while True:
                cursor, batch_keys = self._execute_with_retry('scan', cursor, match=pattern, count=count)
                if isinstance(batch_keys, list):
                    keys.extend([key.decode('utf-8') if isinstance(key, bytes) else str(key) for key in batch_keys])
                
                if cursor == 0:
                    break
            return keys
        except Exception as e:
            logger.error(f"Failed to scan keys with pattern {pattern}: {e}")
            return []
    
    def pipeline(self):
        """
        Create a Redis pipeline for batch operations.
        
        Returns:
            Redis pipeline object
        """
        return self._client.pipeline()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get information about the Redis connection.
        
        Returns:
            Dictionary with connection information
        """
        return {
            'host': self.host,
            'port': self.port,
            'db': self.db,
            'socket_timeout': self.socket_timeout,
            'socket_connect_timeout': self.socket_connect_timeout,
            'max_retries': self.max_retries,
            'decode_responses': self.decode_responses,
            'health_check_interval': self.health_check_interval
        }


def create_redis_client(config=None) -> RedisClient:
    """
    Create a RedisClient instance with the given configuration.
    
    Args:
        config: A dictionary of configuration parameters for the RedisClient.
               If None, default values will be used.
               
    Returns:
        A RedisClient instance
    """
    if config is None:
        config = {}
    
    # Set defaults for any missing configuration
    default_config = {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None,
        'socket_timeout': 5.0,
        'socket_connect_timeout': 5.0,
        'retry_on_timeout': True,
        'max_retries': 3,
        'decode_responses': False,  # Keep binary responses for compatibility with existing code
        'health_check_interval': 30
    }
    
    # Update defaults with provided configuration
    for key, value in config.items():
        default_config[key] = value
    
    # Create and return the client
    return RedisClient(**default_config) 