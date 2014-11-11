#!/usr/bin/env python
"""
run_antenna_report.py
---------------------

Run an antenna report and save output to file. This gets a bandpass
for all 512 signal paths, and saves it to a hickle file.
"""

import os
from datetime import datetime
from prog_all_spectrometer import *
import hickle as hkl

sp = snap_spec_all()

now = datetime.now()
now_str = now.strftime("ant-report-%Y-%m-%d_%H-%M-%S.hkl")
hkl.dump(sp, os.path.join(config.ant_report_dir, now_str))


