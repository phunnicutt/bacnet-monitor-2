#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BACmon Extended Metrics Module

This module extends BACmon's rate monitoring capabilities to track additional metrics
beyond simple packet counts, including:

1. Packet sizes (average, minimum, maximum)
2. Protocol distributions (percentage of different protocols over time)
3. Error rates (ratio of error packets to total traffic)
4. Response times (for relevant protocol exchanges)
5. Connection patterns (new connections per second, connection durations)
6. Service-specific metrics based on packet content analysis

It works alongside the existing CountInterval and SampleRateTask system while
providing more sophisticated metric collection capabilities.
"""

import logging
import time
import statistics
from typing import Dict, List, Tuple, Any, Optional, Set, Union, DefaultDict
from collections import defaultdict, deque
import json
import redis
import struct

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type aliases
MetricValueT = Union[int, float, Dict[str, Union[int, float]]]
MetricSampleT = Tuple[int, MetricValueT]  # (timestamp, value) pairs
TimeSeriesT = List[MetricSampleT]  # List of samples

class MetricType:
    """Enumeration of supported metric types."""
    COUNT = "count"                     # Simple packet count (original metric)
    SIZE = "size"                       # Packet size metrics (min, max, avg)
    PROTOCOL = "protocol"               # Protocol distribution percentages
    ERROR_RATE = "error_rate"           # Error rate (errors/total)
    RESPONSE_TIME = "response_time"     # Response time for exchanges
    CONNECTION = "connection"           # Connection metrics (new, duration)
    SERVICE = "service"                 # Service-specific metrics

class MetricProcessor:
    """Base class for metric processors."""
    
    def __init__(self, metric_type: str):
        """
        Initialize the metric processor.
        
        Args:
            metric_type: The type of metric this processor handles
        """
        self.metric_type = metric_type
        self.current_value: MetricValueT = 0
        self.reset()
        
    def reset(self) -> None:
        """Reset the processor state for a new interval."""
        self.current_value = 0
        
    def process(self, packet: Dict[str, Any]) -> None:
        """
        Process a packet and update the metric.
        
        Args:
            packet: Dictionary containing packet information
        """
        raise NotImplementedError("Subclasses must implement process()")
        
    def get_value(self) -> MetricValueT:
        """
        Get the current metric value.
        
        Returns:
            The current metric value
        """
        return self.current_value
        
    def serialize(self, value: MetricValueT) -> str:
        """
        Serialize a metric value for storage.
        
        Args:
            value: Metric value to serialize
            
        Returns:
            Serialized string representation
        """
        return json.dumps(value)
        
    def deserialize(self, serialized: str) -> MetricValueT:
        """
        Deserialize a stored metric value.
        
        Args:
            serialized: Serialized string representation
            
        Returns:
            Deserialized metric value
        """
        return json.loads(serialized)


class CountMetricProcessor(MetricProcessor):
    """Simple packet count processor (original behavior)."""
    
    def __init__(self):
        super().__init__(MetricType.COUNT)
        
    def process(self, packet: Dict[str, Any]) -> None:
        """Increment the counter by 1."""
        self.current_value = int(self.current_value) + 1


class SizeMetricProcessor(MetricProcessor):
    """Packet size metric processor."""
    
    def __init__(self):
        super().__init__(MetricType.SIZE)
        self.reset()
        
    def reset(self) -> None:
        """Reset size statistics."""
        self.current_value = {
            "min": None,
            "max": None,
            "avg": None,
            "total": 0,
            "count": 0
        }
        
    def process(self, packet: Dict[str, Any]) -> None:
        """Update size statistics with the packet."""
        if "size" not in packet:
            return
            
        size = packet["size"]
        value = self.current_value
        
        # Update count and total
        value["count"] += 1
        value["total"] += size
        
        # Update min/max
        if value["min"] is None or size < value["min"]:
            value["min"] = size
        if value["max"] is None or size > value["max"]:
            value["max"] = size
            
        # Update average
        value["avg"] = value["total"] / value["count"]


class ProtocolMetricProcessor(MetricProcessor):
    """Protocol distribution metric processor."""
    
    def __init__(self):
        super().__init__(MetricType.PROTOCOL)
        self.reset()
        
    def reset(self) -> None:
        """Reset protocol distribution."""
        self.current_value = {
            "protocols": {},
            "total": 0
        }
        
    def process(self, packet: Dict[str, Any]) -> None:
        """Update protocol distribution with the packet."""
        if "protocol" not in packet:
            return
            
        protocol = packet["protocol"]
        value = self.current_value
        
        # Update protocol count
        if protocol not in value["protocols"]:
            value["protocols"][protocol] = 0
        value["protocols"][protocol] += 1
        
        # Update total
        value["total"] += 1
        
    def get_value(self) -> MetricValueT:
        """
        Get the current metric value with percentages.
        
        Returns:
            Dictionary with protocol counts and percentages
        """
        value = self.current_value
        
        # Calculate percentages
        result = {
            "protocols": {},
            "total": value["total"]
        }
        
        if value["total"] > 0:
            for protocol, count in value["protocols"].items():
                result["protocols"][protocol] = {
                    "count": count,
                    "percentage": (count / value["total"]) * 100
                }
                
        return result


class ErrorRateMetricProcessor(MetricProcessor):
    """Error rate metric processor."""
    
    def __init__(self):
        super().__init__(MetricType.ERROR_RATE)
        self.reset()
        
    def reset(self) -> None:
        """Reset error rate statistics."""
        self.current_value = {
            "errors": 0,
            "total": 0,
            "rate": 0.0
        }
        
    def process(self, packet: Dict[str, Any]) -> None:
        """Update error rate with the packet."""
        value = self.current_value
        
        # Update total
        value["total"] += 1
        
        # Check for error
        if "error" in packet and packet["error"]:
            value["errors"] += 1
            
        # Update rate
        if value["total"] > 0:
            value["rate"] = (value["errors"] / value["total"]) * 100


class ResponseTimeMetricProcessor(MetricProcessor):
    """Response time metric processor."""
    
    def __init__(self):
        super().__init__(MetricType.RESPONSE_TIME)
        self.reset()
        
    def reset(self) -> None:
        """Reset response time statistics."""
        self.current_value = {
            "min": None,
            "max": None,
            "avg": None,
            "p50": None,  # 50th percentile (median)
            "p90": None,  # 90th percentile
            "p95": None,  # 95th percentile
            "count": 0,
            "samples": []
        }
        
    def process(self, packet: Dict[str, Any]) -> None:
        """Update response time statistics with the packet."""
        if "response_time" not in packet:
            return
            
        response_time = packet["response_time"]
        value = self.current_value
        
        # Update samples list
        value["samples"].append(response_time)
        value["count"] += 1
        
        # Update min/max
        if value["min"] is None or response_time < value["min"]:
            value["min"] = response_time
        if value["max"] is None or response_time > value["max"]:
            value["max"] = response_time
        
        # Calculate statistics if we have enough samples
        if len(value["samples"]) >= 5:
            value["avg"] = statistics.mean(value["samples"])
            
            # Calculate percentiles
            sorted_samples = sorted(value["samples"])
            value["p50"] = sorted_samples[len(sorted_samples) // 2]
            value["p90"] = sorted_samples[int(len(sorted_samples) * 0.9)]
            value["p95"] = sorted_samples[int(len(sorted_samples) * 0.95)]
            
            # Keep samples list from growing too large
            if len(value["samples"]) > 100:
                value["samples"] = value["samples"][-100:]
    
    def get_value(self) -> MetricValueT:
        """
        Get the current metric value.
        
        Returns:
            Response time statistics (without raw samples)
        """
        value = self.current_value.copy()
        # Don't include samples in the returned value to keep it small
        if "samples" in value:
            del value["samples"]
        return value


class ConnectionMetricProcessor(MetricProcessor):
    """Connection metrics processor."""
    
    def __init__(self):
        super().__init__(MetricType.CONNECTION)
        self.reset()
        
    def reset(self) -> None:
        """Reset connection statistics."""
        self.current_value = {
            "new_connections": 0,
            "closed_connections": 0,
            "active_connections": 0,
            "avg_duration": None,
            "connection_map": {}  # Used internally to track connections
        }
        
    def process(self, packet: Dict[str, Any]) -> None:
        """Update connection statistics with the packet."""
        # Check if this is a connection-related packet
        if "connection" not in packet:
            return
            
        conn_info = packet["connection"]
        value = self.current_value
        
        # Handle new connection
        if conn_info.get("new", False):
            value["new_connections"] += 1
            conn_id = conn_info.get("id")
            if conn_id:
                value["connection_map"][conn_id] = {
                    "start_time": conn_info.get("time", int(time.time())),
                    "active": True
                }
            value["active_connections"] += 1
            
        # Handle closed connection
        elif conn_info.get("closed", False):
            value["closed_connections"] += 1
            conn_id = conn_info.get("id")
            if conn_id and conn_id in value["connection_map"]:
                conn = value["connection_map"][conn_id]
                if conn["active"]:
                    value["active_connections"] -= 1
                    conn["active"] = False
                    
                    # Calculate duration
                    start_time = conn["start_time"]
                    end_time = conn_info.get("time", int(time.time()))
                    duration = end_time - start_time
                    
                    # Update average duration
                    if value["avg_duration"] is None:
                        value["avg_duration"] = duration
                    else:
                        # Simple moving average
                        alpha = 0.2  # Weight for new sample
                        value["avg_duration"] = (alpha * duration) + ((1 - alpha) * value["avg_duration"])
    
    def get_value(self) -> MetricValueT:
        """
        Get the current metric value.
        
        Returns:
            Connection statistics (without internal connection map)
        """
        value = self.current_value.copy()
        # Don't include connection map in the returned value
        if "connection_map" in value:
            del value["connection_map"]
        return value


class ServiceMetricProcessor(MetricProcessor):
    """Service-specific metrics processor."""
    
    def __init__(self, service_name: str, metrics_of_interest: List[str]):
        """
        Initialize service-specific metrics processor.
        
        Args:
            service_name: Name of the service being monitored
            metrics_of_interest: List of service-specific metrics to track
        """
        super().__init__(MetricType.SERVICE)
        self.service_name = service_name
        self.metrics_of_interest = metrics_of_interest
        self.reset()
        
    def reset(self) -> None:
        """Reset service metrics."""
        self.current_value = {
            "service": self.service_name,
            "metrics": {metric: 0 for metric in self.metrics_of_interest}
        }
        
    def process(self, packet: Dict[str, Any]) -> None:
        """Update service metrics with the packet."""
        # Check if this packet is related to our service
        if "service" not in packet or packet["service"] != self.service_name:
            return
            
        # Process metrics of interest
        value = self.current_value
        for metric in self.metrics_of_interest:
            if metric in packet:
                # If the metric is already a counter, increment it
                if isinstance(value["metrics"][metric], int):
                    value["metrics"][metric] += packet[metric]
                # Otherwise, store the latest value
                else:
                    value["metrics"][metric] = packet[metric]


class MetricManager:
    """
    Manages metric collection, storage, and retrieval.
    
    This class coordinates the various metric processors and handles
    storage and retrieval of metric data from Redis.
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize the metric manager.
        
        Args:
            redis_client: Redis client for storing metrics
        """
        self.redis_client = redis_client
        self.processors: Dict[str, Dict[str, MetricProcessor]] = {}
        self.initialize()
        
    def initialize(self) -> None:
        """Initialize the metric manager."""
        # Register standard processors for each key as needed
        pass
        
    def set_redis_client(self, redis_client) -> None:
        """
        Set the Redis client for the metric manager.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis_client = redis_client
        
    def add_processor(self, key: str, processor: MetricProcessor) -> None:
        """
        Add a metric processor for a specific key.
        
        Args:
            key: The message key to associate with this processor
            processor: The metric processor to add
        """
        if key not in self.processors:
            self.processors[key] = {}
            
        self.processors[key][processor.metric_type] = processor
        
    def process_packet(self, key: str, packet: Dict[str, Any]) -> None:
        """
        Process a packet for a specific key.
        
        Args:
            key: The message key associated with this packet
            packet: The packet information to process
        """
        # If we don't have processors for this key, add standard ones
        if key not in self.processors:
            self.add_processor(key, CountMetricProcessor())
            self.add_processor(key, SizeMetricProcessor())
            self.add_processor(key, ProtocolMetricProcessor())
            self.add_processor(key, ErrorRateMetricProcessor())
            
        # Process the packet with each processor
        for processor in self.processors[key].values():
            processor.process(packet)
            
    def get_metric_value(self, key: str, metric_type: str) -> MetricValueT:
        """
        Get the current value of a specific metric for a key.
        
        Args:
            key: The message key
            metric_type: The type of metric to retrieve
            
        Returns:
            The current metric value, or None if not found
        """
        if key in self.processors and metric_type in self.processors[key]:
            return self.processors[key][metric_type].get_value()
            
        return None
        
    def get_all_metrics(self, key: str) -> Dict[str, MetricValueT]:
        """
        Get all metrics for a specific key.
        
        Args:
            key: The message key
            
        Returns:
            Dictionary of all metrics for the key
        """
        if key not in self.processors:
            return {}
            
        result = {}
        for metric_type, processor in self.processors[key].items():
            result[metric_type] = processor.get_value()
            
        return result
        
    def store_metrics(self, interval: int, label: str) -> None:
        """
        Store metrics in Redis for a given interval and label.
        
        Args:
            interval: The sampling interval in seconds
            label: The label for the interval ('s', 'm', 'h')
        """
        if not self.redis_client:
            logger.warning("Cannot store metrics: Redis client not set")
            return
            
        timestamp = int(time.time())
        timestamp = timestamp - (timestamp % interval)
        
        # Store metrics for each key
        for key, processors in self.processors.items():
            for metric_type, processor in processors.items():
                # Get the metric value
                value = processor.get_value()
                
                # Create a Redis key for this metric
                redis_key = f"{key}:{metric_type}:{label}"
                
                # Serialize the metric value
                serialized = processor.serialize(value)
                
                # Store as a time series
                self.redis_client.lpush(redis_key, f"[{timestamp}, {serialized}]")
                
                # Trim the list to a reasonable size
                self.redis_client.ltrim(redis_key, 0, 1000)
        
    def reset_metrics(self) -> None:
        """Reset all metric processors."""
        for processors in self.processors.values():
            for processor in processors.values():
                processor.reset()


def create_metric_processor(metric_type: str, **kwargs) -> MetricProcessor:
    """
    Factory function to create metric processors.
    
    Args:
        metric_type: Type of metric processor to create
        **kwargs: Additional arguments for the processor
        
    Returns:
        A new metric processor instance
    """
    if metric_type == MetricType.COUNT:
        return CountMetricProcessor()
    elif metric_type == MetricType.SIZE:
        return SizeMetricProcessor()
    elif metric_type == MetricType.PROTOCOL:
        return ProtocolMetricProcessor()
    elif metric_type == MetricType.ERROR_RATE:
        return ErrorRateMetricProcessor()
    elif metric_type == MetricType.RESPONSE_TIME:
        return ResponseTimeMetricProcessor()
    elif metric_type == MetricType.CONNECTION:
        return ConnectionMetricProcessor()
    elif metric_type == MetricType.SERVICE:
        service_name = kwargs.get("service_name", "unknown")
        metrics_of_interest = kwargs.get("metrics_of_interest", [])
        return ServiceMetricProcessor(service_name, metrics_of_interest)
    else:
        raise ValueError(f"Unknown metric type: {metric_type}")


def extract_bacnet_metrics(apdu) -> Dict[str, Any]:
    """
    Extract BACnet-specific metrics from an APDU.
    
    Args:
        apdu: The APDU to extract metrics from
        
    Returns:
        Dictionary of extracted metrics
    """
    metrics = {
        "protocol": "BACnet",
        "size": len(apdu.pduData) if hasattr(apdu, "pduData") else 0
    }
    
    # Extract error information
    if hasattr(apdu, "apduType") and apdu.apduType == 5:  # Error
        metrics["error"] = True
        
    # Extract service information if available
    if hasattr(apdu, "apduService"):
        metrics["service"] = str(apdu.apduService)
        
    return metrics


# Singleton instance
_metric_manager = None

def get_metric_manager(redis_client=None) -> MetricManager:
    """
    Get or create the singleton MetricManager instance.
    
    Args:
        redis_client: Redis client to use (optional)
        
    Returns:
        The MetricManager instance
    """
    global _metric_manager
    
    if _metric_manager is None:
        _metric_manager = MetricManager(redis_client)
    elif redis_client is not None:
        _metric_manager.set_redis_client(redis_client)
        
    return _metric_manager 