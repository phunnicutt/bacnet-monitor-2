#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BACmon Enhanced Rate Monitoring Module

This module extends the original CountInterval and SampleRateTask classes
to support additional metrics beyond simple packet counts. It integrates
with the metrics.py module to provide a comprehensive metric collection
and monitoring system.

The enhanced system supports:
1. Packet sizes (average, minimum, maximum)
2. Protocol distributions (percentage of different protocols over time)
3. Error rates (ratio of error packets to total traffic)
4. Response times (for relevant protocol exchanges)
5. Connection patterns (new connections per second, connection durations)
6. Service-specific metrics based on packet content analysis
"""

import logging
import time
from typing import Dict, List, Tuple, Any, Optional, Set, Union, Type, cast
from collections import defaultdict

# Import original classes to extend
from BACmon import CountInterval as OriginalCountInterval
from BACmon import SampleRateTask as OriginalSampleRateTask
from BACmon import RecurringTask, Logging

# Import metrics module
import metrics
from metrics import MetricType, MetricProcessor, MetricManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
_debug = False
r = None  # Redis client (set during initialization)

def set_redis_client(redis_client):
    """Set the Redis client for the module."""
    global r
    r = redis_client
    
    # Also set for metrics module
    metrics_manager = metrics.get_metric_manager(redis_client)

class EnhancedCountInterval(OriginalCountInterval):
    """
    Extended version of CountInterval that supports multiple metric types.
    
    This class extends the original CountInterval to process and store
    additional metrics beyond simple packet counts.
    """
    
    def __init__(self, key, seconds, minutes, hours):
        """
        Initialize the enhanced count interval.
        
        Args:
            key: Redis key for the interval
            seconds: Number of seconds in the interval
            minutes: Number of minutes in the interval
            hours: Number of hours in the interval
        """
        super().__init__(key, seconds, minutes, hours)
        self.metrics_manager = metrics.get_metric_manager()
        
        # Register metric processors for this key
        self.metrics_manager.add_processor(key, metrics.CountMetricProcessor())
        self.metrics_manager.add_processor(key, metrics.SizeMetricProcessor())
        self.metrics_manager.add_processor(key, metrics.ProtocolMetricProcessor())
        self.metrics_manager.add_processor(key, metrics.ErrorRateMetricProcessor())
        
        # For specific message types, add response time and connection processors
        if "request" in key.lower() or "ack" in key.lower():
            self.metrics_manager.add_processor(key, metrics.ResponseTimeMetricProcessor())
        
        if "connect" in key.lower() or "bind" in key.lower():
            self.metrics_manager.add_processor(key, metrics.ConnectionMetricProcessor())
    
    def Count(self, msg, packet_info=None):
        """
        Count a message and process extended metrics if packet info is provided.
        
        Args:
            msg: Message key to count
            packet_info: Optional packet information for extended metrics
        """
        # First call the original implementation to maintain basic counting
        super().Count(msg)
        
        # Process extended metrics if packet info is provided
        if packet_info is not None:
            self.metrics_manager.process_packet(msg, packet_info)
    
    def Sample(self, interval):
        """
        Sample the metrics for a specific interval.
        
        Args:
            interval: Current sampling interval
        """
        # Call the original implementation
        super().Sample(interval)
        
        # Store extended metrics
        if interval == self.seconds:
            self.metrics_manager.store_metrics(interval, 's')
        elif interval == self.minutes:
            self.metrics_manager.store_metrics(interval, 'm')
        elif interval == self.hours:
            self.metrics_manager.store_metrics(interval, 'h')
            
            # Reset metrics after hourly sampling
            self.metrics_manager.reset_metrics()


class EnhancedSampleRateTask(OriginalSampleRateTask):
    """
    Extended version of SampleRateTask that supports multiple metric types.
    
    This class extends the original SampleRateTask to analyze and alert on
    multiple types of metrics beyond simple packet counts.
    """
    
    def __init__(self, key, interval, maxValue, duration, metric_type=MetricType.COUNT, 
                 threshold_config=None, alert_config=None):
        """
        Initialize the enhanced sample rate task.
        
        Args:
            key: Redis key for monitoring
            interval: Sampling interval in seconds
            maxValue: Maximum threshold value
            duration: Number of intervals for trend detection
            metric_type: Type of metric to monitor (default: COUNT)
            threshold_config: Configuration for thresholds on different metrics
            alert_config: Configuration for alerting
        """
        super().__init__(key, interval, maxValue, duration)
        
        # Store the metric type to monitor
        self.metric_type = metric_type
        
        # Set threshold configuration with defaults
        self.threshold_config = threshold_config or {
            MetricType.COUNT: maxValue,
            MetricType.SIZE: {
                "avg": maxValue,
                "max": maxValue * 1.5
            },
            MetricType.PROTOCOL: {
                "unknown": 10.0  # Percentage threshold for unknown protocols
            },
            MetricType.ERROR_RATE: 5.0,  # Percentage threshold for errors
            MetricType.RESPONSE_TIME: {
                "avg": 500,  # ms
                "p95": 1000  # ms
            },
            MetricType.CONNECTION: {
                "new_connections": maxValue,
                "active_connections": maxValue * 2
            }
        }
        
        # Set alert configuration
        self.alert_config = alert_config or {
            "enable": True,
            "levels": {
                "warning": 0.8,  # 80% of threshold
                "alert": 1.0,    # 100% of threshold
                "critical": 1.5  # 150% of threshold
            }
        }
        
        # Initialize alert manager reference
        try:
            import alert_manager
            self.alert_manager = alert_manager.get_alert_manager(r)
        except ImportError:
            logger.warning("Alert manager not available. Alerts will not be generated.")
            self.alert_manager = None
    
    def yield_metric_samples(self, st, et, metric_type=None):
        """
        Yield samples for a specific metric type within a time range.
        
        Args:
            st: Start time
            et: End time
            metric_type: Type of metric to retrieve (default: use self.metric_type)
            
        Yields:
            Tuples of [timestamp, value] for the specified metric
        """
        if _debug: self._debug("yield_metric_samples %r %r %r", st, et, metric_type)
        
        # Use default metric type if not specified
        metric_type = metric_type or self.metric_type
        
        # Create Redis key
        redis_key = f"{self.key}:{metric_type}:s"  # Use seconds samples
        
        # Get samples from Redis
        samples = r.lrange(redis_key, 0, 1000)
        
        # Process samples
        if samples:
            # Reverse and parse the samples
            samples.reverse()
            samples = [eval(s) for s in samples]
            
            # Yield samples within the requested time range
            nt = st
            for t, v in samples:
                # Skip samples too far in the past
                if t < nt:
                    continue
                
                # Fill in missing samples
                while (nt < t) and (nt <= et):
                    # For counts, use 0. For other metrics, use None
                    if metric_type == MetricType.COUNT:
                        yield [nt, 0]
                    else:
                        yield [nt, None]
                    nt += self.interval
                
                # Stop if we've gone past the end time
                if nt > et:
                    break
                
                # Yield the sample
                yield [nt, v]
                nt += self.interval
    
    def check_metric_threshold(self, value):
        """
        Check if a metric value exceeds its threshold.
        
        Args:
            value: The metric value to check
            
        Returns:
            Tuple of (exceeded, ratio, details) where:
            - exceeded: Boolean indicating if threshold was exceeded
            - ratio: Float ratio of value to threshold (1.0 = exactly at threshold)
            - details: Dictionary with details about the threshold check
        """
        # Get threshold for this metric type
        threshold = self.threshold_config.get(self.metric_type)
        
        # Default return values
        exceeded = False
        ratio = 0.0
        details = {"value": value, "threshold": threshold}
        
        # Check based on metric type
        if self.metric_type == MetricType.COUNT:
            # Simple numeric comparison
            if value > threshold:
                exceeded = True
                ratio = value / threshold
                
        elif self.metric_type == MetricType.SIZE:
            # Check size metrics
            if isinstance(value, dict) and isinstance(threshold, dict):
                for key in ["avg", "max"]:
                    if key in value and key in threshold and value[key] is not None:
                        if value[key] > threshold[key]:
                            exceeded = True
                            ratio = max(ratio, value[key] / threshold[key])
                            details[f"{key}_exceeded"] = True
                            
        elif self.metric_type == MetricType.PROTOCOL:
            # Check protocol distribution
            if isinstance(value, dict) and "protocols" in value:
                # Check percentage of unknown protocols
                unknown_pct = 0
                if "unknown" in value["protocols"]:
                    unknown_pct = value["protocols"]["unknown"].get("percentage", 0)
                
                if unknown_pct > threshold.get("unknown", 100):
                    exceeded = True
                    ratio = unknown_pct / threshold["unknown"]
                    details["unknown_percentage"] = unknown_pct
                    
        elif self.metric_type == MetricType.ERROR_RATE:
            # Check error rate
            if isinstance(value, dict) and "rate" in value:
                if value["rate"] > threshold:
                    exceeded = True
                    ratio = value["rate"] / threshold
                    details["error_rate"] = value["rate"]
                    
        elif self.metric_type == MetricType.RESPONSE_TIME:
            # Check response time metrics
            if isinstance(value, dict) and isinstance(threshold, dict):
                for key in ["avg", "p95"]:
                    if key in value and key in threshold and value[key] is not None:
                        if value[key] > threshold[key]:
                            exceeded = True
                            ratio = max(ratio, value[key] / threshold[key])
                            details[f"{key}_exceeded"] = True
                            
        elif self.metric_type == MetricType.CONNECTION:
            # Check connection metrics
            if isinstance(value, dict) and isinstance(threshold, dict):
                for key in ["new_connections", "active_connections"]:
                    if key in value and key in threshold:
                        if value[key] > threshold[key]:
                            exceeded = True
                            ratio = max(ratio, value[key] / threshold[key])
                            details[f"{key}_exceeded"] = True
        
        return exceeded, ratio, details
    
    def generate_alert(self, ratio, details):
        """
        Generate an alert based on threshold ratio.
        
        Args:
            ratio: Ratio of value to threshold
            details: Dictionary with details about the threshold check
        """
        if not self.alert_manager or not self.alert_config.get("enable", True):
            return
            
        # Determine alert level
        levels = self.alert_config.get("levels", {})
        
        if ratio >= levels.get("critical", 1.5):
            level = "critical"
        elif ratio >= levels.get("alert", 1.0):
            level = "alert"
        elif ratio >= levels.get("warning", 0.8):
            level = "warning"
        else:
            # No alert needed
            return
            
        # Create alert message
        message = f"Metric threshold exceeded for {self.key} ({self.metric_type})"
        
        # Generate the alert
        self.alert_manager.create_alert(
            key=f"{self.key}:{self.metric_type}",
            entity=self.key,
            message=message,
            level=level,
            details=details
        )
    
    def process_task(self):
        """Check values against thresholds and generate alerts if needed."""
        if _debug: self._debug("ProcessTask")
        
        # Get current time aligned to interval
        now = int(time.time())
        now = now - (now % self.interval)
        
        # Process samples
        tick = False
        for t, v in self.yield_metric_samples(self.nextCheck, now):
            tick = True
            
            # Check threshold
            if v is not None:
                exceeded, ratio, details = self.check_metric_threshold(v)
                
                # Handle exceeded threshold
                if exceeded:
                    if not self.alarm:
                        self.setCount += 1
                        if self.setCount >= self.duration:
                            if _debug: self._debug("    - in alarm")
                            self.alarm = True
                            self.alarmTime = t
                            
                            # Set alarm in Redis
                            r.set(f"{self.key}:{self.metric_type}:alarm", t)
                            
                            # Generate alert
                            self.generate_alert(ratio, details)
                    else:
                        # Already in alarm, update if ratio increased significantly
                        if ratio > 1.5 and self.alert_manager and self.alert_config.get("enable", True):
                            # Generate escalated alert
                            self.generate_alert(ratio, details)
                else:
                    # Check if we should clear the alarm
                    if self.alarm:
                        self.resetCount += 1
                        if self.resetCount >= self.duration:
                            if _debug: self._debug("    - cleared")
                            
                            # Clear alarm in Redis
                            r.delete(f"{self.key}:{self.metric_type}:alarm")
                            
                            # Log alarm history
                            r.lpush(f"{self.key}:{self.metric_type}:alarm-history", 
                                    str([self.alarmTime, t]))
                            
                            # Reset alarm state
                            self.alarm = False
                            self.setCount = 0
                            self.alarmTime = None
                            
                            # Generate resolved alert
                            if self.alert_manager and self.alert_config.get("enable", True):
                                self.alert_manager.resolve_alert(
                                    key=f"{self.key}:{self.metric_type}",
                                    message=f"Metric threshold returned to normal for {self.key} ({self.metric_type})"
                                )
                    else:
                        self.resetCount = 0
        
        # Update next check time
        if tick:
            self.nextCheck = t + self.interval
        else:
            self.nextCheck = now


def create_enhanced_rate_tasks(config_items):
    """
    Create enhanced rate monitoring tasks from configuration.
    
    Args:
        config_items: List of configuration tuples (key, interval, max_value, duration)
        
    Returns:
        List of EnhancedSampleRateTask instances
    """
    tasks = []
    
    for key, interval, max_value, duration in config_items:
        # Create basic count task
        tasks.append(EnhancedSampleRateTask(key, interval, max_value, duration))
        
        # Create size metric task
        tasks.append(EnhancedSampleRateTask(
            key, interval, max_value, duration,
            metric_type=MetricType.SIZE
        ))
        
        # For specific message types, add specialized tasks
        if "error" in key.lower():
            tasks.append(EnhancedSampleRateTask(
                key, interval, 5.0, duration,  # 5% error rate threshold
                metric_type=MetricType.ERROR_RATE
            ))
            
        if "request" in key.lower() or "ack" in key.lower():
            tasks.append(EnhancedSampleRateTask(
                key, interval, 500, duration,  # 500ms response time threshold
                metric_type=MetricType.RESPONSE_TIME
            ))
            
        if "connect" in key.lower() or "bind" in key.lower():
            tasks.append(EnhancedSampleRateTask(
                key, interval, max_value, duration,
                metric_type=MetricType.CONNECTION
            ))
        # Process samples (similar to original but handling JSON serialized data)
        samples.reverse()
        processed_samples = []
        
        for sample in samples:
            try:
                # Parse the sample
                sample_data = eval(sample)
                timestamp = sample_data[0]
                
                # For complex metrics (like dictionaries), we need to extract a specific value
                # based on the metric type
                value = self._extract_value_from_sample(sample_data[1])
                
                processed_samples.append((timestamp, value))
            except Exception as e:
                if _debug: EnhancedSampleRateTask._debug("Error processing sample: %r", e)
                continue
                
        # Sort by timestamp
        processed_samples.sort(key=lambda x: x[0])
        
        # Yield samples in the requested range (similar to original)
        nt = st
        for t, v in processed_samples:
            # Sample might be too far in the past
            if t < nt:
                continue
                
            # Might be some missing values, assume zero
            while (nt < t) and (nt <= et):
                yield [nt, 0]
                nt += self.interval
                
            # Don't present more samples than requested
            if nt > et:
                break
                
            # Yield the sample
            yield [nt, v]
            nt += self.interval
            
    def _extract_value_from_sample(self, sample_data):
        """
        Extract the appropriate value from a sample based on metric type.
        
        Args:
            sample_data: Sample data (could be a simple value or JSON string)
            
        Returns:
            Extracted value for threshold comparison
        """
        # If it's just a number, return it directly
        if isinstance(sample_data, (int, float)):
            return sample_data
            
        # If it's a string, try to parse it as JSON
        if isinstance(sample_data, str):
            try:
                sample_data = metrics.create_metric_processor(self.metric_type).deserialize(sample_data)
            except Exception:
                # If parsing fails, return the string as-is
                return sample_data
                
        # Extract based on metric type
        if self.metric_type == MetricType.SIZE:
            # Use average size by default
            return sample_data.get("avg", 0) if isinstance(sample_data, dict) else sample_data
            
        elif self.metric_type == MetricType.PROTOCOL:
            # Use total count by default
            return sample_data.get("total", 0) if isinstance(sample_data, dict) else sample_data
            
        elif self.metric_type == MetricType.ERROR_RATE:
            # Use error rate by default
            return sample_data.get("rate", 0) if isinstance(sample_data, dict) else sample_data
            
        elif self.metric_type == MetricType.RESPONSE_TIME:
            # Use average response time by default
            return sample_data.get("avg", 0) if isinstance(sample_data, dict) else sample_data
            
        elif self.metric_type == MetricType.CONNECTION:
            # Use new connections by default
            return sample_data.get("new", 0) if isinstance(sample_data, dict) else sample_data
            
        elif self.metric_type == MetricType.SERVICE:
            # Service metrics are too varied, just return the raw data
            return sample_data
            
        # Default fallback
        return sample_data
        
    def set_mode(self, t, v):
        """
        Check if the alarm should be set based on the metric type.
        
        Args:
            t: Timestamp
            v: Value
        """
        if _debug: EnhancedSampleRateTask._debug("set_mode %r %r", t, v)
        
        # Get the appropriate threshold based on metric type
        threshold = self._get_threshold_for_metric()
        
        # Check if value exceeds threshold
        exceeded = False
        
        if isinstance(threshold, dict):
            # For complex thresholds, check the appropriate value
            if self.metric_type == MetricType.SIZE:
                if isinstance(v, dict):
                    exceeded = (v.get("avg", 0) > threshold.get("avg", float('inf')) or
                                v.get("max", 0) > threshold.get("max", float('inf')))
                else:
                    exceeded = v > threshold.get("avg", float('inf'))
            
            elif self.metric_type == MetricType.RESPONSE_TIME:
                if isinstance(v, dict):
                    exceeded = (v.get("avg", 0) > threshold.get("avg", float('inf')) or
                                v.get("p95", 0) > threshold.get("p95", float('inf')))
                else:
                    exceeded = v > threshold.get("avg", float('inf'))
                    
            elif self.metric_type == MetricType.CONNECTION:
                if isinstance(v, dict):
                    exceeded = (v.get("new", 0) > threshold.get("new", float('inf')) or
                                v.get("active", 0) > threshold.get("active", float('inf')))
                else:
                    exceeded = v > threshold.get("new", float('inf'))
            else:
                # Default comparison for dictionary thresholds
                exceeded = any(v.get(k, 0) > val for k, val in threshold.items() if k in v)
        else:
            # Simple threshold comparison
            exceeded = v > threshold
            
        # Continue with alarm handling (similar to original)
        if not exceeded:
            if _debug: EnhancedSampleRateTask._debug("    - could be")
            self.resetCount += 1
            if (self.resetCount >= self.duration):
                if _debug: EnhancedSampleRateTask._debug("    - cleared")
                # Clear the alarm
                self.alarm = False
                self.alarmTime = None
                r.delete(self.key + ':alarm')
                # Send a text message
                self._send_notification(t, v, True)
        else:
            self.resetCount = 0
            if _debug: EnhancedSampleRateTask._debug("    - never mind")
            
    def reset_mode(self, t, v):
        """
        Check if the alarm should be reset based on the metric type.
        
        Args:
            t: Timestamp
            v: Value
        """
        if _debug: EnhancedSampleRateTask._debug("reset_mode %r %r", t, v)
        
        # Get the appropriate threshold based on metric type
        threshold = self._get_threshold_for_metric()
        
        # Check if value exceeds threshold
        exceeded = False
        
        if isinstance(threshold, dict):
            # For complex thresholds, check the appropriate value
            if self.metric_type == MetricType.SIZE:
                if isinstance(v, dict):
                    exceeded = (v.get("avg", 0) > threshold.get("avg", float('inf')) or
                                v.get("max", 0) > threshold.get("max", float('inf')))
                else:
                    exceeded = v > threshold.get("avg", float('inf'))
            
            elif self.metric_type == MetricType.RESPONSE_TIME:
                if isinstance(v, dict):
                    exceeded = (v.get("avg", 0) > threshold.get("avg", float('inf')) or
                                v.get("p95", 0) > threshold.get("p95", float('inf')))
                else:
                    exceeded = v > threshold.get("avg", float('inf'))
                    
            elif self.metric_type == MetricType.CONNECTION:
                if isinstance(v, dict):
                    exceeded = (v.get("new", 0) > threshold.get("new", float('inf')) or
                                v.get("active", 0) > threshold.get("active", float('inf')))
                else:
                    exceeded = v > threshold.get("new", float('inf'))
            else:
                # Default comparison for dictionary thresholds
                exceeded = any(v.get(k, 0) > val for k, val in threshold.items() if k in v)
        else:
            # Simple threshold comparison
            exceeded = v > threshold
            
        # Continue with alarm handling (similar to original)
        if exceeded:
            if _debug: EnhancedSampleRateTask._debug("    - could be")
            self.setCount += 1
            if (self.setCount >= self.duration):
                if _debug: EnhancedSampleRateTask._debug("    - in alarm")
                # Set the alarm
                self.alarm = True
                self.alarmTime = t
                r.set(self.key + ':alarm', str(t))
                # Send a text message
                self._send_notification(t, v, False)
        else:
            self.setCount = 0
            if _debug: EnhancedSampleRateTask._debug("    - never mind")
            
    def _get_threshold_for_metric(self):
        """
        Get the appropriate threshold for the current metric type.
        
        Returns:
            Threshold value or dictionary
        """
        if self.metric_type in self.thresholds:
            return self.thresholds[self.metric_type]
        else:
            # Default to original threshold
            return self.maxValue
            
    def _send_notification(self, t, v, cleared=False):
        """
        Send a notification for the alarm.
        
        Args:
            t: Timestamp
            v: Value
            cleared: Whether the alarm was cleared
        """
        try:
            if not cleared:
                # Format the message based on metric type
                if self.metric_type == MetricType.COUNT:
                    msg = f"ALARM: {self.key} count exceeded threshold {self.maxValue} with value {v}"
                elif self.metric_type == MetricType.SIZE:
                    size_details = f"avg: {v.get('avg')}, max: {v.get('max')}" if isinstance(v, dict) else str(v)
                    msg = f"ALARM: {self.key} size metrics exceeded threshold with {size_details}"
                elif self.metric_type == MetricType.ERROR_RATE:
                    msg = f"ALARM: {self.key} error rate exceeded threshold {self.thresholds[MetricType.ERROR_RATE]}% with {v}%"
                elif self.metric_type == MetricType.RESPONSE_TIME:
                    rt_details = f"avg: {v.get('avg')}ms, p95: {v.get('p95')}ms" if isinstance(v, dict) else f"{v}ms"
                    msg = f"ALARM: {self.key} response time exceeded threshold with {rt_details}"
                elif self.metric_type == MetricType.CONNECTION:
                    conn_details = f"new: {v.get('new')}, active: {v.get('active')}" if isinstance(v, dict) else str(v)
                    msg = f"ALARM: {self.key} connection metrics exceeded threshold with {conn_details}"
                else:
                    # Generic message for other metric types
                    msg = f"ALARM: {self.key} metric {self.metric_type} exceeded threshold with value {v}"
            else:
                msg = f"CLEARED: {self.key} metric {self.metric_type} returned to normal"
                
            if _debug: EnhancedSampleRateTask._debug("    - notification msg: %r", msg)
            
            # Send the notification through alert_manager if available
            try:
                # Import here to avoid circular dependencies
                import alert_manager
                
                # Prepare alert details
                alert_details = {
                    "key": self.key,
                    "metric_type": self.metric_type,
                    "value": v,
                    "threshold": self._get_threshold_for_metric(),
                    "timestamp": t
                }
                
                if not cleared:
                    alert_manager.trigger_alert(
                        alert_type="rate_threshold",
                        severity=alert_manager.Severity.WARNING,
                        source=f"rate_monitor_{self.metric_type}",
                        message=msg,
                        details=alert_details
                    )
                else:
                    alert_manager.resolve_alert(
                        alert_type="rate_threshold",
                        source=f"rate_monitor_{self.metric_type}",
                        key=self.key,
                        message=msg
                    )
            except (ImportError, AttributeError) as e:
                if _debug: EnhancedSampleRateTask._debug("    - alert_manager not available: %r", e)
                # Fall back to original behavior (e.g., logging)
                logger.warning(msg)
                
        except Exception as e:
            if _debug: EnhancedSampleRateTask._debug("    - notification error: %r", e)
            

# Factory function to create enhanced rate tasks
def create_enhanced_rate_task(key, interval, max_value, duration, metric_type=MetricType.COUNT):
    """
    Create an enhanced rate task for monitoring.
    
    Args:
        key: Metric key
        interval: Sampling interval in seconds
        max_value: Maximum value threshold
        duration: Number of intervals to trigger an alarm
        metric_type: Type of metric to monitor
        
    Returns:
        EnhancedSampleRateTask instance
    """
    return EnhancedSampleRateTask(key, interval, max_value, duration, metric_type)


# Enhanced Count function that processes additional metrics
def enhanced_count(msg, packet_info=None):
    """
    Enhanced version of Count that supports additional metrics.
    
    Args:
        msg: Message key to count
        packet_info: Additional packet information for metrics
    """
    # Import BACmon's Count to maintain compatibility
    from BACmon import Count as OriginalCount
    
    # Call original Count for backward compatibility
    OriginalCount(msg)
    
    # Process additional metrics if packet_info is provided
    if packet_info is not None and r is not None:
        # Get the metrics manager
        metrics_manager = metrics.get_metric_manager(r)
        
        # Process the packet
        metrics_manager.process_packet(msg, packet_info)


# Function to extract packet information from a BACnet PDU
def extract_packet_info_from_pdu(pdu):
    """
    Extract packet information from a BACnet PDU.
    
    Args:
        pdu: BACnet PDU object
        
    Returns:
        Dictionary with packet information
    """
    # Use the metrics module to extract BACnet metrics
    return metrics.extract_bacnet_metrics(pdu)


# Initialize the module with existing CountIntervals
def initialize_with_existing_intervals(count_intervals, redis_client):
    """
    Initialize the module with existing CountInterval instances.
    
    Args:
        count_intervals: List of existing CountInterval instances
        redis_client: Redis client instance
    """
    global r
    r = redis_client
    
    # Set Redis client for metrics module
    set_redis_client(redis_client)
    
    # Convert existing CountIntervals to EnhancedCountIntervals
    enhanced_intervals = []
    
    for interval in count_intervals:
        # Create an enhanced interval with the same parameters
        enhanced_interval = EnhancedCountInterval(
            interval.label,
            interval.modulus,
            interval.maxLen
        )
        
        # Copy over any necessary state
        enhanced_interval.lastInterval = interval.lastInterval
        enhanced_interval.cache = interval.cache.copy()
        
        enhanced_intervals.append(enhanced_interval)
        
    return enhanced_intervals 