#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BACmon Alert Manager

This module provides a flexible alerting system for BACmon with support for:
1. Multiple notification channels (email, SMS, webhook, etc.)
2. Configurable alert severity levels
3. Rate-limiting for alerts to prevent notification storms
4. Alert acknowledgment and resolution tracking
5. Alert templates with variable substitution
6. Scheduled maintenance windows with suppressed alerting
"""

import os
import sys
import time
import json
import logging
import smtplib
import threading
import datetime
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional, Union, Set, Callable, Tuple, cast

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('alert_manager')

# Type aliases
AlertT = Dict[str, Any]
NotificationConfigT = Dict[str, Any]


class AlertLevel:
    """Alert severity levels with integer values for comparison"""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ALERT = 3
    CRITICAL = 4
    EMERGENCY = 5
    
    @staticmethod
    def to_string(level: int) -> str:
        """Convert numeric level to string representation"""
        levels = {
            AlertLevel.DEBUG: "debug",
            AlertLevel.INFO: "info",
            AlertLevel.WARNING: "warning",
            AlertLevel.ALERT: "alert",
            AlertLevel.CRITICAL: "critical",
            AlertLevel.EMERGENCY: "emergency"
        }
        return levels.get(level, "unknown")
    
    @staticmethod
    def from_string(level_str: str) -> int:
        """Convert string level to numeric representation"""
        levels = {
            "debug": AlertLevel.DEBUG,
            "info": AlertLevel.INFO,
            "warning": AlertLevel.WARNING,
            "alert": AlertLevel.ALERT,
            "critical": AlertLevel.CRITICAL,
            "emergency": AlertLevel.EMERGENCY
        }
        return levels.get(level_str.lower(), AlertLevel.INFO)


class Alert:
    """Represents a single alert in the system"""
    
    def __init__(self, 
                 key: str, 
                 message: str, 
                 level: int = AlertLevel.ALERT,
                 source: str = "system",
                 details: Optional[Dict[str, Any]] = None,
                 entity: Optional[str] = None):
        """
        Initialize a new alert.
        
        Args:
            key: Unique identifier for this type of alert
            message: Human-readable alert message
            level: Alert severity level
            source: Component that generated the alert
            details: Additional context information
            entity: Specific entity (device, service) affected
        """
        self.key = key
        self.message = message
        self.level = level
        self.source = source
        self.details = details or {}
        self.entity = entity
        
        # Metadata
        self.timestamp = int(time.time())
        self.uuid = f"{self.key}_{self.timestamp}_{hash(self.message) % 100000}"
        self.acknowledged = False
        self.resolved = False
        self.notifications_sent = 0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for storage"""
        return {
            "key": self.key,
            "message": self.message,
            "level": self.level,
            "level_str": AlertLevel.to_string(self.level),
            "source": self.source,
            "details": self.details,
            "entity": self.entity,
            "timestamp": self.timestamp,
            "uuid": self.uuid,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "notifications_sent": self.notifications_sent
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Create alert from dictionary"""
        alert = cls(
            key=data["key"],
            message=data["message"],
            level=data["level"],
            source=data["source"],
            details=data["details"],
            entity=data["entity"]
        )
        alert.timestamp = data["timestamp"]
        alert.uuid = data["uuid"]
        alert.acknowledged = data["acknowledged"]
        alert.resolved = data["resolved"]
        alert.notifications_sent = data["notifications_sent"]
        return alert
    
    def acknowledge(self) -> None:
        """Mark alert as acknowledged"""
        self.acknowledged = True
    
    def resolve(self) -> None:
        """Mark alert as resolved"""
        self.resolved = True


class MaintenanceWindow:
    """Represents a time period when alerts should be suppressed"""
    
    def __init__(self, 
                 name: str,
                 start_time: int,
                 end_time: int,
                 entity_patterns: Optional[List[str]] = None,
                 key_patterns: Optional[List[str]] = None):
        """
        Initialize a maintenance window.
        
        Args:
            name: Human-readable name for this maintenance window
            start_time: Unix timestamp when window starts
            end_time: Unix timestamp when window ends
            entity_patterns: List of entity patterns to suppress
            key_patterns: List of alert key patterns to suppress
        """
        self.name = name
        self.start_time = start_time
        self.end_time = end_time
        self.entity_patterns = entity_patterns or []
        self.key_patterns = key_patterns or []
        
    def is_active(self) -> bool:
        """Check if the maintenance window is currently active"""
        now = int(time.time())
        return self.start_time <= now <= self.end_time
    
    def matches_alert(self, alert: Alert) -> bool:
        """Check if an alert matches this maintenance window's criteria"""
        # If window isn't active, it doesn't match
        if not self.is_active():
            return False
        
        # If no patterns specified, match all alerts
        if not self.entity_patterns and not self.key_patterns:
            return True
        
        # Check entity patterns
        if self.entity_patterns and alert.entity:
            for pattern in self.entity_patterns:
                if pattern in alert.entity:
                    return True
        
        # Check key patterns
        if self.key_patterns:
            for pattern in self.key_patterns:
                if pattern in alert.key:
                    return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert maintenance window to dictionary for storage"""
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "entity_patterns": self.entity_patterns,
            "key_patterns": self.key_patterns
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MaintenanceWindow':
        """Create maintenance window from dictionary"""
        return cls(
            name=data["name"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            entity_patterns=data["entity_patterns"],
            key_patterns=data["key_patterns"]
        )


class NotificationChannel:
    """Base class for alert notification channels"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize notification channel.
        
        Args:
            name: Channel identifier
            config: Channel configuration parameters
        """
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", True)
        self.min_level = AlertLevel.from_string(config.get("min_level", "alert"))
        
    def can_notify(self, alert: Alert) -> bool:
        """Check if this channel should send notification for this alert"""
        if not self.enabled:
            return False
        
        return alert.level >= self.min_level
    
    def send(self, alert: Alert) -> bool:
        """
        Send alert notification via this channel.
        
        Args:
            alert: The alert to send
            
        Returns:
            Success status
        """
        raise NotImplementedError("Subclasses must implement send()")


class EmailChannel(NotificationChannel):
    """Email notification channel"""
    
    def send(self, alert: Alert) -> bool:
        """Send alert via email"""
        try:
            # Get email configuration
            smtp_server = self.config.get("smtp_server", "localhost")
            smtp_port = self.config.get("smtp_port", 25)
            use_tls = self.config.get("use_tls", False)
            username = self.config.get("username")
            password = self.config.get("password")
            from_addr = self.config.get("from_address", "bacmon@localhost")
            to_addrs = self.config.get("to_addresses", [])
            
            if not to_addrs:
                logger.error("No recipient addresses configured for email notification")
                return False
            
            # Create message
            level_str = AlertLevel.to_string(alert.level).upper()
            subject = f"[{level_str}] BACmon Alert: {alert.key}"
            
            msg = MIMEMultipart()
            msg["From"] = from_addr
            msg["To"] = ", ".join(to_addrs)
            msg["Subject"] = subject
            
            # Create email body
            body = f"""
            BACmon Alert Notification
            -------------------------
            
            Alert: {alert.message}
            Severity: {level_str}
            Time: {datetime.datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S')}
            Source: {alert.source}
            Entity: {alert.entity or 'N/A'}
            
            Details:
            {json.dumps(alert.details, indent=2) if alert.details else "No additional details"}
            
            This is an automated message from BACmon.
            """
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if use_tls:
                    server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
            
            logger.info(f"Sent email notification for alert {alert.key} to {to_addrs}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False


class WebhookChannel(NotificationChannel):
    """Webhook notification channel"""
    
    def send(self, alert: Alert) -> bool:
        """Send alert via webhook"""
        try:
            # Get webhook configuration
            webhook_url = self.config.get("url")
            headers = self.config.get("headers", {})
            method = self.config.get("method", "POST").upper()
            timeout = self.config.get("timeout", 10)
            
            if not webhook_url:
                logger.error("No URL configured for webhook notification")
                return False
            
            # Prepare payload
            payload = alert.to_dict()
            
            # Send request
            response = requests.request(
                method=method,
                url=webhook_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            success = 200 <= response.status_code < 300
            if success:
                logger.info(f"Sent webhook notification for alert {alert.key}, status: {response.status_code}")
            else:
                logger.error(f"Webhook notification failed: {response.status_code} {response.text}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False


class LogFileChannel(NotificationChannel):
    """Log file notification channel"""
    
    def send(self, alert: Alert) -> bool:
        """Send alert to log file"""
        try:
            # Get log file configuration
            log_file = self.config.get("file")
            
            if not log_file:
                logger.error("No file path configured for log file notification")
                return False
            
            # Format log message
            level_str = AlertLevel.to_string(alert.level).upper()
            timestamp = datetime.datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            log_message = f"[{timestamp}] [{level_str}] {alert.key}: {alert.message}"
            
            # Add details if available
            if alert.details:
                details_str = json.dumps(alert.details)
                log_message += f" | Details: {details_str}"
            
            # Write to log file
            with open(log_file, "a") as f:
                f.write(log_message + "\n")
            
            logger.info(f"Wrote alert {alert.key} to log file {log_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")
            return False


class AlertManager:
    """
    Central manager for handling alerts and notifications.
    
    This class manages alert lifecycle, notification dispatch, and provides
    interfaces for alert acknowledgment and resolution.
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize the alert manager.
        
        Args:
            redis_client: Redis client instance for persistence
        """
        self.redis_client = redis_client
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self.maintenance_windows: List[MaintenanceWindow] = []
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self.config_loaded = False
        
        # Alert buffers
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history = 1000
        
        # Background thread for notification dispatch
        self.notification_thread = None
        self.notification_queue: List[Alert] = []
        self.notification_lock = threading.Lock()
        self.running = False
        
    def load_config(self, config_file: Optional[str] = None) -> None:
        """
        Load configuration from file or environment.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        try:
            # Default configuration
            config = {
                "channels": {
                    "email": {
                        "type": "email",
                        "enabled": False,
                        "min_level": "alert",
                        "smtp_server": "localhost",
                        "smtp_port": 25,
                        "use_tls": False,
                        "from_address": "bacmon@localhost",
                        "to_addresses": []
                    },
                    "webhook": {
                        "type": "webhook",
                        "enabled": False,
                        "min_level": "alert",
                        "url": "",
                        "method": "POST",
                        "headers": {}
                    },
                    "logfile": {
                        "type": "logfile",
                        "enabled": True,
                        "min_level": "warning",
                        "file": "logs/alerts.log"
                    }
                },
                "rate_limits": {
                    "default": {
                        "max_alerts_per_hour": 10,
                        "cooldown_period": 300
                    }
                },
                "maintenance": []
            }
            
            # Load from file if provided
            if config_file and os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    # Merge configurations
                    self._merge_config(config, file_config)
            
            # Initialize notification channels
            for name, channel_config in config["channels"].items():
                channel_type = channel_config.get("type", "logfile")
                
                if channel_type == "email":
                    self.notification_channels[name] = EmailChannel(name, channel_config)
                elif channel_type == "webhook":
                    self.notification_channels[name] = WebhookChannel(name, channel_config)
                elif channel_type == "logfile":
                    self.notification_channels[name] = LogFileChannel(name, channel_config)
                else:
                    logger.warning(f"Unknown notification channel type: {channel_type}")
            
            # Initialize rate limits
            self.rate_limits = config["rate_limits"]
            
            # Initialize maintenance windows
            for window_config in config["maintenance"]:
                window = MaintenanceWindow(
                    name=window_config.get("name", "Maintenance"),
                    start_time=window_config.get("start_time", 0),
                    end_time=window_config.get("end_time", 0),
                    entity_patterns=window_config.get("entity_patterns", []),
                    key_patterns=window_config.get("key_patterns", [])
                )
                self.maintenance_windows.append(window)
            
            self.config_loaded = True
            logger.info("Alert manager configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load alert manager configuration: {e}")
            # Use default minimal configuration
            self.notification_channels["default"] = LogFileChannel("default", {
                "type": "logfile",
                "enabled": True,
                "min_level": "warning",
                "file": "logs/alerts.log"
            })
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge configuration dictionaries.
        
        Args:
            base: Base configuration
            override: Configuration to override with
            
        Returns:
            Merged configuration
        """
        for key, value in override.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
        return base
    
    def start(self) -> None:
        """Start the alert manager"""
        if not self.config_loaded:
            self.load_config()
        
        # Load existing alerts from Redis if available
        self._load_from_redis()
        
        # Start notification thread
        self.running = True
        self.notification_thread = threading.Thread(
            target=self._notification_worker,
            daemon=True
        )
        self.notification_thread.start()
        
        logger.info("Alert manager started")
    
    def stop(self) -> None:
        """Stop the alert manager"""
        self.running = False
        if self.notification_thread:
            self.notification_thread.join(timeout=5.0)
        logger.info("Alert manager stopped")
    
    def create_alert(self, 
                    key: str, 
                    message: str, 
                    level: Union[int, str] = AlertLevel.ALERT,
                    source: str = "system",
                    details: Optional[Dict[str, Any]] = None,
                    entity: Optional[str] = None) -> Alert:
        """
        Create a new alert.
        
        Args:
            key: Unique identifier for this type of alert
            message: Human-readable alert message
            level: Alert severity level (int or string)
            source: Component that generated the alert
            details: Additional context information
            entity: Specific entity affected
            
        Returns:
            Created alert
        """
        # Convert string level to int if needed
        if isinstance(level, str):
            level = AlertLevel.from_string(level)
        
        alert = Alert(
            key=key,
            message=message,
            level=level,
            source=source,
            details=details or {},
            entity=entity
        )
        
        # Process the alert
        self._process_alert(alert)
        
        return alert
    
    def _process_alert(self, alert: Alert) -> None:
        """
        Process a new alert.
        
        Args:
            alert: The alert to process
        """
        # Check if alert is in maintenance window
        for window in self.maintenance_windows:
            if window.matches_alert(alert):
                logger.info(f"Alert {alert.key} suppressed due to maintenance window: {window.name}")
                return
        
        # Check rate limiting
        if self._is_rate_limited(alert):
            logger.info(f"Alert {alert.key} suppressed due to rate limiting")
            return
        
        # Store in active alerts
        self.active_alerts[alert.uuid] = alert
        
        # Store in Redis if available
        self._save_to_redis(alert)
        
        # Queue for notification
        with self.notification_lock:
            self.notification_queue.append(alert)
        
        # Store legacy format in Redis sets for backward compatibility
        if self.redis_client:
            level_str = AlertLevel.to_string(alert.level)
            redis_key = f"{level_str}-messages"
            
            # Format message in legacy format
            if alert.entity:
                legacy_msg = f"{alert.entity}/{alert.key}/{alert.message}"
            else:
                legacy_msg = f"-/{alert.key}/{alert.message}"
            
            # Add to appropriate Redis set
            self.redis_client.sadd(redis_key, legacy_msg)
    
    def _is_rate_limited(self, alert: Alert) -> bool:
        """
        Check if an alert should be rate-limited.
        
        Args:
            alert: The alert to check
            
        Returns:
            True if alert should be suppressed, False otherwise
        """
        # Get rate limit config for this alert type
        rate_limit = self.rate_limits.get(alert.key, self.rate_limits.get("default", {}))
        
        if not rate_limit:
            return False
        
        max_per_hour = rate_limit.get("max_alerts_per_hour", 10)
        cooldown = rate_limit.get("cooldown_period", 300)  # seconds
        
        # Check if a similar alert was recently processed
        for existing_alert in self.alert_history:
            if existing_alert.key == alert.key and existing_alert.entity == alert.entity:
                # Check cooldown period
                if alert.timestamp - existing_alert.timestamp < cooldown:
                    return True
                
                # Check hourly rate
                hour_ago = alert.timestamp - 3600
                count = sum(1 for a in self.alert_history 
                           if a.key == alert.key 
                           and a.timestamp >= hour_ago)
                
                if count >= max_per_hour:
                    return True
        
        return False
    
    def _notification_worker(self) -> None:
        """Background worker to send notifications"""
        while self.running:
            # Check for queued alerts
            alerts_to_process = []
            with self.notification_lock:
                if self.notification_queue:
                    alerts_to_process = self.notification_queue.copy()
                    self.notification_queue.clear()
            
            # Process queued alerts
            for alert in alerts_to_process:
                # Send notifications via all applicable channels
                for channel in self.notification_channels.values():
                    if channel.can_notify(alert):
                        try:
                            success = channel.send(alert)
                            if success:
                                alert.notifications_sent += 1
                        except Exception as e:
                            logger.error(f"Error sending notification via {channel.name}: {e}")
                
                # Update alert in storage
                if self.redis_client:
                    self._save_to_redis(alert)
            
            # Sleep before checking again
            time.sleep(1.0)
    
    def acknowledge_alert(self, uuid: str) -> bool:
        """
        Acknowledge an active alert.
        
        Args:
            uuid: Alert UUID to acknowledge
            
        Returns:
            Success status
        """
        if uuid in self.active_alerts:
            alert = self.active_alerts[uuid]
            alert.acknowledge()
            self._save_to_redis(alert)
            return True
        return False
    
    def resolve_alert(self, uuid: str) -> bool:
        """
        Resolve an active alert.
        
        Args:
            uuid: Alert UUID to resolve
            
        Returns:
            Success status
        """
        if uuid in self.active_alerts:
            alert = self.active_alerts[uuid]
            alert.resolve()
            
            # Move to history
            self.alert_history.append(alert)
            while len(self.alert_history) > self.max_history:
                self.alert_history.pop(0)
            
            # Remove from active
            del self.active_alerts[uuid]
            
            # Update in Redis
            self._save_to_redis(alert)
            return True
        return False
    
    def get_active_alerts(self, min_level: int = AlertLevel.WARNING) -> List[Alert]:
        """
        Get list of active alerts at or above the specified level.
        
        Args:
            min_level: Minimum alert level to include
            
        Returns:
            List of active alerts
        """
        return [alert for alert in self.active_alerts.values() 
                if alert.level >= min_level and not alert.resolved]
    
    def get_alert_history(self, 
                         min_level: int = AlertLevel.WARNING,
                         max_results: int = 100) -> List[Alert]:
        """
        Get alert history at or above the specified level.
        
        Args:
            min_level: Minimum alert level to include
            max_results: Maximum number of results to return
            
        Returns:
            List of historical alerts
        """
        # Filter and sort alerts by timestamp (newest first)
        filtered = [alert for alert in self.alert_history if alert.level >= min_level]
        sorted_alerts = sorted(filtered, key=lambda a: a.timestamp, reverse=True)
        
        # Limit results
        return sorted_alerts[:max_results]
    
    def add_maintenance_window(self, window: MaintenanceWindow) -> None:
        """
        Add a new maintenance window.
        
        Args:
            window: Maintenance window to add
        """
        self.maintenance_windows.append(window)
        self._save_maintenance_windows()
    
    def remove_maintenance_window(self, name: str) -> bool:
        """
        Remove a maintenance window by name.
        
        Args:
            name: Name of window to remove
            
        Returns:
            Success status
        """
        for i, window in enumerate(self.maintenance_windows):
            if window.name == name:
                self.maintenance_windows.pop(i)
                self._save_maintenance_windows()
                return True
        return False
    
    def _save_to_redis(self, alert: Alert) -> None:
        """
        Save alert to Redis.
        
        Args:
            alert: Alert to save
        """
        if not self.redis_client:
            return
        
        try:
            # Save to appropriate collection based on status
            if alert.resolved:
                # Save to history
                history_key = "alert_history"
                alert_data = json.dumps(alert.to_dict())
                self.redis_client.lpush(history_key, alert_data)
                self.redis_client.ltrim(history_key, 0, self.max_history - 1)
                
                # Remove from active alerts
                self.redis_client.hdel("active_alerts", alert.uuid)
            else:
                # Save to active alerts
                alert_data = json.dumps(alert.to_dict())
                self.redis_client.hset("active_alerts", alert.uuid, alert_data)
        except Exception as e:
            logger.error(f"Failed to save alert to Redis: {e}")
    
    def _save_maintenance_windows(self) -> None:
        """Save maintenance windows to Redis"""
        if not self.redis_client:
            return
        
        try:
            # Convert windows to serializable format
            windows_data = [window.to_dict() for window in self.maintenance_windows]
            self.redis_client.set("maintenance_windows", json.dumps(windows_data))
        except Exception as e:
            logger.error(f"Failed to save maintenance windows to Redis: {e}")
    
    def _load_from_redis(self) -> None:
        """Load alerts and maintenance windows from Redis"""
        if not self.redis_client:
            return
        
        try:
            # Load active alerts
            active_data = self.redis_client.hgetall("active_alerts")
            if active_data:
                for uuid, data in active_data.items():
                    try:
                        alert_dict = json.loads(data)
                        alert = Alert.from_dict(alert_dict)
                        self.active_alerts[alert.uuid] = alert
                    except Exception as e:
                        logger.error(f"Failed to load active alert: {e}")
            
            # Load alert history
            history_data = self.redis_client.lrange("alert_history", 0, self.max_history - 1)
            if history_data:
                for data in history_data:
                    try:
                        alert_dict = json.loads(data)
                        alert = Alert.from_dict(alert_dict)
                        self.alert_history.append(alert)
                    except Exception as e:
                        logger.error(f"Failed to load alert history: {e}")
            
            # Load maintenance windows
            windows_data = self.redis_client.get("maintenance_windows")
            if windows_data:
                try:
                    windows = json.loads(windows_data)
                    self.maintenance_windows = [MaintenanceWindow.from_dict(w) for w in windows]
                except Exception as e:
                    logger.error(f"Failed to load maintenance windows: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to load data from Redis: {e}")


# Initialize a global alert manager instance
_alert_manager: Optional[AlertManager] = None

def get_alert_manager(redis_client=None) -> AlertManager:
    """
    Get or create the global alert manager instance.
    
    Args:
        redis_client: Redis client to use for persistence
        
    Returns:
        Alert manager instance
    """
    global _alert_manager
    
    if _alert_manager is None:
        _alert_manager = AlertManager(redis_client)
        _alert_manager.start()
    
    return _alert_manager

def create_alert(key: str, 
                message: str, 
                level: Union[int, str] = AlertLevel.ALERT,
                source: str = "system",
                details: Optional[Dict[str, Any]] = None,
                entity: Optional[str] = None) -> Alert:
    """
    Create and process a new alert.
    
    Args:
        key: Unique identifier for this type of alert
        message: Human-readable alert message
        level: Alert severity level
        source: Component that generated the alert
        details: Additional context information
        entity: Specific entity affected
        
    Returns:
        Created alert
    """
    manager = get_alert_manager()
    return manager.create_alert(key, message, level, source, details, entity)

def acknowledge_alert(uuid: str) -> bool:
    """
    Acknowledge an active alert.
    
    Args:
        uuid: Alert UUID to acknowledge
        
    Returns:
        Success status
    """
    manager = get_alert_manager()
    return manager.acknowledge_alert(uuid)

def resolve_alert(uuid: str) -> bool:
    """
    Resolve an active alert.
    
    Args:
        uuid: Alert UUID to resolve
        
    Returns:
        Success status
    """
    manager = get_alert_manager()
    return manager.resolve_alert(uuid)

def create_maintenance_window(name: str,
                             start_time: int,
                             end_time: int,
                             entity_patterns: Optional[List[str]] = None,
                             key_patterns: Optional[List[str]] = None) -> MaintenanceWindow:
    """
    Create and register a new maintenance window.
    
    Args:
        name: Human-readable name
        start_time: Unix timestamp when window starts
        end_time: Unix timestamp when window ends
        entity_patterns: List of entity patterns to suppress
        key_patterns: List of alert key patterns to suppress
        
    Returns:
        Created maintenance window
    """
    window = MaintenanceWindow(
        name=name,
        start_time=start_time,
        end_time=end_time,
        entity_patterns=entity_patterns,
        key_patterns=key_patterns
    )
    
    manager = get_alert_manager()
    manager.add_maintenance_window(window)
    
    return window

def get_active_alerts(min_level: Union[int, str] = AlertLevel.WARNING) -> List[Alert]:
    """
    Get list of active alerts.
    
    Args:
        min_level: Minimum alert level to include
        
    Returns:
        List of active alerts
    """
    # Convert string level to int if needed
    if isinstance(min_level, str):
        min_level = AlertLevel.from_string(min_level)
        
    manager = get_alert_manager()
    return manager.get_active_alerts(min_level)

def get_alert_history(min_level: Union[int, str] = AlertLevel.WARNING,
                     max_results: int = 100) -> List[Alert]:
    """
    Get alert history.
    
    Args:
        min_level: Minimum alert level to include
        max_results: Maximum number of results
        
    Returns:
        List of historical alerts
    """
    # Convert string level to int if needed
    if isinstance(min_level, str):
        min_level = AlertLevel.from_string(min_level)
        
    manager = get_alert_manager()
    return manager.get_alert_history(min_level, max_results) 