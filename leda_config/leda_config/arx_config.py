"""
arx_config.py
-------------

ARX configuration file for LEDA-OVRO
"""

## ARX IP ADDRESSES
arx1_txAddr = ('192.168.25.2', 1738)
arx2_txAddr = ('192.168.25.4', 1738)
arx3_txAddr = ('192.168.25.5', 1738)
arx4_txAddr = ('192.168.25.6', 1738)
rx_addr     = ('192.100.16.226', 1739)

## DIRECTORY SETUP
arx_report_dir = '/home/leda/observing_logs/arx_reports'
default_config  = '/home/leda/leda_dev/control/arx_control/config/config_10db_10db_on'

## ARX AUTO CALIBRATION DEFAULTS
target_rms    = 32
arx_cal_iters = 3
disable_bad   = False