#!/usr/bin/env python
#
# Filename: server_leda_nexus.py
#
#   * load firmware and config roaches for use with HISPEC
#   * allow level setting
#   * allow rearming
#   * retrieve bram data

import threading, sys, time, socket, select, signal, traceback, datetime, atexit, errno
import corr
import time, numpy, math, os, fnmatch

DL = 2

###########################################################################
#
# Some functions
#

def logMsg(lvl, dlvl, message):
  message = message.replace("`","'")
  if (lvl <= dlvl):
    time = getCurrentDadaTimeUS()
    if (lvl == -1):
        sys.stderr.write("[" + time + "] WARN " + message + "\n")
    elif (lvl == -2):
        sys.stderr.write("[" + time + "] ERR  " + message + "\n")
    else:
        sys.stderr.write("[" + time + "] " + message + "\n")

def getCurrentDadaTimeUS():
  now = datetime.datetime.today()
  now_str = now.strftime("%Y-%m-%d-%H:%M:%S.%f")
  return now_str

def getHostMachineName():
  fqdn = socket.gethostname()
  parts = fqdn.split('.',1)
  if (len(parts) >= 1):
    host = parts[0]
  if (len(parts) == 2):
    domain = parts[1]
  return host

def signal_handler(signal, frame):
  print 'You pressed Ctrl+C!'

def openSocket(dl, host, port, attempts=10):
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  while (attempts > 0):

    logMsg(3, dl, "openSocket: attempt " + str(11-attempts))

    try:
      sock.connect((host, port))

    except socket.error, e:
      if e.errno == errno.ECONNREFUSED:
        logMsg(-1, dl, "openSocket: connection to " + host + ":" + str(port) + " refused")
        attempts -= 1
        time.sleep(1)
      else:
        raise
    else:
      logMsg(3, dl, "openSocket: conncected")
      attempts = 0

  return sock

def getUTCDadaTime(toadd=0):
  now = datetime.datetime.utcnow()
  if (toadd > 0):
    delta = datetime.timedelta(0, toadd)
    now = now + delta
  now_str = now.strftime("%Y-%m-%d-%H:%M:%S")
  return now_str

def sendTelnetCommand(sock, msg, timeout=1):
  result = ""
  response = ""
  eod = 0

  sock.send(msg + "\r\n")
  while (not eod):
    reply = sock.recv(4096)
    if (len(reply) == 0):
      eod = 1
    else:
      # remove trailing newlines
      reply = reply.rstrip()
      lines = reply.split("\n")
      for line in lines:
        if ((line == "ok") or (line == "fail")):
          result = reply
          eod = 1
        else:
          if (response == ""):
            response = line
          else:
            response = response + "\n" + line

  return (result, response)

############################################################################### 
#
# main
#

if __name__ == "__main__":
	try:

	  logMsg(1, DL, "STARTING SCRIPT")

#	  logMsg(2, DL, 'Starting leda_udpdb_thread instances...')
#	  os.system('/home/jkocz/roach_scripts/leda_reset_header_noutc.sh')
#	  logMsg(2, DL, "sleeping 10 seconds")
#	  time.sleep(10)

	  logMsg(2, DL, 'Connecting server sockets...')
	  # J, you should have leda_udpdb_thread running on 2 servers before this
	  sock0 = openSocket(DL, "ledagpu3", 12340)
	  sock1 = openSocket(DL, "ledagpu3", 12341)
	  sock2 = openSocket(DL, "ledagpu3", 12342)
	  sock3 = openSocket(DL, "ledagpu3", 12343)
	  sock4 = openSocket(DL, "ledagpu4", 12344)
	  sock5 = openSocket(DL, "ledagpu4", 12345)
	  sock6 = openSocket(DL, "ledagpu4", 12346)
	  sock7 = openSocket(DL, "ledagpu4", 12347)

	  logMsg(2, DL, 'Connecting ROACH sockets...')
	  roach1     = '169.254.128.13'
	  roach2     = '169.254.128.14'
	  fpga1 = corr.katcp_wrapper.FpgaClient(roach1, 7147)
	  fpga2 = corr.katcp_wrapper.FpgaClient(roach2, 7147)
	  time.sleep(2)

	  fpga1.write_int('adc_rst',3)
	  fpga2.write_int('adc_rst',3)

	  # enable ROACH
	  fpga1.write_int('tenge_enable',1)
	  fpga2.write_int('tenge_enable',1)

	  curr_time = int(time.time())
	  next_time = curr_time
	  logMsg(2, DL, "waiting for 1 second boundary")
	  while (curr_time == next_time):
		next_time = int(time.time())
	  #logMsg(2, DL, "sleeping 0.5 seconds")

	  # sleep 0.5 seconds
	  #time.sleep(0.5)

	  # now calculate the UTC time for now + 1 second
	  utc_start = getUTCDadaTime(1)
	  logMsg(2, DL, "UTC_START=" + utc_start)

	  # tell both udpdb_thread's what the UTC_START will be
	  command = 'SET_UTC_START '+utc_start
	  logMsg(2, DL, 'ledagpu3 <- ' + command)
	  result, response = sendTelnetCommand(sock0, command)
	  logMsg(2, DL, 'ledagpu3 -> ' + result + ' ' + response)
	  logMsg(2, DL, 'ledagpu3 <- ' + command)
	  result, response = sendTelnetCommand(sock1, command)
	  logMsg(2, DL, 'ledagpu3 -> ' + result + ' ' + response)
	  logMsg(2, DL, 'ledagpu3 <- ' + command)
	  result, response = sendTelnetCommand(sock2, command)
	  logMsg(2, DL, 'ledagpu3 -> ' + result + ' ' + response)
	  logMsg(2, DL, 'ledagpu3 <- ' + command)
	  result, response = sendTelnetCommand(sock3, command)
	  logMsg(2, DL, 'ledagpu3 -> ' + result + ' ' + response)
	  logMsg(2, DL, 'ledagpu4 <- ' + command)
	  result, response = sendTelnetCommand(sock4, command)
	  logMsg(2, DL, 'ledagpu4 -> ' + result + ' ' + response)
	  logMsg(2, DL, 'ledagpu4 <- ' + command)
	  result, response = sendTelnetCommand(sock5, command)
	  logMsg(2, DL, 'ledagpu4 -> ' + result + ' ' + response)
	  logMsg(2, DL, 'ledagpu4 <- ' + command)
	  result, response = sendTelnetCommand(sock6, command)
	  logMsg(2, DL, 'ledagpu4 -> ' + result + ' ' + response)
	  logMsg(2, DL, 'ledagpu4 <- ' + command)
	  result, response = sendTelnetCommand(sock7, command)
	  logMsg(2, DL, 'ledagpu4 -> ' + result  + ' ' + response)
	  # now tell both to "start" so they are ready for start of data / packet reset
	  command = 'START'
	  logMsg(2, DL, 'ledagpu3 <- ' + command)
	  result, response = sendTelnetCommand(sock0, command)
	  logMsg(2, DL, 'ledagpu3 -> ' + result + ' ' + response)
	  logMsg(2, DL, 'ledagpu3 <- ' + command)
	  result, response = sendTelnetCommand(sock1, command)
	  logMsg(2, DL, 'ledagpu3 -> ' + result + ' ' + response)
	  logMsg(2, DL, 'ledagpu3 <- ' + command)
	  result, response = sendTelnetCommand(sock2, command)
	  logMsg(2, DL, 'ledagpu3 -> ' + result + ' ' + response)
	  logMsg(2, DL, 'ledagpu3 <- ' + command)
	  result, response = sendTelnetCommand(sock3, command)
	  logMsg(2, DL, 'ledagpu3 -> ' + result  + ' ' + response)
	  logMsg(2, DL, 'ledagpu4 <- ' + command)
	  result, response = sendTelnetCommand(sock4, command)
	  logMsg(2, DL, 'ledagpu4 -> ' + result + ' ' + response)
	  logMsg(2, DL, 'ledagpu4 <- ' + command)
	  result, response = sendTelnetCommand(sock5, command)
	  logMsg(2, DL, 'ledagpu4 -> ' + result  + ' ' + response)
	  logMsg(2, DL, 'ledagpu4 <- ' + command)
	  result, response = sendTelnetCommand(sock6, command)
	  logMsg(2, DL, 'ledagpu4 -> ' + result + ' ' + response)
	  logMsg(2, DL, 'ledagpu4 <- ' + command)
	  result, response = sendTelnetCommand(sock7, command)
	  logMsg(2, DL, 'ledagpu4 -> ' + result  + ' ' + response)
	  # this is where you would then start the data (I'm assuming you have no 1pps ?)

	  #curr_time = int(time.time())
	  #next_time = curr_time
	  #logMsg(2, DL, "waiting for 1 second boundary")
	  #while (curr_time == next_time):
	  #	next_time = int(time.time())


	  fpga1.write_int('adc_rst',0)
	  fpga2.write_int('adc_rst',0)
	  logMsg(1,DL,'enable done')

	  sock0.close()
	  sock1.close()

	except:
	  logMsg(-2, DL, "main: exception caught: " + str(sys.exc_info()[0]))
	  print '-'*60
	  traceback.print_exc(file=sys.stdout)
	  print '-'*60

	logMsg(1, DL, "STOPPING SCRIPT")

	# exit
	sys.exit(0)
