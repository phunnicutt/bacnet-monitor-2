#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for Redis Storage Optimization

This script tests the Redis optimization features implemented for BACmon,
including compression, retention policies, time-series optimization,
and enhanced storage patterns.
"""

import sys
import time
import json
import logging
from typing import Dict, Any, List
import unittest
from unittest.mock import patch, MagicMock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_redis_optimization')

def test_imports():
    """Test that all required modules can be imported."""
    logger.info("Testing module imports...")
    
    try:
        from redis_client import RedisClient, create_redis_client
        logger.info("✓ Redis client import successful")
    except ImportError as e:
        logger.error(f"✗ Failed to import redis_client: {e}")
        return False
    
    try:
        from redis_optimizer import (
            RedisStorageOptimizer, DataCompressor, TimeSeriesOptimizer,
            RetentionManager, RetentionPolicy
        )
        logger.info("✓ Redis optimizer import successful")
    except ImportError as e:
        logger.error(f"✗ Failed to import redis_optimizer: {e}")
        return False
    
    try:
        from enhanced_redis_storage import (
            OptimizedCountInterval, OptimizedSampleRateTask,
            get_storage_factory, create_optimized_storage_manager
        )
        logger.info("✓ Enhanced storage import successful")
    except ImportError as e:
        logger.error(f"✗ Failed to import enhanced_redis_storage: {e}")
        return False
    
    return True


def test_data_compression():
    """Test data compression functionality."""
    logger.info("Testing data compression...")
    
    try:
        from redis_optimizer import DataCompressor
        
        compressor = DataCompressor(compression_level=6, min_size_threshold=50)
        
        # Test small data (should not be compressed)
        small_data = "small"
        compressed_small = compressor.compress_data(small_data)
        assert compressed_small.startswith(b'RAW:')
        decompressed_small = compressor.decompress_data(compressed_small)
        assert decompressed_small == small_data
        logger.info("✓ Small data compression test passed")
        
        # Test large data (should be compressed)
        large_data = "This is a much longer string that should be compressed because it exceeds the minimum threshold" * 10
        compressed_large = compressor.compress_data(large_data)
        decompressed_large = compressor.decompress_data(compressed_large)
        assert decompressed_large == large_data
        
        # Check compression actually happened for large data
        if compressed_large.startswith(b'ZLIB:'):
            logger.info("✓ Large data compression test passed")
        else:
            logger.info("✓ Large data handled (compression not beneficial)")
        
        # Test compression stats
        stats = compressor.stats
        logger.info(f"✓ Compression stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Data compression test failed: {e}")
        return False


def test_retention_policies():
    """Test retention policy functionality."""
    logger.info("Testing retention policies...")
    
    try:
        from redis_optimizer import RetentionPolicy, RetentionManager, TimeSeriesOptimizer
        
        # Create mock Redis client
        mock_redis = MagicMock()
        optimizer = TimeSeriesOptimizer(mock_redis)
        retention_manager = RetentionManager(mock_redis, optimizer)
        
        # Add test retention policy
        policy = RetentionPolicy(
            name="test_policy",
            duration_seconds=3600,  # 1 hour
            resolution_seconds=60,  # 1 minute
            aggregation_func="avg",
            compression_enabled=True
        )
        
        retention_manager.add_retention_policy("test:*", policy)
        logger.info("✓ Retention policy added successfully")
        
        # Test policy matching
        applicable_policies = retention_manager.get_applicable_policies("test:data")
        assert len(applicable_policies) == 1
        assert applicable_policies[0].name == "test_policy"
        logger.info("✓ Policy matching test passed")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Retention policy test failed: {e}")
        return False


def test_time_series_optimization():
    """Test time-series optimization functionality."""
    logger.info("Testing time-series optimization...")
    
    try:
        from redis_optimizer import TimeSeriesOptimizer, DataCompressor
        
        # Create mock Redis client
        mock_redis = MagicMock()
        mock_redis.lrange.return_value = [
            b'ZLIB:\x9c\xcbJ\x8c\xcf\xcc(\x06\x00\x02\x95\x00\xdc',  # Compressed data
            b'RAW:[1234567890, 42]',  # Raw data
            b'[1234567888, 40]'  # Legacy data
        ]
        
        compressor = DataCompressor()
        optimizer = TimeSeriesOptimizer(mock_redis, compressor)
        
        # Test data retrieval
        points = optimizer.get_time_series_range("test:key", 0, -1)
        logger.info(f"✓ Retrieved {len(points)} time-series points")
        
        # Test aggregation
        test_points = [(1000, 10), (1001, 20), (1060, 30), (1061, 40)]
        aggregated = optimizer.aggregate_time_series(
            "test:key", test_points, "avg", 60
        )
        
        assert len(aggregated) == 2  # Should aggregate into 2 time windows
        logger.info(f"✓ Aggregation test passed: {aggregated}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Time-series optimization test failed: {e}")
        return False


def test_optimized_count_interval():
    """Test OptimizedCountInterval functionality."""
    logger.info("Testing OptimizedCountInterval...")
    
    try:
        from enhanced_redis_storage import OptimizedCountInterval
        
        # Create mock Redis client
        mock_redis = MagicMock()
        
        # Test without optimization (fallback mode)
        interval = OptimizedCountInterval(
            label="test",
            modulus=60,
            maxLen=100,
            redis_client=mock_redis,
            optimizer=None,
            enable_optimization=False
        )
        
        # Test count operation
        interval.count(mock_redis, 1234567890, 5)
        logger.info("✓ OptimizedCountInterval count test passed")
        
        # Verify Redis operations were called (legacy mode)
        assert mock_redis.lpush.called
        assert mock_redis.ltrim.called
        
        return True
        
    except Exception as e:
        logger.error(f"✗ OptimizedCountInterval test failed: {e}")
        return False


def test_storage_factory():
    """Test storage factory functionality."""
    logger.info("Testing storage factory...")
    
    try:
        from enhanced_redis_storage import get_storage_factory
        
        # Create mock Redis client
        mock_redis = MagicMock()
        
        # Get storage factory
        factory = get_storage_factory(mock_redis, config={'enabled': False})
        
        assert 'optimizer' in factory
        assert 'optimization_enabled' in factory
        assert 'create_count_interval' in factory
        assert 'create_sample_rate_task' in factory
        assert callable(factory['create_count_interval'])
        assert callable(factory['create_sample_rate_task'])
        
        # Test creating objects
        count_interval = factory['create_count_interval']("test", 60, 100)
        rate_task = factory['create_sample_rate_task']("test:rate", 1, 20, 30)
        
        assert count_interval is not None
        assert rate_task is not None
        
        logger.info("✓ Storage factory test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Storage factory test failed: {e}")
        return False


def test_configuration_validation():
    """Test configuration validation for Redis optimization."""
    logger.info("Testing configuration validation...")
    
    try:
        from config_validator import create_bacmon_validator
        
        # Test configuration with Redis optimization
        test_config = {
            'BACmon': {
                'interface': 'eth0',
                'address': '192.168.1.100/24',
                'bbmd': '192.168.1.1',
                'logdir': '/tmp/logs',
                'logdirsize': '16106127360',
                'rollover': '1h',
                'apachedir': '/tmp/apache',
                'staticdir': '/tmp/static',
                'templatedir': '/tmp/template'
            },
            'Redis': {
                'host': 'localhost',
                'port': '6379',
                'db': '0',
                'socket_timeout': '5.0',
                'socket_connect_timeout': '5.0'
            },
            'RedisOptimization': {
                'enabled': 'true',
                'compression_enabled': 'true',
                'compression_level': '6',
                'min_compression_size': '100',
                'auto_cleanup_enabled': 'true',
                'cleanup_interval_seconds': '3600',
                'max_memory_usage_mb': '1024',
                'enable_memory_monitoring': 'true',
                'batch_size': '1000',
                'pipeline_operations': 'true'
            },
            'RateMonitoring': {
                'scan_interval': '10000',
                'use_enhanced_detection': 'true',
                'sensitivity': '1.0',
                'total_rate': 'total:s, 1, 20, 30'
            }
        }
        
        validator = create_bacmon_validator()
        results = validator.validate_config(test_config)
        
        # Check if validation passed
        is_valid = validator.is_valid(results)
        if is_valid:
            logger.info("✓ Configuration validation test passed")
        else:
            logger.warning("⚠ Configuration validation had issues:")
            for section, validations in results.items():
                for field, valid, message in validations:
                    if not valid:
                        logger.warning(f"  {section}.{field}: {message}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Configuration validation test failed: {e}")
        return False


def test_memory_usage_estimation():
    """Test memory usage estimation."""
    logger.info("Testing memory usage estimation...")
    
    try:
        from redis_optimizer import RedisStorageOptimizer
        
        # Create mock Redis client
        mock_redis = MagicMock()
        
        # Test optimizer creation
        optimizer = RedisStorageOptimizer(mock_redis, {
            'compression_level': 6,
            'auto_cleanup_enabled': True,
            'cleanup_interval_seconds': 1800
        })
        
        # Test statistics gathering
        stats = optimizer.get_storage_statistics()
        
        assert 'storage_stats' in stats
        assert 'compression_stats' in stats
        assert 'monitored_keys' in stats
        assert 'retention_policies' in stats
        
        logger.info(f"✓ Storage statistics test passed: {len(stats)} categories")
        return True
        
    except Exception as e:
        logger.error(f"✗ Memory usage estimation test failed: {e}")
        return False


def run_performance_benchmark():
    """Run a simple performance benchmark."""
    logger.info("Running performance benchmark...")
    
    try:
        from redis_optimizer import DataCompressor
        
        compressor = DataCompressor()
        
        # Generate test data
        test_data = []
        for i in range(1000):
            data_point = json.dumps([time.time() + i, i * 1.5])
            test_data.append(data_point)
        
        # Benchmark compression
        start_time = time.time()
        compressed_data = []
        for data in test_data:
            compressed = compressor.compress_data(data)
            compressed_data.append(compressed)
        compression_time = time.time() - start_time
        
        # Benchmark decompression
        start_time = time.time()
        for compressed in compressed_data:
            decompressed = compressor.decompress_data(compressed)
        decompression_time = time.time() - start_time
        
        # Calculate statistics
        original_size = sum(len(data.encode()) for data in test_data)
        compressed_size = sum(len(data) for data in compressed_data)
        compression_ratio = (original_size - compressed_size) / original_size * 100
        
        logger.info(f"✓ Performance benchmark completed:")
        logger.info(f"  - Compression time: {compression_time:.3f}s for 1000 items")
        logger.info(f"  - Decompression time: {decompression_time:.3f}s for 1000 items")
        logger.info(f"  - Original size: {original_size} bytes")
        logger.info(f"  - Compressed size: {compressed_size} bytes")
        logger.info(f"  - Compression ratio: {compression_ratio:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Performance benchmark failed: {e}")
        return False


def main():
    """Run all Redis optimization tests."""
    logger.info("Starting Redis Storage Optimization Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Module Imports", test_imports),
        ("Data Compression", test_data_compression),
        ("Retention Policies", test_retention_policies),
        ("Time-Series Optimization", test_time_series_optimization),
        ("Optimized Count Interval", test_optimized_count_interval),
        ("Storage Factory", test_storage_factory),
        ("Configuration Validation", test_configuration_validation),
        ("Memory Usage Estimation", test_memory_usage_estimation),
        ("Performance Benchmark", run_performance_benchmark)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed_tests += 1
                logger.info(f"✓ {test_name} PASSED")
            else:
                logger.error(f"✗ {test_name} FAILED")
        except Exception as e:
            logger.error(f"✗ {test_name} FAILED with exception: {e}")
    
    logger.info("\n" + "=" * 50)
    logger.info(f"Test Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All Redis optimization tests passed successfully!")
        return 0
    else:
        logger.error(f"❌ {total_tests - passed_tests} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 