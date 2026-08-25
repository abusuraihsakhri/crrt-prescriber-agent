#!/usr/bin/env python3
"""
CLI for CRRT Prescriber Calculator.
Delegates to crrt_mind.py for all calculations.
"""
import sys
from crrt_mind import main

if __name__ == "__main__":
    sys.exit(main())
