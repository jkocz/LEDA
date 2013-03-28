/***************************************************************************
 *  
 *    Copyright (C) 2010 by Andrew Jameson
 *    Licensed under the Academic Free License version 2.1
 * 
 ****************************************************************************/

/*
 * leda_udptest
 *
 * Reads UDP packets from an ROACH supa fast
 */

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif

#include <time.h>
#include <sys/socket.h>
#include <math.h>
#include <pthread.h>
#include <sys/sysinfo.h>
#include <sys/types.h>
#include <sys/syscall.h>
#include <sys/mman.h>
#include <sched.h>
#include <signal.h>

#include "leda_udp.h"
#include "dada_affinity.h"
#include "sock.h"

int quit_threads = 0;

void stats_thread(void * arg);
void signal_handler(int signalValue);
void usage (void);

void usage()
{
  fprintf (stdout,
           "fastest_udpdb [options] key\n"
           " -b size        udp packet size [default 8192]\n"
           " -c core        bind to CPU core\n"
           " -i iface       interface for UDP packets [default all interfaces]\n"
           " -p port        port for incoming UDP packets [default %d]\n"
           " -h             print help text\n"
           " -v             verbose messages\n",
     LEDA_DEFAULT_UDPDB_PORT);
}

typedef struct {

  stats_t * packets;

  stats_t * bytes; 

  size_t pkt_size;

  unsigned verbose;

  uint64_t n_sleeps;

} leda_udptest_t;

int main (int argc, char **argv)
{

  // for stats thread
  leda_udptest_t udptest;

  /* Interface on which to listen for udp packets */
  char * interface = "any";

  /* port for incoming UDP packets */
  int inc_port = 4000;

  /* Flag set in verbose mode */
  unsigned verbose = 0;

  /* UDP packet size */
  size_t pkt_size = 8208;

  /* statistics thread */
  pthread_t stats_thread_id;

  int arg = 0;

  int core = -1;

  while ((arg=getopt(argc,argv,"b:c:i:p:vh")) != -1) 
  {
    switch (arg) 
    {
      case 'b':
        if (optarg)
          pkt_size = atoi(optarg);
        break;

      case 'c': 
        if (optarg)
          core = atoi(optarg);
        break;

      case 'i':
        if (optarg)
          interface = strdup(optarg);
        break;
    
      case 'p':
        inc_port = atoi (optarg);
        break;

      case 'v':
        verbose++;
        break;

      case 'h':
        usage();
        return 0;
      
      default:
        usage ();
        return 0;
    }
  }
  
  signal(SIGINT, signal_handler);

  stats_t * packets = init_stats_t();
  stats_t * bytes   = init_stats_t();

  udptest.packets = packets;
  udptest.bytes = bytes;
  udptest.verbose = verbose;
  udptest.pkt_size = pkt_size;
  udptest.n_sleeps = 0;

  multilog_t * log = multilog_open ("leda_udptest", 0);
  multilog_add (log, stderr);

  if (core >= 0)
    if (dada_bind_thread_to_core(core) < 0)
      multilog(log, LOG_INFO, "Error bindinf to core: %d\n", core);

  if (verbose)
    multilog(log, LOG_INFO, "starting stats_thread()\n");
  int rval = pthread_create (&stats_thread_id, 0, (void *) stats_thread, (void *) &udptest);
  if (rval != 0) {
    multilog(log, LOG_INFO, "Error creating stats_thread: %s\n", strerror(rval));
    return -1;
  }

  // UDP file descriptor
  int fd = dada_udp_sock_in (log, interface, inc_port, verbose);

  // set the socket size to 16 MB
  int sock_buf_size = 16*1024*1024;
  multilog(log, LOG_INFO, "start_function: setting buffer size to %d\n", sock_buf_size);
  dada_udp_sock_set_buffer_size (log, fd, verbose, sock_buf_size);

  // set the socket to non-blocking
  multilog(log, LOG_INFO, "start_function: setting non_block\n");
  sock_nonblock(fd);

  // clear any packets buffered by the kernel
  multilog(log, LOG_INFO, "start_function: clearing packets at socket\n");
  size_t cleared = dada_sock_clear_buffered_packets(fd, pkt_size);

  // allocate some nicely aligned memory
  void * buffer;
  posix_memalign (&buffer, 512, pkt_size);

  void * dst;
  posix_memalign (&dst, 512, pkt_size);

  unsigned char * arr = 0;
  unsigned have_packet = 0;
  unsigned got = 0;
  uint64_t tmp = 0;
  uint64_t seq_no = 0;
  uint64_t prev_seq_no = 0;
  unsigned i=0;

  while (!quit_threads) 
  {
    have_packet = 0;

    // incredibly tight loop to try and get a packet
    while (!have_packet && !quit_threads)
    {
      // receive 1 packet into the socket buffer
      got = recvfrom (fd, buffer, pkt_size, 0, NULL, NULL);

      if (got == pkt_size)
      {
        have_packet = 1;
      }
      else if (got == -1)
      {
        udptest.n_sleeps++;
      }
      else // we received a packet of the WRONG size, ignore it
      {
        multilog (log, LOG_ERR, "receive_obs: received %d bytes, expected %d\n", got, pkt_size);
      }
    }

    // we have a valid packet within the timeout
    if (have_packet)
    {
      // decode the packet sequence number
      arr = (unsigned char *)buffer;
      seq_no = UINT64_C (0);
      for (i = 0; i < 8; i++ )
      {
        tmp = UINT64_C (0);
        tmp = arr[8 - i - 1];
        seq_no |= (tmp << ((i & 7) << 3));

      }

      if (prev_seq_no)
      {
        if (seq_no == prev_seq_no + 1)
        {
          bytes->received += pkt_size;
          packets->received += 1;
          memcpy (dst, buffer, pkt_size);
        } 
        else if (seq_no <= prev_seq_no)
        {
          multilog (log, LOG_ERR, "main: impossible! seq=%"PRIu64", prev=%"PRIu64"\n", seq_no, prev_seq_no);
        }
        else
        {
          uint64_t diff = seq_no - prev_seq_no;
	  if (verbose > 2)
	          multilog(log, LOG_ERR, "dropped %"PRIu64" pkts seq=%"PRIu64", prev=%"PRIu64"\n", diff, seq_no, prev_seq_no);
          packets->dropped += diff;
          bytes->dropped += diff * (pkt_size);
        }
      }
      prev_seq_no = seq_no;
    }
  }

  if (verbose)
    multilog(log, LOG_INFO, "joining stats_thread\n");
  void * result;
  pthread_join (stats_thread_id, &result);

  close(fd);

  /* clean up memory */
  free(buffer);
  free(dst);


  return EXIT_SUCCESS;

}


/* 
 *  Thread to print simple capture statistics
 */
void stats_thread(void * arg) {

  leda_udptest_t * ctx = (leda_udptest_t *) arg;

  uint64_t b_rcv_total = 0;
  uint64_t b_rcv_1sec = 0;
  uint64_t b_rcv_curr = 0;

  uint64_t b_drp_total = 0;
  uint64_t b_drp_1sec = 0;
  uint64_t b_drp_curr = 0;

  uint64_t s_rcv_total = 0;
  uint64_t s_rcv_1sec = 0;
  uint64_t s_rcv_curr = 0;

  uint64_t ooo_pkts = 0;
  float gb_rcv_ps = 0;
  float mb_rcv_ps = 0;
  float mb_drp_ps = 0;

  while (!quit_threads)
  {
            
    /* get a snapshot of the data as quickly as possible */
    b_rcv_curr = ctx->bytes->received;
    b_drp_curr = ctx->bytes->dropped;
    s_rcv_curr = ctx->n_sleeps;

    /* calc the values for the last second */
    b_rcv_1sec = b_rcv_curr - b_rcv_total;
    b_drp_1sec = b_drp_curr - b_drp_total;
    s_rcv_1sec = s_rcv_curr - s_rcv_total;

    /* update the totals */
    b_rcv_total = b_rcv_curr;
    b_drp_total = b_drp_curr;
    s_rcv_total = s_rcv_curr;

    mb_rcv_ps = (double) b_rcv_1sec / 1000000;
    mb_drp_ps = (double) b_drp_1sec / 1000000;
    gb_rcv_ps = b_rcv_1sec * 8;
    gb_rcv_ps /= 1000000000;

    /* determine how much memory is free in the receivers */
    //if (ctx->verbose)
      fprintf (stderr,"R=%6.3f [Gb/s], D=%4.1f [MB/s], D=%"PRIu64" pkts, s_s=%"PRIu64"\n", gb_rcv_ps, mb_drp_ps, ctx->packets->dropped, s_rcv_1sec);

    sleep(1);
  }
}

/*
 *  Simple signal handler to exit more gracefully
 */
void signal_handler(int signalValue) 
{

  fprintf(stderr, "received signal %d\n", signalValue);
  if (quit_threads) {
    fprintf(stderr, "received signal %d twice, hard exit\n", signalValue);
    exit(EXIT_FAILURE);
  }
  quit_threads = 1;

}

