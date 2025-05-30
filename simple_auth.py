#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple Authentication Module for BACmon
Provides basic API key and session authentication for testing purposes.
"""

import os
import time
import hashlib
import secrets
import functools
from typing import Dict, Optional, Set, List, Any, Callable
from datetime import datetime, timedelta

# Simple in-memory storage for testing (use Redis in production)
_sessions: Dict[str, Dict[str, Any]] = {}
_api_keys: Dict[str, Dict[str, Any]] = {}

# Default configuration
DEFAULT_SESSION_TIMEOUT = 3600  # 1 hour
DEFAULT_API_KEYS = {
    'test_key_123': {
        'name': 'Test Key',
        'permissions': ['read', 'write'],
        'created': time.time()
    },
    'admin_key_456': {
        'name': 'Admin Key', 
        'permissions': ['read', 'write', 'admin'],
        'created': time.time()
    }
}

class SimpleAuth:
    """Simple authentication manager for BACmon testing."""
    
    def __init__(self, redis_client=None):
        """Initialize authentication manager."""
        self.redis_client = redis_client
        self.session_timeout = int(os.getenv('AUTH_SESSION_TIMEOUT', DEFAULT_SESSION_TIMEOUT))
        self.enabled = os.getenv('AUTH_ENABLED', 'true').lower() == 'true'
        
        # Load API keys from environment or defaults
        self._load_api_keys()
    
    def _load_api_keys(self):
        """Load API keys from environment or use defaults."""
        global _api_keys
        
        # Check for environment variable with API keys (JSON format)
        env_keys = os.getenv('AUTH_API_KEYS')
        if env_keys:
            try:
                import json
                _api_keys.update(json.loads(env_keys))
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Use defaults if no custom keys provided
        if not _api_keys:
            _api_keys.update(DEFAULT_API_KEYS)
    
    def create_session(self, user_id: str, permissions: List[str] = None) -> str:
        """Create a new session and return session token."""
        session_token = secrets.token_urlsafe(32)
        session_data = {
            'user_id': user_id,
            'permissions': permissions or ['read'],
            'created': time.time(),
            'last_access': time.time()
        }
        
        if self.redis_client:
            # Store in Redis with expiration
            try:
                import json
                self.redis_client.set(
                    f"session:{session_token}", 
                    json.dumps(session_data), 
                    ex=self.session_timeout
                )
            except Exception:
                # Fall back to memory storage
                _sessions[session_token] = session_data
        else:
            # Store in memory
            _sessions[session_token] = session_data
        
        return session_token
    
    def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Validate session token and return session data."""
        if not session_token:
            return None
        
        session_data = None
        
        if self.redis_client:
            try:
                import json
                data = self.redis_client.get(f"session:{session_token}")
                if data:
                    session_data = json.loads(data)
            except Exception:
                pass
        
        # Fall back to memory storage
        if not session_data and session_token in _sessions:
            session_data = _sessions[session_token]
        
        if not session_data:
            return None
        
        # Check if session has expired
        if time.time() - session_data['last_access'] > self.session_timeout:
            self.invalidate_session(session_token)
            return None
        
        # Update last access time
        session_data['last_access'] = time.time()
        
        if self.redis_client:
            try:
                import json
                self.redis_client.set(
                    f"session:{session_token}", 
                    json.dumps(session_data), 
                    ex=self.session_timeout
                )
            except Exception:
                _sessions[session_token] = session_data
        else:
            _sessions[session_token] = session_data
        
        return session_data
    
    def invalidate_session(self, session_token: str):
        """Invalidate a session."""
        if self.redis_client:
            try:
                self.redis_client.delete(f"session:{session_token}")
            except Exception:
                pass
        
        if session_token in _sessions:
            del _sessions[session_token]
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return key data."""
        if not api_key or api_key not in _api_keys:
            return None
        
        return _api_keys[api_key]
    
    def has_permission(self, permissions: List[str], required_permission: str) -> bool:
        """Check if user has required permission."""
        return required_permission in permissions or 'admin' in permissions
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions from memory storage."""
        global _sessions
        current_time = time.time()
        expired = [
            token for token, data in _sessions.items()
            if current_time - data['last_access'] > self.session_timeout
        ]
        
        for token in expired:
            del _sessions[token]

# Global auth instance
_auth_instance: Optional[SimpleAuth] = None

def get_auth_manager(redis_client=None) -> SimpleAuth:
    """Get or create global auth manager instance."""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = SimpleAuth(redis_client)
    return _auth_instance

def require_auth(permission: str = 'read'):
    """Decorator to require authentication for API endpoints."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            auth = get_auth_manager()
            
            # Skip auth if disabled
            if not auth.enabled:
                return func(*args, **kwargs)
            
            import bottle
            
            # Check for API key in header
            api_key = bottle.request.get_header('X-API-Key')
            if api_key:
                key_data = auth.validate_api_key(api_key)
                if key_data and auth.has_permission(key_data['permissions'], permission):
                    # Add auth info to request for use in endpoint
                    bottle.request.auth = {
                        'type': 'api_key',
                        'permissions': key_data['permissions'],
                        'name': key_data['name']
                    }
                    return func(*args, **kwargs)
            
            # Check for session token in cookie
            session_token = bottle.request.get_cookie('session_token')
            if session_token:
                session_data = auth.validate_session(session_token)
                if session_data and auth.has_permission(session_data['permissions'], permission):
                    # Add auth info to request
                    bottle.request.auth = {
                        'type': 'session',
                        'permissions': session_data['permissions'],
                        'user_id': session_data['user_id']
                    }
                    return func(*args, **kwargs)
            
            # Authentication failed
            bottle.response.status = 401
            return {
                'status': 'error',
                'code': 401,
                'error': 'Authentication required',
                'timestamp': int(time.time())
            }
        
        return wrapper
    return decorator

def require_admin():
    """Decorator to require admin permission."""
    return require_auth('admin')

def login_required(func: Callable) -> Callable:
    """Decorator for web pages that require login."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        auth = get_auth_manager()
        
        # Skip auth if disabled
        if not auth.enabled:
            return func(*args, **kwargs)
        
        import bottle
        
        # Check for session token
        session_token = bottle.request.get_cookie('session_token')
        if session_token:
            session_data = auth.validate_session(session_token)
            if session_data:
                bottle.request.auth = {
                    'type': 'session',
                    'permissions': session_data['permissions'],
                    'user_id': session_data['user_id']
                }
                return func(*args, **kwargs)
        
        # Redirect to login page
        bottle.redirect('/login')
    
    return wrapper

def create_test_user_session() -> str:
    """Create a test user session for development/testing."""
    auth = get_auth_manager()
    return auth.create_session('test_user', ['read', 'write'])

def get_api_keys_info() -> Dict[str, Dict[str, Any]]:
    """Get information about available API keys (for setup/testing)."""
    return {
        key: {
            'name': data['name'],
            'permissions': data['permissions'],
            'created': datetime.fromtimestamp(data['created']).isoformat()
        }
        for key, data in _api_keys.items()
    } 