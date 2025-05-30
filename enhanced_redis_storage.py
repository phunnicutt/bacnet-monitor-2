#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Enhanced Redis Storage Integration for BACmon

This module provides enhanced versions of CountInterval and SampleRateTask
that integrate with the Redis optimization features for better performance
and storage efficiency while maintaining backward compatibility.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union

try:
    from redis_optimizer import RedisStorageOptimizer, RetentionPolicy
except ImportError:
    # Fallback if redis_optimizer is not available
    RedisStorageOptimizer = None
    RetentionPolicy = None

logger = logging.getLogger(__name__)


class OptimizedCountInterval:
    """
    Enhanced CountInterval that uses Redis optimization features.
    
    Maintains backward compatibility with the original CountInterval
    while adding compression, retention policies, and performance optimizations.
    """
    
    def __init__(
        self,
        label: str,
        modulus: int,
        maxLen: int,
        redis_client=None,
        optimizer: Optional['RedisStorageOptimizer'] = None,
        enable_optimization: bool = True
    ):
        """
        Initialize OptimizedCountInterval.
        
        Args:
            label: Label for the interval
            modulus: Interval modulus in seconds
            maxLen: Maximum length of data to retain
            redis_client: Redis client instance
            optimizer: Redis storage optimizer instance
            enable_optimization: Whether to enable optimization features
        """
        self.label = label
        self.modulus = modulus
        self.maxLen = maxLen
        self.lastInterval = 0
        self.enable_optimization = enable_optimization and RedisStorageOptimizer is not None
        
        # Redis integration
        self.redis_client = redis_client
        self.optimizer = optimizer
        
        # Setup optimization if available and enabled
        if self.enable_optimization and self.optimizer:
            self._setup_optimization()
        
        logger.debug(f"OptimizedCountInterval initialized: {label}, optimization={'enabled' if self.enable_optimization else 'disabled'}")
    
    def _setup_optimization(self) -> None:
        """Setup Redis optimization features for this interval."""
        if not self.optimizer:
            return
        
        try:
            # Determine retention policy based on modulus
            if self.modulus <= 1:
                # High frequency (seconds)
                key_pattern = f"{self.label}:s"
                retention_policy = RetentionPolicy(
                    name=f"{self.label}_high_freq",
                    duration_seconds=3600,  # 1 hour
                    resolution_seconds=self.modulus,
                    aggregation_func="avg",
                    compression_enabled=True
                )
            elif self.modulus <= 60:
                # Medium frequency (minutes)
                key_pattern = f"{self.label}:m"
                retention_policy = RetentionPolicy(
                    name=f"{self.label}_medium_freq",
                    duration_seconds=86400,  # 24 hours
                    resolution_seconds=self.modulus,
                    aggregation_func="avg",
                    compression_enabled=True
                )
            else:
                # Low frequency (hours)
                key_pattern = f"{self.label}:h"
                retention_policy = RetentionPolicy(
                    name=f"{self.label}_low_freq",
                    duration_seconds=604800,  # 7 days
                    resolution_seconds=self.modulus,
                    aggregation_func="avg",
                    compression_enabled=True
                )
            
            # Add the retention policy
            self.optimizer.retention_manager.add_retention_policy(key_pattern, retention_policy)
            
        except Exception as e:
            logger.warning(f"Failed to setup optimization for {self.label}: {e}")
            self.enable_optimization = False
    
    def count(
        self,
        r,  # Redis client
        bucket: int,
        count: int = 1,
        packet_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Count an event and store it in Redis with optimization.
        
        Args:
            r: Redis client instance
            bucket: Time bucket for the count
            count: Count value to add
            packet_info: Optional packet information for enhanced metrics
        """
        # Calculate interval
        lasti = int(bucket // self.modulus) * self.modulus
        
        # Backward compatibility: use original storage method if optimization disabled
        if not self.enable_optimization or not self.optimizer:
            self._count_legacy(r, lasti, count)
            return
        
        # Enhanced storage with optimization
        try:
            current_time = time.time()
            key = f"{self.label}:{self._get_frequency_suffix()}"
            
            # Store using optimized method
            self.optimizer.optimizer.store_time_series_point(
                key=key,
                timestamp=lasti,
                value=count,
                max_points=self.maxLen,
                use_compression=True
            )
            
            # Add to monitored keys for optimization
            self.optimizer.monitored_keys.add(key)
            
            # Trigger optimization if needed (not too frequently)
            if current_time - getattr(self, '_last_optimization', 0) > 300:  # 5 minutes
                self.optimizer.optimize_key(key, force=False)
                self._last_optimization = current_time
            
            self.lastInterval = lasti
            
        except Exception as e:
            logger.warning(f"Optimization failed for {self.label}, falling back to legacy: {e}")
            self._count_legacy(r, lasti, count)
    
    def _count_legacy(self, r, lasti: int, count: int) -> None:
        """Legacy count method for backward compatibility."""
        key = self.label
        
        # Original BACmon storage logic
        if lasti != self.lastInterval:
            xkey = key + ":s"
            xcount = count
            r.lpush(xkey, str([self.lastInterval, xcount]))
            r.ltrim(xkey, 0, self.maxLen - 1)
            self.lastInterval = lasti
        
        # Store current count
        r.lpush(key, str([lasti, count]))
        r.ltrim(key, 0, self.maxLen - 1)
    
    def _get_frequency_suffix(self) -> str:
        """Get frequency suffix based on modulus."""
        if self.modulus <= 1:
            return "s"  # seconds
        elif self.modulus <= 60:
            return "m"  # minutes
        else:
            return "h"  # hours
    
    def get_data(self, r, limit: int = -1) -> List[List[Union[int, float]]]:
        """
        Get stored data with optimization support.
        
        Args:
            r: Redis client instance
            limit: Limit on number of data points to return
            
        Returns:
            List of [timestamp, value] pairs
        """
        if not self.enable_optimization or not self.optimizer:
            return self._get_data_legacy(r, limit)
        
        try:
            key = f"{self.label}:{self._get_frequency_suffix()}"
            
            # Get data using optimizer
            end_index = limit if limit > 0 else -1
            points = self.optimizer.optimizer.get_time_series_range(
                key=key,
                start_index=0,
                end_index=end_index
            )
            
            # Convert to expected format
            return [[int(timestamp), value] for timestamp, value in points]
            
        except Exception as e:
            logger.warning(f"Optimized data retrieval failed for {self.label}, falling back: {e}")
            return self._get_data_legacy(r, limit)
    
    def _get_data_legacy(self, r, limit: int = -1) -> List[List[Union[int, float]]]:
        """Legacy data retrieval method."""
        try:
            key = self.label
            end_index = limit if limit > 0 else -1
            raw_data = r.lrange(key, 0, end_index)
            
            data = []
            for item in raw_data:
                try:
                    item_str = item.decode('utf-8') if isinstance(item, bytes) else str(item)
                    timestamp, value = eval(item_str)  # Note: eval used for backward compatibility
                    data.append([timestamp, value])
                except (ValueError, SyntaxError):
                    continue
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to retrieve data for {self.label}: {e}")
            return []


class OptimizedSampleRateTask:
    """
    Enhanced SampleRateTask that uses Redis optimization features.
    
    Maintains backward compatibility while adding advanced monitoring
    and storage optimization capabilities.
    """
    
    def __init__(
        self,
        key: str,
        interval: int,
        max_value: int,
        duration: int,
        redis_client=None,
        optimizer: Optional['RedisStorageOptimizer'] = None,
        enable_optimization: bool = True
    ):
        """
        Initialize OptimizedSampleRateTask.
        
        Args:
            key: Redis key for rate monitoring
            interval: Sample interval in seconds
            max_value: Maximum allowed value
            duration: Duration threshold in seconds
            redis_client: Redis client instance
            optimizer: Redis storage optimizer instance
            enable_optimization: Whether to enable optimization features
        """
        self.key = key
        self.interval = interval
        self.max_value = max_value
        self.duration = duration
        self.redis_client = redis_client
        self.optimizer = optimizer
        self.enable_optimization = enable_optimization and RedisStorageOptimizer is not None
        
        # State tracking
        self.alarmTime = 0
        self.consecutiveAlarms = 0
        
        # Setup optimization
        if self.enable_optimization and self.optimizer:
            self._setup_optimization()
        
        logger.debug(f"OptimizedSampleRateTask initialized: {key}, optimization={'enabled' if self.enable_optimization else 'disabled'}")
    
    def _setup_optimization(self) -> None:
        """Setup Redis optimization for rate monitoring data."""
        if not self.optimizer:
            return
        
        try:
            # Add retention policies for rate monitoring data
            rate_policy = RetentionPolicy(
                name=f"{self.key}_rate_monitoring",
                duration_seconds=86400,  # 24 hours for rate data
                resolution_seconds=self.interval,
                aggregation_func="avg",
                compression_enabled=True
            )
            
            alarm_policy = RetentionPolicy(
                name=f"{self.key}_alarm_history",
                duration_seconds=2592000,  # 30 days for alarm history
                resolution_seconds=1,
                aggregation_func="first",  # Don't aggregate alarms
                compression_enabled=True
            )
            
            self.optimizer.retention_manager.add_retention_policy(self.key, rate_policy)
            self.optimizer.retention_manager.add_retention_policy(f"{self.key}:alarm-history", alarm_policy)
            
        except Exception as e:
            logger.warning(f"Failed to setup optimization for {self.key}: {e}")
            self.enable_optimization = False
    
    def sample(self, r) -> Optional[bool]:
        """
        Sample rate data and check for threshold violations.
        
        Args:
            r: Redis client instance
            
        Returns:
            True if alarm triggered, False if cleared, None if no change
        """
        try:
            # Get recent samples for analysis
            if self.enable_optimization and self.optimizer:
                points = self.optimizer.optimizer.get_time_series_range(
                    key=self.key,
                    start_index=0,
                    end_index=25  # Analyze last 25 samples
                )
                samples = [value for _, value in points]
            else:
                # Legacy method
                raw_samples = r.lrange(self.key, 0, 25)
                samples = []
                for sample in raw_samples:
                    try:
                        sample_str = sample.decode('utf-8') if isinstance(sample, bytes) else str(sample)
                        _, value = eval(sample_str)
                        samples.append(value)
                    except (ValueError, SyntaxError):
                        continue
            
            if not samples:
                return None
            
            # Check for threshold violation
            recent_value = samples[0] if samples else 0
            alarm_triggered = False
            
            if recent_value > self.max_value:
                if self.alarmTime == 0:
                    self.alarmTime = time.time()
                
                # Check if alarm duration exceeded
                if time.time() - self.alarmTime >= self.duration:
                    alarm_triggered = True
                    self.consecutiveAlarms += 1
                    
                    # Store alarm in history
                    self._store_alarm_event(r, recent_value)
            else:
                # Clear alarm state
                if self.alarmTime > 0:
                    self.alarmTime = 0
                    self.consecutiveAlarms = 0
                    return False  # Alarm cleared
            
            return alarm_triggered if alarm_triggered else None
            
        except Exception as e:
            logger.error(f"Failed to sample rate for {self.key}: {e}")
            return None
    
    def _store_alarm_event(self, r, value: Union[int, float]) -> None:
        """Store alarm event in history."""
        try:
            alarm_data = [int(time.time()), value, self.consecutiveAlarms]
            alarm_key = f"{self.key}:alarm-history"
            
            if self.enable_optimization and self.optimizer:
                # Store using optimizer
                self.optimizer.optimizer.store_time_series_point(
                    key=alarm_key,
                    timestamp=time.time(),
                    value=alarm_data,
                    max_points=1000,
                    use_compression=True
                )
                self.optimizer.monitored_keys.add(alarm_key)
            else:
                # Legacy storage
                r.lpush(alarm_key, str(alarm_data))
                r.ltrim(alarm_key, 0, 999)  # Keep last 1000 alarms
                
        except Exception as e:
            logger.error(f"Failed to store alarm event for {self.key}: {e}")
    
    def get_alarm_history(self, r, limit: int = 100) -> List[List[Union[int, float]]]:
        """
        Get alarm history with optimization support.
        
        Args:
            r: Redis client instance
            limit: Maximum number of alarm events to return
            
        Returns:
            List of alarm events
        """
        try:
            alarm_key = f"{self.key}:alarm-history"
            
            if self.enable_optimization and self.optimizer:
                points = self.optimizer.optimizer.get_time_series_range(
                    key=alarm_key,
                    start_index=0,
                    end_index=limit
                )
                return [[int(timestamp), value] for timestamp, value in points]
            else:
                # Legacy method
                raw_data = r.lrange(alarm_key, 0, limit)
                history = []
                for item in raw_data:
                    try:
                        item_str = item.decode('utf-8') if isinstance(item, bytes) else str(item)
                        event_data = eval(item_str)
                        history.append(event_data)
                    except (ValueError, SyntaxError):
                        continue
                return history
                
        except Exception as e:
            logger.error(f"Failed to get alarm history for {self.key}: {e}")
            return []


def create_optimized_storage_manager(redis_client, config: Optional[Dict[str, Any]] = None) -> Optional['RedisStorageOptimizer']:
    """
    Create an optimized storage manager if redis_optimizer is available.
    
    Args:
        redis_client: Redis client instance
        config: Configuration for the optimizer
        
    Returns:
        RedisStorageOptimizer instance or None if not available
    """
    if RedisStorageOptimizer is None:
        logger.info("Redis optimization not available, using legacy storage")
        return None
    
    try:
        optimizer = RedisStorageOptimizer(redis_client, config)
        optimizer.add_default_retention_policies()
        logger.info("Redis storage optimization enabled")
        return optimizer
    except Exception as e:
        logger.error(f"Failed to create Redis storage optimizer: {e}")
        return None


def get_storage_factory(redis_client, config: Optional[Dict[str, Any]] = None):
    """
    Get storage factory functions for creating optimized or legacy storage objects.
    
    Args:
        redis_client: Redis client instance
        config: Configuration dictionary
        
    Returns:
        Dictionary with factory functions
    """
    optimizer = create_optimized_storage_manager(redis_client, config)
    optimization_enabled = optimizer is not None
    
    def create_count_interval(label: str, modulus: int, maxLen: int):
        """Create an optimized or legacy CountInterval."""
        return OptimizedCountInterval(
            label=label,
            modulus=modulus,
            maxLen=maxLen,
            redis_client=redis_client,
            optimizer=optimizer,
            enable_optimization=optimization_enabled
        )
    
    def create_sample_rate_task(key: str, interval: int, max_value: int, duration: int):
        """Create an optimized or legacy SampleRateTask."""
        return OptimizedSampleRateTask(
            key=key,
            interval=interval,
            max_value=max_value,
            duration=duration,
            redis_client=redis_client,
            optimizer=optimizer,
            enable_optimization=optimization_enabled
        )
    
    return {
        'optimizer': optimizer,
        'optimization_enabled': optimization_enabled,
        'create_count_interval': create_count_interval,
        'create_sample_rate_task': create_sample_rate_task,
        'get_statistics': lambda: optimizer.get_storage_statistics() if optimizer else {},
        'run_cleanup': lambda force=False: optimizer.run_global_cleanup(force) if optimizer else {}
    } 