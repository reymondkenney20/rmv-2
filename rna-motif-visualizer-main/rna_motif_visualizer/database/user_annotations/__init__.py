"""
User Annotations Module

Provides infrastructure for loading user-uploaded motif annotation files
from external tools like FR3D and RNAMotifScan.
"""

from .converters import FR3DConverter, RNAMotifScanConverter, MotifInstanceSimple
from .user_provider import UserAnnotationProvider

__all__ = [
    'FR3DConverter',
    'RNAMotifScanConverter',
    'MotifInstanceSimple',
    'UserAnnotationProvider',
]
