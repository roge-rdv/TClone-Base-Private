"""Compatibility fixes for various Python versions."""
import sys

# If we're on Python 3.13+, patch sys.modules to include our imghdr module
if sys.version_info >= (3, 13):
    import compat.imghdr
    sys.modules['imghdr'] = compat.imghdr
