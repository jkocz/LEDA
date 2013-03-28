/***************************************************************************
 *  
 *    Copyright (C) 2009 by Andrew Jameson
 *    Licensed under the Academic Free License version 2.1
 * 
 ****************************************************************************/

#ifndef __LEDA_UDPDB_THREAD_H
#define __LEDA_UDPDB_THREAD_H

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>
#include <errno.h>
#include <assert.h>
#include <netinet/in.h>
#include <signal.h>

#include "futils.h"
#include "dada_hdu.h"
#include "dada_pwc_main.h"
#include "multilog.h"
#include "ipcio.h"
#include "ascii_header.h"

#include "leda_def.h"
#include "leda_udp.h"

/* Number of UDP packets to be recived for a called to buffer_function */
#define NOTRECORDING 0
#define RECORDING 1

typedef struct {

  //dada_hdu_t *      hdu;                // DADA Header + Data Unit
  multilog_t *      log;                // DADA logging interface
  int               verbose;            // verbosity flag 

  leda_sock_t *     sock;               // UDP socket for data capture
  int               port;               // port to receive UDP data 
  int               control_port;       // port to receive control commands
  char *            interface;          // IP Address to accept packets on 

  // configuration for number of inputs
  unsigned int      num_inputs;         // number of antennas / inputs

  // datablock management
  unsigned	    ihdu;
  unsigned          nhdus;
  dada_hdu_t     ** hdus;
  uint64_t        * hdu_bufsz;
  unsigned        * block_open;        // if the current data block element is open
  unsigned          hdu_open;          // if the current hdu is open
  char           ** block;             // pointer to current datablock buffer
  uint64_t        * block_start_byte;  // seq_byte of first byte for the block
  uint64_t        * block_end_byte;    // seq_byte of first byte of final packet of the block
  uint64_t        * block_count;       // number of packets in this block

  // packets
  unsigned          capture_started;      // flag for start of UDP data
  uint64_t          packets_per_buffer;   // number of UDP packets per datablock buffer

  /* Packet and byte statistics */
  stats_t * packets;
  stats_t * bytes;

  uint64_t bytes_to_acquire;
  double mb_rcv_ps;
  double mb_drp_ps;
  double mb_free;
  double mb_total;
  uint64_t rcv_sleeps;

  uint64_t last_seq;                     // most recently received seq number
  uint64_t last_byte;                    // most recently received byte
  struct   timeval timeout; 

  uint64_t n_sleeps;
  uint64_t ooo_packets;

  int      recv_core;

} udpNdb_t;


int leda_udpNdb_init_receiver (udpNdb_t * ctx);
void leda_udpNdb_reset_receiver (udpNdb_t * ctx);
int leda_udpNdb_destroy_receiver (udpNdb_t * ctx);
int leda_udpNdb_connect_hdus (udpNdb_t * ctx, char ** argv, int num_hdu);
void leda_udpNdb_destroy_hdus (udpNdb_t * ctx);
int leda_udpNdb_open_buffer (udpNdb_t * ctx, int nhdu);
int leda_udpNdb_close_buffer (udpNdb_t * ctx, uint64_t bytes_written, unsigned eod, int ndhu);
int leda_udpNdb_new_buffer (udpNdb_t * ctx,int nhdu);
//int leda_udpNdb_close_hdu (udpNdb_t * ctx, uint64_t bytes_written)
// allocate required resources for data capture
int leda_udpNdb_prepare (udpNdb_t * ctx);

// move to a state where data acquisition can begin
time_t leda_dpNdb_start (udpNdb_t * ctx, char * header, int nhdu);

// main workhorse function to receive data for a single observation
void * leda_udpNdb_receive_obs (void * ctx);

// close the datablock signifying end of data 
int udpNdb_stop_function (udpNdb_t* ctx);

void usage();
void signal_handler (int signalValue); 
void stats_thread(void * arg);
void control_thread(void * arg);

#endif
