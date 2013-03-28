#!/usr/bin/env python
#
# Various helper functions that Andrew Jameson wrote
#

import sys, time, socket, datetime, errno

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
      #attempts = 0
      return sock
  return None

def getUTCDadaTime(toadd=0):
  now = datetime.datetime.utcnow()
  if (toadd > 0):
    delta = datetime.timedelta(0, toadd)
    now = now + delta
  now_str = now.strftime("%Y-%m-%d-%H:%M:%S")
  return now_str

def wait_for_1sec_boundary():
	curr_time = int(time.time())
	next_time = curr_time
	while curr_time == next_time:
		next_time = int(time.time())
def wait_until_utc_sec(utcstr):
	cur_time = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H:%M:%S")
	while cur_time != utcstr:
		cur_time = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H:%M:%S")

def sendTelnetCommand(sock, msg, timeout=1):
  # Note: Returned result is either 'ok' or 'fail'
  result = ""
  response = ""
  eod = 0

  try:
	  sock.send(msg + "\r\n")
  except:
	  sock = None
	  return 'fail', ''
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
