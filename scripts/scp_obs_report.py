#!/usr/bin/env python
"""
scp_obs_report.py
-----------------

Copy observation reports over from ledaovro. This script should be run on
your local computer, not remotely.
"""

import os, system

if __name__ == '__main__':
    is not os.path.exists('report'):
        os.mkdir('report')

    ledascp = 'leda@ledaovro.lwa.ovro.caltech.edu:observing_logs'
    os.system('scp %s/ant_reports/ant_report.pdf report' % ledascp)
    os.system('scp %s/arx_reports/arx_report.pdf report' % ledascp)
    os.system('scp %s/outrigger_reports/outrigger_reports.pdf report' % ledascp)

