#!/usr/bin/env python3
"""
Convenience script to run the Bodet capture server.
This is a simple wrapper around src/bodet_capture.py
"""

import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

if __name__ == '__main__':
    from bodet_capture import main
    main()
