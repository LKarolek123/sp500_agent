#!/usr/bin/env python3
"""Wrapper script to run dynamic TP/SL test from workspace root."""

import sys
import os

# Set up path
sys.path.insert(0, os.getcwd())

# Now import and run
from src.models import hybrid_ma_ml_filter_dynamic_tp_sl
