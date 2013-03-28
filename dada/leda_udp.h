/***************************************************************************
 *  
 *    Copyright (C) 2011 by Andrew Jameson
 *    Licensed under the Academic Free License version 2.1
 * 
 ****************************************************************************/

#ifndef __LEDA_UDP_H
#define __LEDA_UDP_H

#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <sys/types.h>

#include "dada_udp.h"
#include "leda_def.h"

#define LEDA_UDPDB_BUF_CLEAR = 0
#define LEDA_UDPDB_BUF_FULL = 1

/* socket buffer for receiving udp data */
typedef struct {

  int           fd;            // FD of the socket
  size_t        bufsz;         // size of socket buffer
  char *        buf;          // the socket buffer
  int           have_packet;   // 
  size_t        got;           // amount of data received

} leda_sock_t;

leda_sock_t * leda_init_sock ();

void leda_free_sock(leda_sock_t* b);

void leda_decode_header (unsigned char * b, uint64_t *seq_no, uint16_t * ant_id);

void leda_encode_header (char *b, uint64_t seq_no, uint16_t ant_id);

#endif

