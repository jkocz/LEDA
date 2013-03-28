/***************************************************************************
 *  
 *    Copyright (C) 2011 by Andrew Jameson
 *    Licensed under the Academic Free License version 2.1
 * 
 ****************************************************************************/

#include "dada_client.h"
#include "dada_hdu.h"
#include "dada_def.h"
#include "leda_udp.h"
#include "leda_def.h"
#include "ascii_header.h"
#include "daemon.h"
#include "dada_affinity.h"

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <assert.h>

#include <sys/types.h>
#include <sys/socket.h>

//#define _DEBUG

int quit_threads = 0;
void stats_thread(void * arg);

typedef struct {

  multilog_t * log;               // logging interface
  char * interface;               // ethX interface to use
  int port;                       // UDP capture port
  char * header_file;             // file containing DADA header
  unsigned verbose;               // verbosity level
  leda_sock_t * sock;             // custom socket struct
  stats_t * packets;              // packet stats
  stats_t * bytes;                // bytes stats
  uint64_t n_sleeps;              // busy sleep counter
  unsigned capture_started;       // flag for start of data
  uint64_t buffer_start_byte;     // buffer byte counters
  uint64_t buffer_end_byte;
  unsigned header_written;
  int recv_core;

} leda_udpdb_t;

void usage()
{
  fprintf (stdout,
     "leda_udpdb [options] header\n"
#ifdef HAVE_AFFINITY
     " -c core      bind process to CPU core\n"
#endif
     " -k key       hexadecimal shared memory key  [default: %x]\n"
     " -i ip        only listen on specified ip address [default: any]\n"
     " -p port      port for incoming UDP packets [default %d]\n"
     " -v           be verbose\n"
     " -s           1 transfer, then exit\n"
     "header        DADA header file contain obs metadata\n",
     DADA_DEFAULT_BLOCK_KEY, LEDA_DEFAULT_UDPDB_PORT);
}

int leda_init (leda_udpdb_t * ctx)
{
  // allocate memory for socket
  ctx->sock = leda_init_sock();

  // allocate memory for packet/byte stats
  ctx->packets = init_stats_t();
  ctx->bytes   = init_stats_t();

  ctx->n_sleeps = 0;
  ctx->capture_started = 0;
  ctx->buffer_start_byte = 0;
  ctx->buffer_end_byte = 0;
  ctx->header_written = 0;
 
#ifdef HAVE_AFFINITY
  // set the CPU that this thread shall run on
  if (ctx->recv_core > 0)
    if (dada_bind_thread_to_core(ctx->recv_core) < 0)
      multilog(ctx->log, LOG_WARNING, "receive_obs: failed to bind to core %d\n", ctx->recv_core);
#endif

}


/*! Function that opens the data transfer target */
int leda_udpdb_open (dada_client_t* client)
{
  assert (client != 0);

  // contextual data for dada_udpdb
  leda_udpdb_t * ctx = (leda_udpdb_t *) client->context;
  assert(ctx != 0);

  fprintf(stderr, "ctx->verbose=%d\n", ctx->verbose);
  if (ctx->verbose)
    multilog(ctx->log, LOG_INFO, "leda_udpdb_open()\n");

  // DADA ascii header
  char * header = client->header;
  assert (header != 0);

  // read the ASCII DADA header from the file
  if (fileread (ctx->header_file, client->header, client->header_size) < 0)
    multilog (client->log, LOG_ERR, "Could not read header from %s\n", ctx->header_file);

  // open socket
  ctx->sock->fd = dada_udp_sock_in(ctx->log, ctx->interface, ctx->port, ctx->verbose);
  if (ctx->sock->fd < 0) 
  {
    multilog (ctx->log, LOG_ERR, "Error, Failed to create udp socket\n");
    return -1;
  }

  // set the socket size to 256 MB
  int sock_buf_size = 256*1024*1024;
  if (ctx->verbose)
    multilog(ctx->log, LOG_INFO, "start_function: setting buffer size to %d\n", sock_buf_size);
  dada_udp_sock_set_buffer_size (ctx->log, ctx->sock->fd, ctx->verbose, sock_buf_size);

  // set the socket to non-blocking
  if (ctx->verbose)
    multilog(ctx->log, LOG_INFO, "start_function: setting non_block\n");
  sock_nonblock(ctx->sock->fd);

  // clear any packets buffered by the kernel
  if (ctx->verbose)
    multilog(ctx->log, LOG_INFO, "start_function: clearing packets at socket\n");
  size_t cleared = dada_sock_clear_buffered_packets(ctx->sock->fd, UDP_PAYLOAD);

  ctx->header_written = 0;

  return 0;
}

/*! Transfer header to data block */
int64_t leda_udpdb_recv (dada_client_t* client, void* data, uint64_t data_size)
{

  leda_udpdb_t* ctx = (leda_udpdb_t *) client->context;

  ctx->header_written = 1;
  multilog (client->log, LOG_INFO, "recv: read header\n");
  return data_size;
}

/*! Transfer UDP data to data block, receives 1 block worth of UDP packets */
int64_t leda_udpdb_recv_block (dada_client_t* client, void* data, uint64_t data_size, uint64_t block_id)
{
  leda_udpdb_t * ctx = (leda_udpdb_t *) client->context;

  unsigned keep_receiving = 1;
  uint64_t bytes_received = 0;
  uint64_t seq_no = 0;
  uint16_t ant_id = 0;
  uint64_t seq_byte = 0;
  unsigned ignore_packet = 0;
  int errsv = 0;
  uint64_t byte_offset = 0;

  // update start/end bytes for this block
  if (ctx->capture_started)
  {
    ctx->buffer_start_byte = ctx->buffer_end_byte + UDP_DATA;
    ctx->buffer_end_byte = (ctx->buffer_start_byte + data_size) - UDP_DATA;
    if (ctx->verbose)
      multilog (client->log, LOG_INFO, "recv_block: CONT  [%"PRIu64" - %"PRIu64"]\n", ctx->buffer_start_byte, ctx->buffer_end_byte);
  }

  while (keep_receiving)
  {
#ifdef _DEBUG
    multilog (client->log, LOG_INFO, "recv_block: get packet\n");
#endif

    ctx->n_sleeps = 0;

    while (!ctx->sock->have_packet && !quit_threads)
    {

      // receive 1 packet into the socket buffer
      ctx->sock->got = recvfrom (ctx->sock->fd, ctx->sock->buf, UDP_PAYLOAD, 0, NULL, NULL);

      if (ctx->sock->got == UDP_PAYLOAD)
      {
        ctx->sock->have_packet = 1;
        ignore_packet = 0;
      }
      else if (ctx->sock->got == -1)
      {
        errsv = errno;
        if (errsv == EAGAIN)
        {
          ctx->n_sleeps++;
        }
        else
        {
          multilog (client->log, LOG_ERR, "recv_block: recvfrom failed %s\n", strerror(errsv));
          return -1;
        }
      }
      else // we received a packet of the WRONG size, ignore it
      {
        multilog (client->log, LOG_ERR, "recv_block: received %d bytes, expected %d\n", ctx->sock->got, UDP_PAYLOAD);
        ignore_packet = 1;
      }

      // if packets stop flowing
      if (ctx->capture_started && ctx->n_sleeps > 100000)
        return 0;
    }

#ifdef _DEBUG
    multilog (client->log, LOG_INFO, "recv_block: have packet\n");
#endif

    // if we received a packet
    if (ctx->sock->have_packet)
    {
      // reset this for next iteration

      ctx->sock->have_packet = 0;

      // decode sequence number
      leda_decode_header(ctx->sock->buf, &seq_no, &ant_id);

#ifdef _DEBUG
      multilog (client->log, LOG_INFO, "recv_block: seq_no=%"PRIu64"\n", seq_no);
#endif

      // if first packet
      if (!ctx->capture_started)
      {
        ctx->buffer_start_byte = seq_no * UDP_DATA;
        ctx->buffer_end_byte   = (ctx->buffer_start_byte + data_size) - UDP_DATA;
        ctx->capture_started = 1;
        if (ctx->verbose)
          multilog (client->log, LOG_INFO, "recv_block: START [%"PRIu64" - %"PRIu64"]\n", ctx->buffer_start_byte, ctx->buffer_end_byte);
      }

      seq_byte = seq_no * UDP_DATA;

      // if packet arrived too late, ignore
      if (seq_byte < ctx->buffer_start_byte)
      {
        ctx->packets->dropped++;
        ctx->bytes->dropped += UDP_DATA;
      }
      else
      {
        // packet belongs in this buffer
        if (seq_byte <= ctx->buffer_end_byte)
        {
         byte_offset = seq_byte - ctx->buffer_start_byte;
          memcpy (data + byte_offset, ctx->sock->buf + UDP_HEADER, UDP_DATA);
          ctx->packets->received++;
          if (seq_byte == ctx->buffer_end_byte)
            keep_receiving = 0;
        }
        // packet belongs in subsequent buffer
        else
        {
          ctx->packets->dropped++;
          keep_receiving = 0;
        }
        ctx->bytes->received += UDP_DATA;
      }
    }
  }
  return data_size;
}



/*! Function that closes socket */
int leda_udpdb_close (dada_client_t* client, uint64_t bytes_written)
{

  assert (client != 0);

  // status and error logging facility
  multilog_t* log = client->log;
  assert (log != 0);

  // contextual data for dada_udpdb
  leda_udpdb_t * ctx = (leda_udpdb_t *) client->context;
  assert(ctx != 0);

  close(ctx->sock->fd);


  return 0;
}

int main (int argc, char **argv)
{

  // udpdb contextual struct
  leda_udpdb_t udpdb;

  // DADA Header plus Data Unit 
  dada_hdu_t* hdu = 0;

  // DADA Primary Read Client main loop
  dada_client_t* client = 0;

  // DADA Logger
  multilog_t* log = 0;

  // Flag set in verbose mode
  char verbose = 0;

  char * header_file = 0;

  // Quit flag
  char single_transfer = 0;

  // dada key for SHM 
  key_t dada_key = DADA_DEFAULT_BLOCK_KEY;

  // ethernet interface to receive packets on
  char * interface = "any";

  // port to receive data on
  int port = LEDA_DEFAULT_UDPDB_PORT;

  int arg = 0;

  int core = -1;

  while ((arg=getopt(argc,argv,"c:k:i:p:sv")) != -1)
    switch (arg) {
  
    case 'c':
      if (optarg)
      {
        core = atoi(optarg);
        break;
      }
      else
      {
        fprintf (stderr, "ERROR: -c flag requires argument\n");
        return EXIT_FAILURE;
      }

    case 'k':
      if (sscanf (optarg, "%x", &dada_key) != 1) {
        fprintf (stderr, "ERROR: could not parse key from %s\n", optarg);
        return EXIT_FAILURE;
      }
      break;

    case 'i':
      if (optarg)
      {
        interface = strdup(optarg);
        break;
      }
      else
      {
        fprintf (stderr, "ERROR: -i flag requires argument\n");
        return EXIT_FAILURE;
      }

    case 'p':
      if (optarg)
      {
        port = atoi(optarg);
        break;
      }
      else
      {
        fprintf (stderr, "ERROR: -p flag requires argument\n");
        return EXIT_FAILURE;
      }

    case 's':
      single_transfer = 1;
      break;

    case 'v':
      verbose++;
      break;

    default:
      usage ();
      return 0;
      
    }

  // check the header file was supplied
  if ((argc - optind) != 1) 
  {
    fprintf (stderr, "ERROR: header must be specified\n");
    usage();
    exit(EXIT_FAILURE);
  }

  udpdb.header_file = strdup(argv[optind]);

  // check the header can be read
  FILE* fptr = fopen (udpdb.header_file, "r");
  if (!fptr) 
  {
    fprintf (stderr, "ERROR: could not open '%s' for reading: %s\n", header_file, strerror(errno));
    return(EXIT_FAILURE);
  }
  fclose(fptr);

  udpdb.interface = strdup(interface);
  udpdb.port = port;
  udpdb.verbose = verbose;
  udpdb.recv_core = core;

  // allocate memory for socket etc
  if (verbose)
    multilog (log, LOG_INFO, "main: initialising resources\n");
  if (leda_init (&udpdb) < 0)
  {
    multilog (log, LOG_ERR, "could not initialize resources\n");
    return EXIT_FAILURE;
  }

  log = multilog_open ("dada_udpdb", 0);
  multilog_add (log, stderr);

  hdu = dada_hdu_create (log);

  dada_hdu_set_key(hdu, dada_key);

  if (verbose)
    multilog (log, LOG_INFO, "main: connecting to HDU %x\n", dada_key);
  if (dada_hdu_connect (hdu) < 0)
  {
    fprintf(stderr, "ERROR: could not connect to HDU %x\n", dada_key);
    return EXIT_FAILURE;
  }

  if (verbose)
    multilog (log, LOG_INFO, "main: locking write on HDU %x\n", dada_key);
  if (dada_hdu_lock_write (hdu) < 0)
  {
    fprintf(stderr, "ERROR: could not lock write on HDU %x\n", dada_key);
    return EXIT_FAILURE;
  }

  // check that the DADA buffer block size is a multiple of the UDP_DATA size
  uint64_t block_size = ipcbuf_get_bufsz ((ipcbuf_t *) hdu->data_block);
  if (block_size % UDP_DATA != 0)
  {
    fprintf(stderr, "ERROR: DADA buffer size must be a multiple of UDP_DATA size\n");
    dada_hdu_unlock_write (hdu);
    dada_hdu_disconnect (hdu);
    return EXIT_FAILURE;
  }
  if (verbose)
    multilog (log, LOG_INFO, "main: DADA block_size=%"PRIu64", UDP_DATA size=%d\n", block_size, UDP_DATA);

  client = dada_client_create ();

  udpdb.verbose = verbose;
  udpdb.log = log;

  client->context = &udpdb;
  client->log = log;

  client->data_block = hdu->data_block;
  client->header_block = hdu->header_block;

  client->open_function     = leda_udpdb_open;
  client->io_function       = leda_udpdb_recv;
  client->io_block_function = leda_udpdb_recv_block;
  client->close_function    = leda_udpdb_close;

  client->direction         = dada_client_writer;

  pthread_t stats_thread_id;
  if (verbose)
    multilog(log, LOG_INFO, "main: starting stats_thread()\n");
  int rval = pthread_create (&stats_thread_id, 0, (void *) stats_thread, (void *) &udpdb);
  if (rval != 0) {
    multilog(log, LOG_INFO, "Error creating stats_thread: %s\n", strerror(rval));
    return -1;
  }

  if (verbose)
    multilog (log, LOG_INFO, "main: dada_client_write\n");
  if (dada_client_write (client) < 0)
    multilog (log, LOG_ERR, "Error during transfer\n");

  quit_threads = 1;
  void* result = 0;
  if (verbose)
    multilog(log, LOG_INFO, "joining stats_thread\n");
  pthread_join (stats_thread_id, &result);

  if (dada_hdu_unlock_write (hdu) < 0)
  {
    multilog (log, LOG_ERR, "could not unlock read on hdu\n");
    return EXIT_FAILURE;
  }

  if (dada_hdu_disconnect (hdu) < 0)
  {
    multilog (log, LOG_ERR, "could not disconnect from HDU\n");
    return EXIT_FAILURE;
  }

  return EXIT_SUCCESS;
}

/* 
 *  Thread to print simple capture statistics
 */
void stats_thread(void * arg) 
{
  leda_udpdb_t * ctx = (leda_udpdb_t *) arg;

  uint64_t bytes_received_total = 0;
  uint64_t bytes_received_this_sec = 0;
  uint64_t bytes_dropped_total = 0;
  uint64_t bytes_dropped_this_sec = 0;
  double   mb_received_ps = 0;
  double   mb_dropped_ps = 0;

  struct timespec ts;

  sleep(2);

  fprintf(stderr,"Bytes\t\t\t\tPackets\n");
  fprintf(stderr,"Received\t Dropped\tReceived\tDropped\t\n");

  while (!quit_threads)
  {
    bytes_received_this_sec = ctx->bytes->received - bytes_received_total;
    bytes_dropped_this_sec  = ctx->bytes->dropped - bytes_dropped_total;

    bytes_received_total = ctx->bytes->received;
    bytes_dropped_total = ctx->bytes->dropped;

    mb_received_ps = (double) bytes_received_this_sec / (1024*1024);
    mb_dropped_ps = (double) bytes_dropped_this_sec / (1024*1024);

    //fprintf(stderr,"T=%5.2f, R=%5.2f MB/s\t D=%5.2f MB/s packets=%"PRIu64" dropped=%"PRIu64"\n", (mb_received_ps+mb_dropped_ps), mb_received_ps, mb_dropped_ps, ctx->packets->received, ctx->packets->dropped);
   
    fprintf(stderr,"%7.1f MB/s\t%7.1f MB/s\t%"PRIu64" pkts\t\t%"PRIu64" pkts\n", (mb_received_ps+mb_dropped_ps), mb_received_ps, mb_dropped_ps, ctx->packets->received, ctx->packets->dropped);

    sleep(1);
  }
}

