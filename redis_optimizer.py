#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Redis Storage Optimization Module for BACmon

This module provides advanced Redis storage optimization features for BACmon's
rate monitoring system, including data compression, retention policies,
time-series optimizations, and memory management.
"""

import json
import logging
import time
import zlib
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
import math
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Type aliases
TimestampT = Union[int, float]
ValueT = Union[int, float, str, bytes]
TimeSeriesPoint = Tuple[TimestampT, ValueT]
AggregationFunc = Callable[[List[ValueT]], ValueT]


@dataclass
class RetentionPolicy:
    """
    Configuration for data retention and aggregation policies.
    
    Defines how long to keep data at different granularities and
    how to aggregate data when moving between retention levels.
    """
    name: str
    duration_seconds: int
    resolution_seconds: int
    aggregation_func: str = "avg"  # avg, max, min, sum, count, first, last
    compression_enabled: bool = True
    auto_cleanup: bool = True


@dataclass
class StorageStats:
    """Statistics for Redis storage optimization."""
    total_keys: int = 0
    compressed_keys: int = 0
    total_memory_bytes: int = 0
    compressed_memory_bytes: int = 0
    compression_ratio: float = 0.0
    last_cleanup_time: float = 0.0
    data_points_stored: int = 0
    data_points_aggregated: int = 0


class DataCompressor:
    """Handles data compression and decompression for Redis storage."""
    
    def __init__(self, compression_level: int = 6, min_size_threshold: int = 100):
        """
        Initialize the data compressor.
        
        Args:
            compression_level: zlib compression level (1-9, higher = better compression)
            min_size_threshold: Minimum data size in bytes before compression is applied
        """
        self.compression_level = compression_level
        self.min_size_threshold = min_size_threshold
        self.stats = {'compressed': 0, 'decompressed': 0, 'bytes_saved': 0}
    
    def compress_data(self, data: Union[str, bytes]) -> bytes:
        """
        Compress data using zlib compression.
        
        Args:
            data: Data to compress (string or bytes)
            
        Returns:
            Compressed data with compression marker
        """
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
            
        # Don't compress small data
        if len(data_bytes) < self.min_size_threshold:
            return b'RAW:' + data_bytes
            
        try:
            compressed = zlib.compress(data_bytes, self.compression_level)
            # Only use compression if it actually saves space
            if len(compressed) < len(data_bytes):
                self.stats['compressed'] += 1
                self.stats['bytes_saved'] += len(data_bytes) - len(compressed)
                return b'ZLIB:' + compressed
            else:
                return b'RAW:' + data_bytes
        except Exception as e:
            logger.warning(f"Compression failed, storing raw data: {e}")
            return b'RAW:' + data_bytes
    
    def decompress_data(self, data: bytes) -> str:
        """
        Decompress data based on compression marker.
        
        Args:
            data: Compressed data with marker
            
        Returns:
            Decompressed string data
        """
        if not isinstance(data, bytes):
            return str(data)
            
        if data.startswith(b'ZLIB:'):
            try:
                compressed_data = data[5:]  # Remove 'ZLIB:' prefix
                decompressed = zlib.decompress(compressed_data)
                self.stats['decompressed'] += 1
                return decompressed.decode('utf-8')
            except Exception as e:
                logger.error(f"Decompression failed: {e}")
                return data.decode('utf-8', errors='replace')
        elif data.startswith(b'RAW:'):
            return data[4:].decode('utf-8')  # Remove 'RAW:' prefix
        else:
            # Legacy data without compression markers
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                return data.decode('utf-8', errors='replace')


class TimeSeriesOptimizer:
    """Optimizes time-series data storage and retrieval in Redis."""
    
    def __init__(self, redis_client, compressor: Optional[DataCompressor] = None):
        """
        Initialize the time-series optimizer.
        
        Args:
            redis_client: Redis client instance
            compressor: Data compressor instance
        """
        self.redis_client = redis_client
        self.compressor = compressor or DataCompressor()
        self.aggregation_functions = {
            'avg': lambda values: sum(values) / len(values) if values else 0,
            'max': lambda values: max(values) if values else 0,
            'min': lambda values: min(values) if values else 0,
            'sum': lambda values: sum(values),
            'count': lambda values: len(values),
            'first': lambda values: values[0] if values else 0,
            'last': lambda values: values[-1] if values else 0
        }
    
    def store_time_series_point(
        self,
        key: str,
        timestamp: TimestampT,
        value: ValueT,
        max_points: Optional[int] = None,
        use_compression: bool = True
    ) -> bool:
        """
        Store a single time-series data point efficiently.
        
        Args:
            key: Redis key for the time series
            timestamp: Data point timestamp
            value: Data point value
            max_points: Maximum number of points to retain
            use_compression: Whether to use compression
            
        Returns:
            True if stored successfully
        """
        try:
            # Format data point
            data_point = json.dumps([timestamp, value])
            
            # Apply compression if enabled
            if use_compression:
                data_point = self.compressor.compress_data(data_point)
            
            # Store the data point
            pipeline = self.redis_client._client.pipeline()
            pipeline.lpush(key, data_point)
            
            # Trim to max points if specified
            if max_points:
                pipeline.ltrim(key, 0, max_points - 1)
            
            pipeline.execute()
            return True
            
        except Exception as e:
            logger.error(f"Failed to store time-series point for {key}: {e}")
            return False
    
    def get_time_series_range(
        self,
        key: str,
        start_index: int = 0,
        end_index: int = -1,
        start_time: Optional[TimestampT] = None,
        end_time: Optional[TimestampT] = None
    ) -> List[TimeSeriesPoint]:
        """
        Retrieve time-series data points with optional time filtering.
        
        Args:
            key: Redis key for the time series
            start_index: Start index for range query
            end_index: End index for range query
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of (timestamp, value) tuples
        """
        try:
            # Get raw data from Redis
            raw_data = self.redis_client.lrange(key, start_index, end_index)
            
            points = []
            for raw_point in raw_data:
                try:
                    # Decompress if needed
                    if isinstance(raw_point, bytes) and (
                        raw_point.startswith(b'ZLIB:') or raw_point.startswith(b'RAW:')
                    ):
                        data_str = self.compressor.decompress_data(raw_point)
                    else:
                        data_str = raw_point.decode('utf-8') if isinstance(raw_point, bytes) else str(raw_point)
                    
                    # Parse the data point
                    timestamp, value = json.loads(data_str)
                    
                    # Apply time filtering if specified
                    if start_time is not None and timestamp < start_time:
                        continue
                    if end_time is not None and timestamp > end_time:
                        continue
                        
                    points.append((timestamp, value))
                    
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse time-series point: {raw_point}, error: {e}")
                    continue
            
            return points
            
        except Exception as e:
            logger.error(f"Failed to retrieve time-series range for {key}: {e}")
            return []
    
    def aggregate_time_series(
        self,
        key: str,
        source_points: List[TimeSeriesPoint],
        aggregation_func: str,
        time_window_seconds: int
    ) -> List[TimeSeriesPoint]:
        """
        Aggregate time-series data points into larger time windows.
        
        Args:
            key: Redis key for logging purposes
            source_points: Source data points to aggregate
            aggregation_func: Aggregation function name
            time_window_seconds: Size of aggregation window in seconds
            
        Returns:
            List of aggregated (timestamp, value) tuples
        """
        if not source_points or aggregation_func not in self.aggregation_functions:
            return []
        
        try:
            # Group points by time windows
            time_windows = defaultdict(list)
            
            for timestamp, value in source_points:
                # Calculate window start time
                window_start = int(timestamp // time_window_seconds) * time_window_seconds
                time_windows[window_start].append(float(value) if isinstance(value, (int, float, str)) else 0)
            
            # Apply aggregation function to each window
            aggregated_points = []
            func = self.aggregation_functions[aggregation_func]
            
            for window_start, values in sorted(time_windows.items()):
                aggregated_value = func(values)
                aggregated_points.append((window_start, aggregated_value))
            
            return aggregated_points
            
        except Exception as e:
            logger.error(f"Failed to aggregate time-series data for {key}: {e}")
            return []


class RetentionManager:
    """Manages data retention policies and automatic cleanup."""
    
    def __init__(self, redis_client, optimizer: TimeSeriesOptimizer):
        """
        Initialize the retention manager.
        
        Args:
            redis_client: Redis client instance
            optimizer: Time-series optimizer instance
        """
        self.redis_client = redis_client
        self.optimizer = optimizer
        self.policies: Dict[str, List[RetentionPolicy]] = {}
        self.last_cleanup_times: Dict[str, float] = {}
        self.cleanup_lock = threading.Lock()
    
    def add_retention_policy(self, key_pattern: str, policy: RetentionPolicy) -> None:
        """
        Add a retention policy for keys matching a pattern.
        
        Args:
            key_pattern: Pattern to match Redis keys (supports wildcards)
            policy: Retention policy configuration
        """
        if key_pattern not in self.policies:
            self.policies[key_pattern] = []
        
        # Insert policy in order of duration (shortest first)
        policies = self.policies[key_pattern]
        insert_index = 0
        for i, existing_policy in enumerate(policies):
            if policy.duration_seconds < existing_policy.duration_seconds:
                insert_index = i
                break
            insert_index = i + 1
        
        policies.insert(insert_index, policy)
        logger.info(f"Added retention policy '{policy.name}' for pattern '{key_pattern}'")
    
    def get_applicable_policies(self, key: str) -> List[RetentionPolicy]:
        """
        Get retention policies applicable to a specific key.
        
        Args:
            key: Redis key
            
        Returns:
            List of applicable retention policies
        """
        applicable_policies = []
        
        for pattern, policies in self.policies.items():
            # Simple wildcard matching (supports * and ?)
            if self._match_pattern(key, pattern):
                applicable_policies.extend(policies)
        
        # Sort by duration (shortest first)
        applicable_policies.sort(key=lambda p: p.duration_seconds)
        return applicable_policies
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Simple wildcard pattern matching."""
        if '*' not in pattern and '?' not in pattern:
            return key == pattern
        
        # Convert to regex-like matching
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
    
    def apply_retention_policies(self, key: str, force: bool = False) -> Dict[str, Any]:
        """
        Apply retention policies to a specific key.
        
        Args:
            key: Redis key to process
            force: Force processing even if recently cleaned
            
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            'processed_policies': 0,
            'data_points_processed': 0,
            'data_points_removed': 0,
            'data_points_aggregated': 0,
            'memory_freed_bytes': 0
        }
        
        try:
            # Check if cleanup is needed
            current_time = time.time()
            last_cleanup = self.last_cleanup_times.get(key, 0)
            
            if not force and (current_time - last_cleanup) < 300:  # 5 minutes minimum between cleanups
                return stats
            
            with self.cleanup_lock:
                policies = self.get_applicable_policies(key)
                if not policies:
                    return stats
                
                # Get current data
                current_points = self.optimizer.get_time_series_range(key, 0, -1)
                if not current_points:
                    return stats
                
                stats['data_points_processed'] = len(current_points)
                
                # Process each retention policy level
                retained_points = current_points.copy()
                
                for policy in policies:
                    cutoff_time = current_time - policy.duration_seconds
                    
                    # Separate points into keep and aggregate/remove
                    keep_points = []
                    process_points = []
                    
                    for timestamp, value in retained_points:
                        if timestamp >= cutoff_time:
                            keep_points.append((timestamp, value))
                        else:
                            process_points.append((timestamp, value))
                    
                    if process_points:
                        # Aggregate old points if aggregation is configured
                        if policy.aggregation_func != 'remove':
                            aggregated = self.optimizer.aggregate_time_series(
                                key,
                                process_points,
                                policy.aggregation_func,
                                policy.resolution_seconds
                            )
                            keep_points.extend(aggregated)
                            stats['data_points_aggregated'] += len(aggregated)
                        
                        stats['data_points_removed'] += len(process_points)
                    
                    retained_points = keep_points
                    stats['processed_policies'] += 1
                
                # Update Redis with retained data
                if len(retained_points) != len(current_points):
                    self._update_redis_data(key, retained_points, policies[0] if policies else None)
                    stats['memory_freed_bytes'] = self._estimate_memory_saved(
                        len(current_points), len(retained_points)
                    )
                
                self.last_cleanup_times[key] = current_time
                
        except Exception as e:
            logger.error(f"Failed to apply retention policies for {key}: {e}")
        
        return stats
    
    def _update_redis_data(
        self,
        key: str,
        points: List[TimeSeriesPoint],
        policy: Optional[RetentionPolicy]
    ) -> None:
        """Update Redis with processed data points."""
        try:
            # Clear existing data
            self.redis_client.delete(key)
            
            # Store processed points
            use_compression = policy.compression_enabled if policy else True
            
            for timestamp, value in reversed(points):  # Reverse to maintain order with lpush
                self.optimizer.store_time_series_point(
                    key, timestamp, value, use_compression=use_compression
                )
                
        except Exception as e:
            logger.error(f"Failed to update Redis data for {key}: {e}")
    
    def _estimate_memory_saved(self, old_count: int, new_count: int) -> int:
        """Estimate memory saved by data reduction."""
        # Rough estimate: 50 bytes per data point on average
        return (old_count - new_count) * 50


class RedisStorageOptimizer:
    """Main Redis storage optimization coordinator."""
    
    def __init__(self, redis_client, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Redis storage optimizer.
        
        Args:
            redis_client: Redis client instance
            config: Configuration dictionary
        """
        self.redis_client = redis_client
        self.config = config or {}
        
        # Initialize components
        self.compressor = DataCompressor(
            compression_level=self.config.get('compression_level', 6),
            min_size_threshold=self.config.get('min_compression_size', 100)
        )
        
        self.optimizer = TimeSeriesOptimizer(redis_client, self.compressor)
        self.retention_manager = RetentionManager(redis_client, self.optimizer)
        
        # Statistics
        self.stats = StorageStats()
        self.monitored_keys: Set[str] = set()
        
        # Background cleanup configuration
        self.auto_cleanup_enabled = self.config.get('auto_cleanup_enabled', True)
        self.cleanup_interval_seconds = self.config.get('cleanup_interval_seconds', 3600)  # 1 hour
        self.last_global_cleanup = 0.0
        
        logger.info("Redis storage optimizer initialized")
    
    def add_default_retention_policies(self) -> None:
        """Add default retention policies for BACmon data."""
        # High-frequency data (seconds): keep 1 hour raw, then 1-minute aggregates for 24 hours
        self.retention_manager.add_retention_policy(
            "*:s",
            RetentionPolicy(
                name="high_freq_raw",
                duration_seconds=3600,  # 1 hour
                resolution_seconds=1,
                aggregation_func="avg",
                compression_enabled=True
            )
        )
        
        self.retention_manager.add_retention_policy(
            "*:s",
            RetentionPolicy(
                name="high_freq_aggregated",
                duration_seconds=86400,  # 24 hours
                resolution_seconds=60,  # 1-minute aggregates
                aggregation_func="avg",
                compression_enabled=True
            )
        )
        
        # Medium-frequency data (minutes): keep 24 hours raw, then 10-minute aggregates for 7 days
        self.retention_manager.add_retention_policy(
            "*:m",
            RetentionPolicy(
                name="medium_freq_raw",
                duration_seconds=86400,  # 24 hours
                resolution_seconds=60,
                aggregation_func="avg",
                compression_enabled=True
            )
        )
        
        self.retention_manager.add_retention_policy(
            "*:m",
            RetentionPolicy(
                name="medium_freq_aggregated",
                duration_seconds=604800,  # 7 days
                resolution_seconds=600,  # 10-minute aggregates
                aggregation_func="avg",
                compression_enabled=True
            )
        )
        
        # Low-frequency data (hours): keep 7 days raw, then hourly aggregates for 30 days
        self.retention_manager.add_retention_policy(
            "*:h",
            RetentionPolicy(
                name="low_freq_raw",
                duration_seconds=604800,  # 7 days
                resolution_seconds=3600,
                aggregation_func="avg",
                compression_enabled=True
            )
        )
        
        self.retention_manager.add_retention_policy(
            "*:h",
            RetentionPolicy(
                name="low_freq_aggregated",
                duration_seconds=2592000,  # 30 days
                resolution_seconds=3600,  # Hourly aggregates
                aggregation_func="avg",
                compression_enabled=True
            )
        )
        
        # Alarm history: keep 30 days with compression
        self.retention_manager.add_retention_policy(
            "*:alarm-history",
            RetentionPolicy(
                name="alarm_history",
                duration_seconds=2592000,  # 30 days
                resolution_seconds=1,
                aggregation_func="first",  # Don't aggregate alarms, just remove old ones
                compression_enabled=True
            )
        )
    
    def optimize_key(self, key: str, force: bool = False) -> Dict[str, Any]:
        """
        Optimize storage for a specific Redis key.
        
        Args:
            key: Redis key to optimize
            force: Force optimization even if recently processed
            
        Returns:
            Optimization statistics
        """
        stats = {
            'key': key,
            'optimization_applied': False,
            'retention_stats': {},
            'compression_stats': {},
            'error': None
        }
        
        try:
            # Add to monitored keys
            self.monitored_keys.add(key)
            
            # Apply retention policies
            retention_stats = self.retention_manager.apply_retention_policies(key, force)
            stats['retention_stats'] = retention_stats
            stats['optimization_applied'] = retention_stats['processed_policies'] > 0
            
            # Update global statistics
            self.stats.data_points_stored += retention_stats['data_points_processed']
            self.stats.data_points_aggregated += retention_stats['data_points_aggregated']
            
            return stats
            
        except Exception as e:
            stats['error'] = str(e)
            logger.error(f"Failed to optimize key {key}: {e}")
            return stats
    
    def run_global_cleanup(self, force: bool = False) -> Dict[str, Any]:
        """
        Run optimization on all monitored keys.
        
        Args:
            force: Force cleanup even if recently run
            
        Returns:
            Global cleanup statistics
        """
        current_time = time.time()
        
        if not force and (current_time - self.last_global_cleanup) < self.cleanup_interval_seconds:
            return {'skipped': True, 'reason': 'Too soon since last cleanup'}
        
        stats = {
            'start_time': current_time,
            'keys_processed': 0,
            'total_retention_stats': defaultdict(int),
            'errors': []
        }
        
        try:
            logger.info(f"Starting global Redis cleanup on {len(self.monitored_keys)} keys")
            
            for key in self.monitored_keys.copy():  # Copy to avoid modification during iteration
                try:
                    result = self.optimize_key(key, force=False)
                    stats['keys_processed'] += 1
                    
                    # Aggregate retention statistics
                    retention_stats = result.get('retention_stats', {})
                    for stat_key, value in retention_stats.items():
                        stats['total_retention_stats'][stat_key] += value
                    
                    if result.get('error'):
                        stats['errors'].append({'key': key, 'error': result['error']})
                        
                except Exception as e:
                    stats['errors'].append({'key': key, 'error': str(e)})
                    logger.error(f"Failed to optimize key {key} during global cleanup: {e}")
            
            self.last_global_cleanup = current_time
            stats['duration_seconds'] = time.time() - current_time
            
            logger.info(f"Global cleanup completed: {stats['keys_processed']} keys processed")
            return stats
            
        except Exception as e:
            logger.error(f"Global cleanup failed: {e}")
            stats['errors'].append({'global_error': str(e)})
            return stats
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive storage optimization statistics."""
        try:
            # Update basic stats
            self.stats.total_keys = len(self.monitored_keys)
            
            # Get compression stats
            compression_stats = self.compressor.stats.copy()
            
            # Calculate compression ratio
            if compression_stats['compressed'] > 0:
                self.stats.compression_ratio = (
                    compression_stats['bytes_saved'] / 
                    (compression_stats['bytes_saved'] + sum(compression_stats.values()))
                )
            
            return {
                'storage_stats': {
                    'total_keys': self.stats.total_keys,
                    'compressed_keys': compression_stats['compressed'],
                    'compression_ratio': f"{self.stats.compression_ratio:.2%}",
                    'data_points_stored': self.stats.data_points_stored,
                    'data_points_aggregated': self.stats.data_points_aggregated,
                    'last_cleanup_time': datetime.fromtimestamp(self.last_global_cleanup).isoformat()
                },
                'compression_stats': compression_stats,
                'monitored_keys': list(self.monitored_keys),
                'retention_policies': {
                    pattern: [
                        {
                            'name': policy.name,
                            'duration_hours': policy.duration_seconds / 3600,
                            'resolution_seconds': policy.resolution_seconds,
                            'aggregation_func': policy.aggregation_func,
                            'compression_enabled': policy.compression_enabled
                        }
                        for policy in policies
                    ]
                    for pattern, policies in self.retention_manager.policies.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {e}")
            return {'error': str(e)} 