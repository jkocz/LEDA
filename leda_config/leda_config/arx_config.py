"""
arx_config.py
-------------

ARX configuration file for LEDA-OVRO
"""
import os

## ARX IP ADDRESSES
arx1_txAddr = ('192.168.25.2', 1738)
arx2_txAddr = ('192.168.25.4', 1738)
arx3_txAddr = ('192.168.25.5', 1738)
arx4_txAddr = ('192.168.25.6', 1738)
rx_addr     = ('192.100.16.226', 1739)

## DIRECTORY SETUP
arx_report_dir = '/home/leda/observing_logs/arx_reports'
arx_config_dir = '/home/leda/leda_dev/control/arx_control/config'
default_config = os.path.join(arx_config_dir, 'config_14_14_on')

## ARX AUTO CALIBRATION DEFAULTS
target_rms    = 32          # Target RMS
arx_cal_iters = 3           # NUmber of times to iterate on calibration
disable_bad   = False       # Disable stands identified as bad
snap_iters    = 3           # Number of ADC RMS snaps in calibration
