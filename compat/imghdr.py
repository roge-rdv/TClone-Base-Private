"""
Replacement for the removed imghdr module in Python 3.13+
This provides basic image type detection functionality needed by Telethon.
"""

import struct
import os

def what(file, h=None):
    """
    Simplified version of imghdr.what() to provide compatibility with Python 3.13+
    Determines the type of image contained in a file or provided bytes.
    
    Args:
        file: A filename (string), a file object, or bytes.
        h: Bytes to test (if file is a filename or file object, h is ignored).
        
    Returns:
        A string describing the image type if recognized, or None if not recognized.
    """
    if h is None:
        if isinstance(file, bytes):
            h = file[:32]
        else:
            if hasattr(file, 'read'):
                # It's a file-like object
                pos = file.tell()
                h = file.read(32)
                file.seek(pos)
            else:
                # It's a filename string
                with open(file, 'rb') as f:
                    h = f.read(32)
    
    # JPEG
    if h[0:2] == b'\xff\xd8':
        return 'jpeg'
    
    # PNG
    if h[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    
    # GIF
    if h[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    
    # TIFF
    if h[:2] in (b'MM', b'II'):
        if h[2:4] == b'\x00\x2a':
            return 'tiff'
    
    # BMP
    if h[:2] == b'BM':
        return 'bmp'
    
    # WEBP
    if h[:4] == b'RIFF' and h[8:12] == b'WEBP':
        return 'webp'
    
    return None

# Define test functions for each image type format
tests = []

def test_jpeg(h, f):
    """Test for JPEG data."""
    if h[0:2] == b'\xff\xd8':
        return 'jpeg'

tests.append(test_jpeg)

def test_png(h, f):
    """Test for PNG data."""
    if h[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'

tests.append(test_png)

def test_gif(h, f):
    """Test for GIF data."""
    if h[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'

tests.append(test_gif)

def test_tiff(h, f):
    """Test for TIFF data."""
    if h[:2] in (b'MM', b'II'):
        if h[2:4] == b'\x00\x2a':
            return 'tiff'

tests.append(test_tiff)

def test_bmp(h, f):
    """Test for BMP data."""
    if h[:2] == b'BM':
        return 'bmp'

tests.append(test_bmp)

def test_webp(h, f):
    """Test for WebP data."""
    if h[:4] == b'RIFF' and h[8:12] == b'WEBP':
        return 'webp'

tests.append(test_webp)
