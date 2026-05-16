"""
MAGI Meta Layer — Web dashboard backend.
Entry point: python -m magi --web
"""
from magi.meta.server import create_app

__all__ = ["create_app"]
