#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BACmon Anomaly Detection Module

This module enhances BACmon's rate monitoring capabilities with advanced anomaly detection
algorithms. It provides detection for various types of anomalies beyond simple threshold
violations, including:

1. Sudden spikes (even if below absolute threshold)
2. Statistical anomalies based on historical patterns
3. Time-of-day pattern deviations
4. Trend-based anomalies (increasing/decreasing trends)
5. Seasonality-aware detection

The module is designed to work alongside the existing SampleRateTask system
while providing more sophisticated detection capabilities.
"""

import logging
import time
import math
import statistics
from typing import List, Dict, Tuple, Optional, Any, Union, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta
import numpy as np
import json

# Set up logging
logger = logging.getLogger(__name__)

# Type aliases
TimeSeriesT = List[Tuple[int, float]]  # List of (timestamp, value) pairs
AnomalyResultT = Dict[str, Any]  # Result of anomaly detection

# Import alert manager
import alert_manager

class AnomalyDetector:
    """Base class for anomaly detection algorithms."""
    
    def __init__(self, key: str, window_size: int = 30, sensitivity: float = 1.0):
        """
        Initialize the anomaly detector.
        
        Args:
            key: The monitoring key this detector will analyze
            window_size: Number of data points to consider for detection
            sensitivity: Sensitivity multiplier for detection thresholds (higher = more sensitive)
        """
        self.key = key
        self.window_size = window_size
        self.sensitivity = sensitivity
        self.history: TimeSeriesT = []
        self.last_anomaly_time: Optional[int] = None
        
    def add_sample(self, timestamp: int, value: float) -> None:
        """
        Add a new sample to the detector history.
        
        Args:
            timestamp: Unix timestamp of the sample
            value: Value of the sample
        """
        self.history.append((timestamp, value))
        
        # Keep history limited to window size
        if len(self.history) > self.window_size:
            self.history.pop(0)
    
    def detect(self) -> AnomalyResultT:
        """
        Detect anomalies in the current data.
        
        Returns:
            A dictionary with anomaly detection results
        """
        raise NotImplementedError("Subclasses must implement detect()")
    
    def get_values(self) -> List[float]:
        """Extract just the values from the time series."""
        return [v for _, v in self.history]
    
    def get_timestamps(self) -> List[int]:
        """Extract just the timestamps from the time series."""
        return [t for t, _ in self.history]


class ThresholdDetector(AnomalyDetector):
    """
    Enhanced threshold-based anomaly detector.
    
    This improves on the basic SampleRateTask by adding:
    - Adaptive thresholds based on recent history
    - Sudden spike detection even when below absolute threshold
    - Rate of change monitoring
    """
    
    def __init__(self, key: str, base_threshold: float, duration: int = 5, 
                 window_size: int = 30, spike_sensitivity: float = 2.0,
                 rate_of_change_threshold: float = 0.5):
        """
        Initialize the threshold detector.
        
        Args:
            key: The monitoring key this detector will analyze
            base_threshold: Base threshold value (similar to maxValue in SampleRateTask)
            duration: Number of consecutive samples needed to trigger (similar to duration in SampleRateTask)
            window_size: Number of data points to consider
            spike_sensitivity: Multiplier for spike detection sensitivity
            rate_of_change_threshold: Threshold for rate of change detection
        """
        super().__init__(key, window_size)
        self.base_threshold = base_threshold
        self.duration = duration
        self.spike_sensitivity = spike_sensitivity
        self.rate_of_change_threshold = rate_of_change_threshold
        self.consecutive_count = 0
        
    def detect(self) -> AnomalyResultT:
        """
        Detect threshold-based anomalies with enhancements.
        
        Returns:
            Dictionary with detection results including:
            - is_anomaly: Whether an anomaly was detected
            - anomaly_type: Type of anomaly detected (threshold, spike, rate_of_change)
            - value: Current value
            - threshold: Threshold that was used
            - confidence: Confidence score (0-1)
        """
        if len(self.history) < 2:
            return {"is_anomaly": False, "reason": "insufficient_data"}
        
        # Get the most recent value
        timestamp, value = self.history[-1]
        
        # Basic threshold check (similar to original SampleRateTask)
        is_threshold_exceeded = value > self.base_threshold
        
        # Check for sudden spikes
        recent_values = self.get_values()[-5:]  # Last 5 values
        if len(recent_values) >= 3:
            avg_recent = sum(recent_values[:-1]) / len(recent_values[:-1])
            is_spike = value > (avg_recent * self.spike_sensitivity) and value > (self.base_threshold * 0.7)
        else:
            is_spike = False
            
        # Check rate of change
        if len(self.history) >= 2:
            prev_timestamp, prev_value = self.history[-2]
            time_diff = timestamp - prev_timestamp
            if time_diff > 0:
                rate_of_change = abs(value - prev_value) / time_diff
                is_rate_anomaly = rate_of_change > self.rate_of_change_threshold
            else:
                is_rate_anomaly = False
        else:
            is_rate_anomaly = False
            
        # Combine detection methods
        is_anomaly = is_threshold_exceeded or is_spike or is_rate_anomaly
        
        if is_anomaly:
            self.consecutive_count += 1
            
            # Only trigger if consecutive count meets duration requirement
            if self.consecutive_count >= self.duration:
                anomaly_type = []
                if is_threshold_exceeded:
                    anomaly_type.append("threshold")
                if is_spike:
                    anomaly_type.append("spike")
                if is_rate_anomaly:
                    anomaly_type.append("rate_of_change")
                    
                self.last_anomaly_time = timestamp
                
                return {
                    "is_anomaly": True,
                    "anomaly_type": anomaly_type,
                    "value": value,
                    "threshold": self.base_threshold,
                    "consecutive_count": self.consecutive_count,
                    "confidence": min(self.consecutive_count / (self.duration * 1.5), 1.0)
                }
        else:
            self.consecutive_count = 0
            
        return {
            "is_anomaly": False,
            "value": value,
            "threshold": self.base_threshold,
            "consecutive_count": self.consecutive_count
        }


class StatisticalDetector(AnomalyDetector):
    """
    Statistical anomaly detector using standard deviation.
    
    This detector identifies anomalies based on statistical properties of the data:
    - Z-score based detection (values exceeding n standard deviations)
    - Moving average comparison
    - Seasonality-aware baselines
    """
    
    def __init__(self, key: str, window_size: int = 60, z_threshold: float = 3.0,
                 min_history: int = 10, sensitivity: float = 1.0):
        """
        Initialize the statistical detector.
        
        Args:
            key: The monitoring key this detector will analyze
            window_size: Number of data points to consider
            z_threshold: Z-score threshold for anomaly detection
            min_history: Minimum history length required for detection
            sensitivity: Sensitivity multiplier (higher = more sensitive)
        """
        super().__init__(key, window_size, sensitivity)
        self.z_threshold = z_threshold
        self.min_history = min_history
        
        # Initialize moving statistics
        self.moving_avg = 0.0
        self.moving_std = 0.0
        
    def update_statistics(self) -> None:
        """Update the moving statistics based on current history."""
        values = self.get_values()
        if len(values) >= self.min_history:
            self.moving_avg = statistics.mean(values)
            # Handle cases where all values are the same
            if all(v == values[0] for v in values):
                self.moving_std = 0.1  # Small non-zero value to prevent division by zero
            else:
                self.moving_std = max(statistics.stdev(values), 0.1)  # Prevent near-zero std
        else:
            # Not enough data yet
            self.moving_avg = sum(values) / max(len(values), 1)
            self.moving_std = 1.0  # Default value
            
    def detect(self) -> AnomalyResultT:
        """
        Detect statistical anomalies.
        
        Returns:
            Dictionary with detection results including:
            - is_anomaly: Whether an anomaly was detected
            - anomaly_type: Type of anomaly detected (z_score)
            - z_score: Z-score of the current value
            - value: Current value
            - confidence: Confidence score (0-1)
        """
        if len(self.history) < self.min_history:
            return {"is_anomaly": False, "reason": "insufficient_data"}
        
        # Update statistics
        self.update_statistics()
        
        # Get the most recent value
        timestamp, value = self.history[-1]
        
        # Calculate z-score
        if self.moving_std > 0:
            z_score = (value - self.moving_avg) / self.moving_std
        else:
            z_score = 0
            
        # Adjust threshold by sensitivity
        adjusted_threshold = self.z_threshold / self.sensitivity
        
        # Check if z-score exceeds threshold
        is_anomaly = abs(z_score) > adjusted_threshold
        
        if is_anomaly:
            self.last_anomaly_time = timestamp
            # Calculate confidence based on how much z-score exceeds threshold
            confidence = min(abs(z_score) / (adjusted_threshold * 2), 1.0)
            
            return {
                "is_anomaly": True,
                "anomaly_type": ["z_score"],
                "z_score": z_score,
                "value": value,
                "moving_avg": self.moving_avg,
                "moving_std": self.moving_std,
                "confidence": confidence
            }
        
        return {
            "is_anomaly": False,
            "z_score": z_score,
            "value": value,
            "moving_avg": self.moving_avg,
            "moving_std": self.moving_std
        }


class TimeAwareDetector(AnomalyDetector):
    """
    Time-aware anomaly detector that considers daily and weekly patterns.
    
    This detector maintains separate profiles for different times of day
    and days of the week to detect anomalies considering time patterns.
    """
    
    def __init__(self, key: str, window_size: int = 168, # 24*7 hours for a week
                 hour_granularity: int = 1, # Group by hour
                 z_threshold: float = 3.0,
                 min_history_per_slot: int = 3,
                 sensitivity: float = 1.0):
        """
        Initialize the time-aware detector.
        
        Args:
            key: The monitoring key this detector will analyze
            window_size: Number of data points to consider overall
            hour_granularity: Hour grouping granularity (1 = hourly, 3 = every 3 hours, etc.)
            z_threshold: Z-score threshold for anomaly detection
            min_history_per_slot: Minimum history length required for each time slot
            sensitivity: Sensitivity multiplier (higher = more sensitive)
        """
        super().__init__(key, window_size, sensitivity)
        self.hour_granularity = hour_granularity
        self.z_threshold = z_threshold
        self.min_history_per_slot = min_history_per_slot
        
        # Initialize time slot profiles
        # Format: {(day_of_week, hour_slot): [(timestamp, value), ...]}
        self.time_slots: Dict[Tuple[int, int], TimeSeriesT] = defaultdict(list)
        
        # Statistics for each time slot
        # Format: {(day_of_week, hour_slot): (mean, std)}
        self.slot_statistics: Dict[Tuple[int, int], Tuple[float, float]] = {}
        
    def add_sample(self, timestamp: int, value: float) -> None:
        """
        Add a new sample to the detector history and appropriate time slot.
        
        Args:
            timestamp: Unix timestamp of the sample
            value: Value of the sample
        """
        # Add to overall history
        super().add_sample(timestamp, value)
        
        # Add to time slot history
        dt = datetime.fromtimestamp(timestamp)
        day_of_week = dt.weekday()  # 0-6 (Monday to Sunday)
        hour_slot = dt.hour // self.hour_granularity
        
        slot_key = (day_of_week, hour_slot)
        self.time_slots[slot_key].append((timestamp, value))
        
        # Keep slot history limited
        max_slot_history = max(self.min_history_per_slot * 4, 20)
        if len(self.time_slots[slot_key]) > max_slot_history:
            self.time_slots[slot_key].pop(0)
        
        # Update statistics for this slot
        self._update_slot_statistics(slot_key)
    
    def _update_slot_statistics(self, slot_key: Tuple[int, int]) -> None:
        """
        Update statistics for a specific time slot.
        
        Args:
            slot_key: (day_of_week, hour_slot) tuple
        """
        slot_values = [v for _, v in self.time_slots[slot_key]]
        
        if len(slot_values) >= self.min_history_per_slot:
            mean_value = statistics.mean(slot_values)
            
            # Handle cases where all values are the same
            if all(v == slot_values[0] for v in slot_values):
                std_value = 0.1  # Small non-zero value
            else:
                std_value = max(statistics.stdev(slot_values), 0.1)
                
            self.slot_statistics[slot_key] = (mean_value, std_value)
    
    def detect(self) -> AnomalyResultT:
        """
        Detect time-aware anomalies.
        
        Returns:
            Dictionary with detection results including:
            - is_anomaly: Whether an anomaly was detected
            - anomaly_type: Type of anomaly detected
            - time_context: Time context information
            - value: Current value
            - expected_value: Expected value for this time slot
            - confidence: Confidence score (0-1)
        """
        if not self.history:
            return {"is_anomaly": False, "reason": "no_data"}
        
        # Get the most recent value
        timestamp, value = self.history[-1]
        
        # Get time slot for this sample
        dt = datetime.fromtimestamp(timestamp)
        day_of_week = dt.weekday()
        hour_slot = dt.hour // self.hour_granularity
        slot_key = (day_of_week, hour_slot)
        
        # Check if we have enough history for this slot
        if (slot_key not in self.slot_statistics or 
            len(self.time_slots[slot_key]) < self.min_history_per_slot):
            # Not enough data for this specific time slot
            # Fall back to general statistics
            if len(self.history) < self.min_history_per_slot:
                return {"is_anomaly": False, "reason": "insufficient_data"}
                
            values = self.get_values()
            mean_value = statistics.mean(values)
            std_value = max(statistics.stdev(values) if len(values) > 1 else 1.0, 0.1)
        else:
            # Use time-slot specific statistics
            mean_value, std_value = self.slot_statistics[slot_key]
        
        # Calculate z-score
        z_score = (value - mean_value) / std_value
        
        # Adjust threshold by sensitivity
        adjusted_threshold = self.z_threshold / self.sensitivity
        
        # Check if z-score exceeds threshold
        is_anomaly = abs(z_score) > adjusted_threshold
        
        # Time context information
        time_context = {
            "day_of_week": day_of_week,
            "hour": dt.hour,
            "hour_slot": hour_slot,
            "time_str": dt.strftime("%A %H:%M")
        }
        
        if is_anomaly:
            self.last_anomaly_time = timestamp
            confidence = min(abs(z_score) / (adjusted_threshold * 2), 1.0)
            
            return {
                "is_anomaly": True,
                "anomaly_type": ["time_pattern"],
                "z_score": z_score,
                "value": value,
                "expected_value": mean_value,
                "time_context": time_context,
                "confidence": confidence
            }
        
        return {
            "is_anomaly": False,
            "z_score": z_score,
            "value": value,
            "expected_value": mean_value,
            "time_context": time_context
        }


class TrendDetector(AnomalyDetector):
    """
    Trend-based anomaly detector that identifies unusual trends.
    
    This detector looks for significant upward or downward trends
    that deviate from normal patterns.
    """
    
    def __init__(self, key: str, window_size: int = 30, trend_window: int = 10,
                 trend_threshold: float = 0.2, sensitivity: float = 1.0):
        """
        Initialize the trend detector.
        
        Args:
            key: The monitoring key this detector will analyze
            window_size: Overall window size for historical context
            trend_window: Window size to analyze for trend
            trend_threshold: Threshold for trend significance
            sensitivity: Sensitivity multiplier (higher = more sensitive)
        """
        super().__init__(key, window_size, sensitivity)
        self.trend_window = min(trend_window, window_size)
        self.trend_threshold = trend_threshold
        
    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calculate the trend coefficient from a list of values.
        
        Args:
            values: List of values to analyze
            
        Returns:
            Trend coefficient (-1 to 1) indicating direction and strength
        """
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
            
        # Calculate trend coefficient (normalized to -1 to 1)
        slope = numerator / denominator
        max_possible_slope = (max(values) - min(values)) / (n - 1) if n > 1 else 1.0
        
        if max_possible_slope == 0:
            return 0.0
            
        normalized_trend = slope / max_possible_slope
        return max(min(normalized_trend, 1.0), -1.0)
        
    def detect(self) -> AnomalyResultT:
        """
        Detect trend-based anomalies.
        
        Returns:
            Dictionary with detection results including:
            - is_anomaly: Whether an anomaly was detected
            - anomaly_type: Type of anomaly detected (increasing_trend, decreasing_trend)
            - trend: Trend coefficient
            - values: Recent values used for trend analysis
            - confidence: Confidence score (0-1)
        """
        if len(self.history) < self.trend_window:
            return {"is_anomaly": False, "reason": "insufficient_data"}
        
        # Get recent values for trend analysis
        recent_values = self.get_values()[-self.trend_window:]
        
        # Calculate trend
        trend = self._calculate_trend(recent_values)
        
        # Adjust threshold by sensitivity
        adjusted_threshold = self.trend_threshold / self.sensitivity
        
        # Check if trend exceeds threshold
        is_anomaly = abs(trend) > adjusted_threshold
        
        if is_anomaly:
            timestamp = self.history[-1][0]
            self.last_anomaly_time = timestamp
            
            # Determine trend direction
            if trend > 0:
                anomaly_type = "increasing_trend"
            else:
                anomaly_type = "decreasing_trend"
                
            # Calculate confidence
            confidence = min(abs(trend) / adjusted_threshold, 1.0)
            
            return {
                "is_anomaly": True,
                "anomaly_type": [anomaly_type],
                "trend": trend,
                "values": recent_values,
                "confidence": confidence
            }
        
        return {
            "is_anomaly": False,
            "trend": trend,
            "values": recent_values
        }


class AnomalyDetectionManager:
    """
    Manages multiple anomaly detectors for comprehensive detection capabilities.
    
    This class coordinates multiple detection algorithms and aggregates their results
    to provide a unified anomaly detection system.
    """
    
    def __init__(self, key: str, config: Dict[str, Any] = None):
        """
        Initialize the anomaly detection manager.
        
        Args:
            key: The monitoring key to analyze
            config: Configuration dictionary for the detectors
        """
        self.key = key
        self.config = config or {}
        
        # Default configuration
        self.base_threshold = self.config.get('base_threshold', 20)
        self.duration = self.config.get('duration', 5)
        self.window_size = self.config.get('window_size', 60)
        self.sensitivity = self.config.get('sensitivity', 1.0)
        
        # Initialize detectors
        self.detectors = {
            'threshold': ThresholdDetector(
                key, 
                base_threshold=self.base_threshold,
                duration=self.duration,
                window_size=self.window_size,
                spike_sensitivity=self.config.get('spike_sensitivity', 2.0)
            ),
            'statistical': StatisticalDetector(
                key,
                window_size=self.window_size,
                z_threshold=self.config.get('z_threshold', 3.0),
                sensitivity=self.sensitivity
            ),
            'time_aware': TimeAwareDetector(
                key,
                window_size=168,  # One week of hourly data
                hour_granularity=self.config.get('hour_granularity', 1),
                sensitivity=self.sensitivity
            ),
            'trend': TrendDetector(
                key,
                window_size=self.window_size,
                trend_window=self.config.get('trend_window', 10),
                trend_threshold=self.config.get('trend_threshold', 0.2),
                sensitivity=self.sensitivity
            )
        }
        
        # Detector weights for combined scoring
        self.detector_weights = {
            'threshold': self.config.get('threshold_weight', 1.0),
            'statistical': self.config.get('statistical_weight', 0.8),
            'time_aware': self.config.get('time_aware_weight', 0.7),
            'trend': self.config.get('trend_weight', 0.6)
        }
        
        # Anomaly history
        self.anomaly_history: List[Dict[str, Any]] = []
        self.max_history_items = self.config.get('max_history_items', 100)
        
        # Initialize alert manager with our Redis client
        self.alert_manager = alert_manager.get_alert_manager(None)
        
    def add_sample(self, timestamp: int, value: float) -> None:
        """
        Add a sample to all detectors.
        
        Args:
            timestamp: Unix timestamp of the sample
            value: Value of the sample
        """
        for detector in self.detectors.values():
            detector.add_sample(timestamp, value)
    
    def detect(self) -> AnomalyResultT:
        """
        Run all anomaly detectors and combine results.
        
        Returns:
            Dictionary with combined detection results
        """
        # Run all detectors
        results = {}
        for name, detector in self.detectors.items():
            results[name] = detector.detect()
        
        # Combine results
        combined_result = self._combine_results(results)
        
        # Store anomaly in history if detected
        if combined_result["is_anomaly"]:
            self.anomaly_history.append({
                "timestamp": self.detectors["threshold"].history[-1][0] if self.detectors["threshold"].history else time.time(),
                "value": self.detectors["threshold"].history[-1][1] if self.detectors["threshold"].history else 0,
                "result": combined_result
            })
            
            # Trim history if needed
            if len(self.anomaly_history) > self.max_history_items:
                self.anomaly_history.pop(0)
        
        return combined_result
    
    def _combine_results(self, results: Dict[str, AnomalyResultT]) -> AnomalyResultT:
        """
        Combine results from multiple detectors.
        
        Args:
            results: Dictionary of results from each detector
            
        Returns:
            Combined anomaly detection result
        """
        # Count anomalies and calculate weighted score
        anomaly_count = 0
        total_score = 0.0
        anomaly_types = []
        
        for name, result in results.items():
            if result.get("is_anomaly", False):
                anomaly_count += 1
                confidence = result.get("confidence", 0.5)
                total_score += confidence * self.detector_weights.get(name, 1.0)
                
                # Collect anomaly types
                if "anomaly_type" in result:
                    anomaly_types.extend(result["anomaly_type"])
        
        # Normalize score
        total_weight = sum(self.detector_weights.values())
        if total_weight > 0:
            normalized_score = total_score / total_weight
        else:
            normalized_score = 0
            
        # Determine if this is an anomaly based on score and count
        is_anomaly = normalized_score > 0.5 or anomaly_count >= 2
        
        # Create combined result
        timestamp, value = self.detectors["threshold"].history[-1] if self.detectors["threshold"].history else (int(time.time()), 0)
        
        combined_result = {
            "is_anomaly": is_anomaly,
            "anomaly_score": normalized_score,
            "anomaly_count": anomaly_count,
            "anomaly_types": list(set(anomaly_types)),  # Remove duplicates
            "timestamp": timestamp,
            "value": value,
            "detector_results": results
        }
        
        return combined_result
    
    def get_anomaly_history(self) -> List[Dict[str, Any]]:
        """Get the history of detected anomalies."""
        return self.anomaly_history
    
    def store_result_for_visualization(self, redis_client, key: str, timestamp: int, value: float, result: Dict[str, Any]) -> None:
        """
        Store anomaly detection result in Redis for visualization.
        
        Args:
            redis_client: Redis client instance
            key: The monitoring key (e.g., 'total')
            timestamp: The timestamp of the data point
            value: The value of the data point
            result: The result from process_value
        """
        if not result.get('is_anomaly', False):
            return
        
        # Create entry for history
        entry = {
            'timestamp': timestamp,
            'value': value,
            'result': result
        }
        
        # Store in Redis
        # First, try to get existing history
        history_key = f"{key}:enhanced_anomaly_history"
        existing_history = redis_client.get(history_key)
        
        history = []
        if existing_history:
            try:
                history = json.loads(existing_history)
                # Keep only the last 1000 entries to prevent unbounded growth
                if len(history) >= 1000:
                    history = history[-999:]
            except Exception:
                # If we can't parse it, start fresh
                history = []
        
        # Add new entry and save back to Redis
        history.append(entry)
        redis_client.set(history_key, json.dumps(history))
        
        # Also update anomaly type distribution for quick access
        type_distribution_key = f"{key}:anomaly_type_distribution"
        try:
            type_distribution = {}
            existing_distribution = redis_client.get(type_distribution_key)
            
            if existing_distribution:
                type_distribution = json.loads(existing_distribution)
            
            # Update counts
            for anomaly_type in result.get('anomaly_types', []):
                if anomaly_type in type_distribution:
                    type_distribution[anomaly_type] += 1
                else:
                    type_distribution[anomaly_type] = 1
                    
            redis_client.set(type_distribution_key, json.dumps(type_distribution))
        except Exception:
            # If we can't update the distribution, just continue
            pass

    def notify_anomaly_detected(self, key, rate_type, threshold, actual_value, device=None, details=None):
        """
        Send notification when an anomaly is detected.
        
        Args:
            key: The rate key (e.g., 'ip/192.168.1.1')
            rate_type: Type of rate anomaly (threshold, statistical, etc.)
            threshold: The threshold or expected value
            actual_value: The actual observed value
            device: Optional device identifier
            details: Additional anomaly details
        """
        if not self.redis_client:
            return
            
        # Format message text for legacy Redis storage
        entity = key.replace('/', '-')
        message = f"Rate anomaly: {rate_type} ({actual_value:.2f} > {threshold:.2f})"
        msgtxt = f"{entity}/rate-anomaly/{message}"
        
        # Store in legacy critical messages set for backward compatibility
        if self.redis_client.sadd('critical-messages', msgtxt):
            print(f"CRITICAL: {msgtxt}")
            
        # Also create a structured alert using the alert manager
        alert_details = {
            'rate_type': rate_type,
            'threshold': threshold,
            'actual_value': actual_value,
            'timestamp': int(time.time())
        }
        
        if details:
            alert_details.update(details)
            
        # Create the alert with appropriate severity based on rate_type
        if rate_type.lower() == 'threshold':
            level = alert_manager.AlertLevel.WARNING
        elif rate_type.lower() == 'statistical':
            level = alert_manager.AlertLevel.ALERT
        elif rate_type.lower() == 'trend':
            level = alert_manager.AlertLevel.ALERT
        else:
            level = alert_manager.AlertLevel.CRITICAL
            
        alert_manager.create_alert(
            key='rate-anomaly',
            message=message,
            level=level,
            source='anomaly_detection',
            details=alert_details,
            entity=entity
        )


class EnhancedRateTask:
    """
    Enhanced version of SampleRateTask that uses advanced anomaly detection.
    
    This class is designed to be a drop-in replacement for SampleRateTask
    but with enhanced detection capabilities.
    """
    
    def __init__(self, key: str, interval: int, base_threshold: float, 
                 duration: int, config: Dict[str, Any] = None):
        """
        Initialize the enhanced rate task.
        
        Args:
            key: The monitoring key to analyze
            interval: Sampling interval in seconds
            base_threshold: Base threshold for detection
            duration: Duration for threshold violation
            config: Additional configuration options
        """
        self.key = key
        self.interval = interval
        self.base_threshold = base_threshold
        self.duration = duration
        self.config = config or {}
        
        # Create anomaly detection manager
        detector_config = {
            'base_threshold': base_threshold,
            'duration': duration,
            'window_size': self.config.get('window_size', 60),
            'sensitivity': self.config.get('sensitivity', 1.0),
            'spike_sensitivity': self.config.get('spike_sensitivity', 2.0),
            'z_threshold': self.config.get('z_threshold', 3.0),
            'hour_granularity': self.config.get('hour_granularity', 1),
            'trend_window': self.config.get('trend_window', 10),
            'trend_threshold': self.config.get('trend_threshold', 0.2)
        }
        
        self.detector = AnomalyDetectionManager(key, detector_config)
        
        # Initialize alarm state
        self.alarm = False
        self.alarm_time = None
        self.next_check = int(time.time())
        
        # Redis client (to be set by caller)
        self.redis_client = None
    
    def set_redis_client(self, redis_client) -> None:
        """Set the Redis client for this task."""
        self.redis_client = redis_client
        
    def get_samples(self, start_time: int, end_time: int) -> TimeSeriesT:
        """
        Get samples from Redis.
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
            
        Returns:
            List of (timestamp, value) pairs
        """
        if not self.redis_client:
            logger.error("Redis client not set for EnhancedRateTask")
            return []
        
        samples = self.redis_client.lrange(self.key, 0, 25)
        if not samples:
            return []
            
        # Process samples
        samples.reverse()
        processed_samples = []
        
        for sample_str in samples:
            try:
                t, v = eval(sample_str)
                if start_time <= t <= end_time:
                    processed_samples.append((t, v))
            except Exception as e:
                logger.error(f"Error processing sample {sample_str}: {e}")
                
        return processed_samples
    
    def process_task(self) -> Dict[str, Any]:
        """
        Process the task and detect anomalies.
        
        Returns:
            Anomaly detection result
        """
        now = int(time.time())
        now = now - (now % self.interval)
        
        # Get samples
        samples = self.get_samples(self.next_check, now)
        
        # Update next check time
        if samples:
            self.next_check = samples[-1][0] + self.interval
        else:
            self.next_check = now
            
        # Process samples
        result = None
        
        for timestamp, value in samples:
            # Add to detector
            self.detector.add_sample(timestamp, value)
            
            # Detect anomalies
            result = self.detector.detect()
            
            # Store result for visualization
            if self.redis_client and result:
                try:
                    self.detector.store_result_for_visualization(
                        self.redis_client, self.key, timestamp, value, result
                    )
                except Exception as e:
                    logger.error(f"Error storing visualization data: {e}")
            
            # Update alarm state
            if result["is_anomaly"] and not self.alarm:
                self.alarm = True
                self.alarm_time = timestamp
                
                # Save alarm to Redis
                if self.redis_client:
                    self.redis_client.set(f"{self.key}:alarm", timestamp)
                    
                    # Log the anomaly details
                    anomaly_types = ",".join(result.get("anomaly_types", ["unknown"]))
                    msg = f"Anomaly detected for {self.key}: {anomaly_types} (score: {result.get('anomaly_score', 0):.2f})"
                    logger.warning(msg)
                    
                    # Add to critical messages
                    msgtxt = f"-/{self.key}/Anomaly Detected"
                    if self.redis_client.sadd('critical-messages', msgtxt):
                        # Further notification logic can be added here
                        pass
            
            # Check if alarm should be cleared
            elif self.alarm and not result["is_anomaly"]:
                # Use a cooldown period before clearing (similar to original SampleRateTask)
                if "consecutive_count" in result and result["consecutive_count"] == 0:
                    self.alarm = False
                    
                    # Clear alarm in Redis
                    if self.redis_client:
                        # Save alarm history
                        self.redis_client.lpush(
                            f"{self.key}:alarm-history", 
                            str([self.alarm_time, timestamp])
                        )
                        # Delete current alarm
                        self.redis_client.delete(f"{self.key}:alarm")
                        
                    self.alarm_time = None
        
        return result

    def check_threshold_anomaly(self, current_rate):
        """Check if the current rate exceeds the configured threshold."""
        threshold = self.config.get('threshold', 0)
        if threshold > 0 and current_rate > threshold:
            # Notify anomaly
            self.manager.notify_anomaly_detected(
                key=self.key,
                rate_type='threshold',
                threshold=threshold,
                actual_value=current_rate,
                details={
                    'anomaly_type': 'threshold_violation',
                    'config': {
                        'threshold': threshold
                    }
                }
            )
            return True
        return False
    
    def check_statistical_anomaly(self, current_rate):
        """Check if the current rate is statistically significant outlier."""
        # ... existing code ...
        
        if is_anomaly:
            # Notify anomaly
            self.manager.notify_anomaly_detected(
                key=self.key,
                rate_type='statistical',
                threshold=threshold,
                actual_value=current_rate,
                details={
                    'anomaly_type': 'statistical_outlier',
                    'config': {
                        'z_score_threshold': z_score_threshold,
                        'min_samples': min_samples
                    },
                    'statistics': {
                        'mean': mean,
                        'std_dev': std_dev,
                        'z_score': z_score
                    }
                }
            )
            
        # ... existing code ...
    
    def check_trend_anomaly(self, current_rate):
        """Check if there's an unusual trend in the rate."""
        # ... existing code ...
        
        if is_anomaly:
            # Notify anomaly
            self.manager.notify_anomaly_detected(
                key=self.key,
                rate_type='trend',
                threshold=threshold,
                actual_value=slope,
                details={
                    'anomaly_type': 'trend_anomaly',
                    'config': {
                        'slope_threshold': slope_threshold,
                        'window_size': window_size
                    },
                    'statistics': {
                        'slope': slope,
                        'r_squared': r_squared
                    }
                }
            )
            
        # ... existing code ...
    
    def check_time_pattern_anomaly(self, current_rate):
        """Check if the current rate deviates from historical patterns for this time."""
        # ... existing code ...
        
        if is_anomaly:
            # Notify anomaly
            self.manager.notify_anomaly_detected(
                key=self.key,
                rate_type='time-pattern',
                threshold=expected_range[1],
                actual_value=current_rate,
                details={
                    'anomaly_type': 'time_pattern_deviation',
                    'config': {
                        'time_window': time_window,
                        'day_grouping': day_grouping
                    },
                    'statistics': {
                        'expected_min': expected_range[0],
                        'expected_max': expected_range[1],
                        'deviation_factor': deviation
                    }
                }
            )
            
        # ... existing code ...


# Utility functions for working with anomaly detection

def create_enhanced_rate_task(key: str, interval: int, base_threshold: float, 
                              duration: int, config: Dict[str, Any] = None) -> EnhancedRateTask:
    """
    Create an enhanced rate task.
    
    Args:
        key: The monitoring key to analyze
        interval: Sampling interval in seconds
        base_threshold: Base threshold for detection
        duration: Duration for threshold violation
        config: Additional configuration options
        
    Returns:
        Configured EnhancedRateTask instance
    """
    return EnhancedRateTask(key, interval, base_threshold, duration, config)


def detect_anomalies_from_data(key: str, data: TimeSeriesT, 
                              config: Dict[str, Any] = None) -> List[AnomalyResultT]:
    """
    Detect anomalies from a list of time series data.
    
    Args:
        key: The monitoring key to analyze
        data: List of (timestamp, value) pairs
        config: Configuration options
        
    Returns:
        List of anomaly detection results
    """
    detector = AnomalyDetectionManager(key, config)
    results = []
    
    for timestamp, value in data:
        detector.add_sample(timestamp, value)
        result = detector.detect()
        results.append(result)
        
    return results 