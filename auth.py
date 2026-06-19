"""
Token-based authentication middleware for MeetAssistant admin endpoints.

Usage:
    1. Set ADMIN_TOKEN environment variable
    2. Apply @require_token decorator to protected endpoints
    3. Clients send token via Authorization header or query parameter
"""

import hashlib
import hmac
import os
import secrets
from functools import wraps
from flask import request, jsonify

# Default token for development (auto-generated)
_dev_token = None
_token_hash = None


def _hash_token(token: str) -> str:
    """Hash token using SHA-256 for secure storage."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def bootstrap_admin_token():
    """
    Initialize admin token from environment or generate one for development.
    Call this once during app startup.

    Returns:
        str: The plaintext token (only shown once in dev mode)
    """
    global _dev_token, _token_hash

    token = os.environ.get('ADMIN_TOKEN', '').strip()

    if token:
        # Production: use provided token
        _token_hash = _hash_token(token)
        return None  # Don't return production token
    else:
        # Development: generate random token
        _dev_token = secrets.token_urlsafe(32)
        _token_hash = _hash_token(_dev_token)
        return _dev_token


def verify_token(provided_token: str) -> bool:
    """
    Verify a provided token against the stored hash.

    Args:
        provided_token: The token to verify

    Returns:
        bool: True if token is valid
    """
    if not provided_token or not _token_hash:
        return False

    provided_hash = _hash_token(provided_token)
    return hmac.compare_digest(provided_hash, _token_hash)


def require_token(f):
    """
    Decorator to require valid token for endpoint access.

    Token can be provided via:
    - Authorization header: "Bearer <token>"
    - Query parameter: ?token=<token>
    - Form field: token=<token>
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Check Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()

        # Check query parameter
        if not token:
            token = request.args.get('token', '').strip()

        # Check form data
        if not token:
            token = request.form.get('token', '').strip()

        # Check JSON body
        if not token and request.is_json:
            data = request.get_json(silent=True) or {}
            token = data.get('token', '').strip()

        if not token or not verify_token(token):
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'Valid admin token required. Provide via Authorization header, query parameter, or request body.'
            }), 401

        return f(*args, **kwargs)

    return decorated


