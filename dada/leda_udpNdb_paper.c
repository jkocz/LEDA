/***************************************************************************
 *  
 *    Copyright (C) 2012 by Andrew Jameson
 *    Licensed under the Academic Free License version 2.1
 * 
 ****************************************************************************/

/*
 * leda_udpNdb_thread
 *
 * Reads UDP packets for LEDA correlator, uses:
 *  * separate thread for primary UDP capture
 *  * direct block access for performance
 *  * variable missed packet buffers for out of order packets 
 * 
 *  JKOCZ: Modified to include sending UDP packets to multiple buffers
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
#include <sys/types.h>
#include <sys/syscall.h>
#include <sys/mman.h>
#include <sched.h>
#include <endian.h>

#include "leda_udpNdb_paper.h"
#include "dada_generator.h"
#include "dada_affinity.h"

/* debug mode */
#define _DEBUG 1

/* global variables */
int quit_threads = 0;
int start_pending = 0;
int stop_pending = 0;
int recording = 0;
uint64_t stop_byte = 0;

void usage()
{
  fprintf (stdout,
     "leda_udpNdb [options] key1 keyN\n"
     " -b core          bind process to run on CPU core\n"
     " -c port          port for 'telnet' control commands\n"
     " -f header_file   ascii header file[default ]\n"
     " -i iface         interface for UDP packets [default all interfaces]\n"
     " -n inputs        number of inputs / antennae [default 1]\n"
     " -p port          port for incoming UDP packets [default %d]\n"
     " -t secs          acquire for secs only [default continuous]\n"
     " -x x-engines     number of x-engines to distribute data to [default 1]\n"   
     " -d               run as a daemon\n"
     " -v               verbose messages\n"
     " -h               print help text\n",
     LEDA_DEFAULT_UDPDB_PORT);
}


/* 
 *  intialize UDP receiver resources
 */
int leda_udpNdb_init_receiver (udpNdb_t * ctx)
{
  if (ctx->verbose > 1)
    multilog (ctx->log, LOG_INFO, "leda_udpNdb_init_receiver()\n");

  // create a LEDA socket which can hold variable num of UDP packet
  ctx->sock = leda_init_sock();

  //ctx->packets_this_xfer = 0;
  ctx->ooo_packets = 0;
  ctx->recv_core = -1;
  ctx->n_sleeps = 0;
  ctx->mb_rcv_ps = 0;
  ctx->mb_drp_ps = 0;
  //ctx->block_open = 0;
  //ctx->block_count = 0;
  //ctx->capture_started = 0;
  ctx->last_seq = 0;
  ctx->last_byte = 0;

  // allocate required memory strucutres
  ctx->packets = init_stats_t();
  ctx->bytes   = init_stats_t();
  return 0;

}

/* 
 *  destory UDP receiver resources 
 */
int leda_udpNdb_destroy_receiver (udpNdb_t * ctx)
{
  if (ctx->sock)
    leda_free_sock(ctx->sock);
  ctx->sock = 0;
}

/*
 *  reset receiver before an observation commences
 */
void leda_udpNdb_reset_receiver (udpNdb_t * ctx) 
{

  int i=0;
  if (ctx->verbose)
    multilog (ctx->log, LOG_INFO, "leda_udpNdb_reset_receiver()\n");

  for (i=0; i<ctx->nhdus; i++)
	  ctx->capture_started[i] = 0;
  ctx->last_seq = 0;
  ctx->last_byte = 0;
  ctx->n_sleeps = 0;

  reset_stats_t(ctx->packets);
  reset_stats_t(ctx->bytes);
}


int leda_udpNdb_connect_hdus (udpNdb_t * ctx, char ** argv, int num_hdu)
{
  unsigned i;

  if (ctx->verbose > 1)
     multilog(ctx->log, LOG_INFO, "leda_udpNdb_connect_hdus()\n");

  key_t dada_key;
 
  ctx->hdus = (dada_hdu_t **) malloc(sizeof(dada_hdu_t *) * num_hdu);
  assert (ctx->hdus);

  ctx->hdu_bufsz = (uint64_t *) malloc(sizeof(uint64_t) * num_hdu);
  assert (ctx->hdu_bufsz);

  ctx->block_start_byte = (uint64_t *) malloc(sizeof(uint64_t) * num_hdu);
  assert (ctx->block_start_byte);

  ctx->block_end_byte   = (uint64_t *) malloc(sizeof(uint64_t) * num_hdu);
  assert (ctx->block_end_byte);

  ctx->block_count   = (uint64_t *) malloc(sizeof(uint64_t) * num_hdu);
  assert (ctx->block_count);
  
  ctx->packets = (stats_t *) malloc(sizeof(stats_t) * num_hdu);
  assert (ctx->packets);

  ctx->bytes = (stats_t *) malloc(sizeof(stats_t) * num_hdu);
  assert (ctx->bytes);

  ctx->block_open = (unsigned *) malloc(sizeof(unsigned) * num_hdu);
  assert (ctx->block_open);

  ctx->block = (char **) malloc(sizeof(char *) * num_hdu);
  assert (ctx->block);

  ctx->capture_started = (unsigned *) malloc(sizeof(unsigned) * num_hdu);
  assert(ctx->capture_started);

  for (i=0; i<ctx->nhdus;i++)
  {
    
    uint64_t block_size = 0;

    if (ctx->verbose)
      multilog(ctx->log, LOG_INFO, "connect_hdus: connect hdu[%d] %s\n",i,argv[i]);

    ctx->block_start_byte[i] = 0;
    ctx->block_end_byte[i] = 0;
    ctx->block_count[i] = 0;
    ctx->block_open[i] = 0;
  

    if (sscanf (argv[i], "%x", &dada_key) != 1)
    {
      multilog (ctx->log, LOG_ERR, "could not parse key %d from %s\n", i, argv[i]);
      return -1;
    }
    // create HDU struct
    ctx->hdus[i] = dada_hdu_create(ctx->log);

    if (ctx->verbose)
      multilog(ctx->log, LOG_INFO, "HDU struct created\n");

    // set the key to connecting to the HDU
    dada_hdu_set_key (ctx->hdus[i], dada_key);
   
    if (ctx->verbose)
      multilog(ctx->log, LOG_INFO, "key set\n");

    // connect to HDU
    if (dada_hdu_connect (ctx->hdus[i]) < 0)
    {    
      multilog(ctx->log, LOG_ERR, "could not connect to hdu %d\n", i);
      return -1;
    }
   
    if (ctx->verbose)
      multilog(ctx->log, LOG_INFO, "determining bufsz\n");

    // determine block size of the data block
    ctx->hdu_bufsz[i] = ipcbuf_get_bufsz ((ipcbuf_t *) ctx->hdus[i]->data_block);

    // determine number of packets per block, must be a multiple of UDP_DATA    
    if (ctx->hdu_bufsz[i] % UDP_DATA != 0)
    {
      multilog (ctx->log, LOG_ERR, "data block size of [%"PRIu64"] was not "
                "a multiple of the UDP_DATA size [%d]\n", ctx->hdu_bufsz[i], UDP_DATA);
      return EXIT_FAILURE;
    }
 
    if (!ctx->packets_per_buffer)
    {
      ctx->packets_per_buffer = ctx->hdu_bufsz[i] / UDP_DATA;

      if (ctx->verbose)
        multilog (ctx->log, LOG_INFO, "main: HDU bufsz=%"PRIu64", UDP_DATA=%d, packets_per_buffer=%"PRIu64"\n",
                                    ctx->hdu_bufsz[i], UDP_DATA, ctx->packets_per_buffer);
    }
  }

  if (ctx->verbose)
     multilog(ctx->log, LOG_INFO, "leda_udpNdb_connect_hdus() complete\n");
  
}



/*  
 *  unlock write and disconnect from all hdus
 */
void leda_udpNdb_destroy_hdus (udpNdb_t * ctx)
{

  unsigned i=0;
  if (ctx->hdus)
  {
    for (i=0; i<ctx->nhdus; i++)
    {
      if (ctx->verbose)
        multilog (ctx->log, LOG_INFO, "destroy_hdus: disconnecting hdu%d\n", i);
      // only the current hdu should be open/locked
      //if (ctx->ihdu == i) 
      //{
      //  if (dada_hdu_unlock_write (ctx->hdus[i]) < 0)
      //    multilog (ctx->log, LOG_ERR, "could not unlock write on hdu %d\n", i);
      //}
      if (dada_hdu_disconnect (ctx->hdus[i]) < 0)
        multilog (ctx->log, LOG_ERR, "could not unlock write on hdu %d\n", i);
    }

    free (ctx->hdus);
    ctx->hdus = 0;
  }

}


int leda_udpNdb_prepare (udpNdb_t * ctx)
{

  unsigned i;

  if (ctx->verbose)
    multilog(ctx->log, LOG_INFO, "leda_udpNdb_prepare()\n");

  // open socket
  if (ctx->verbose)
    multilog(ctx->log, LOG_INFO, "prepare: creating udp socket on %s:%d\n", ctx->interface, ctx->port);
  ctx->sock->fd = dada_udp_sock_in(ctx->log, ctx->interface, ctx->port, ctx->verbose);
  if (ctx->sock->fd < 0) {
    multilog (ctx->log, LOG_ERR, "Error, Failed to create udp socket\n");
    return -1;
  }

  // set the socket size to 256 MB
  int sock_buf_size = 256*1024*1024;
  if (ctx->verbose)
    multilog(ctx->log, LOG_INFO, "prepare: setting buffer size to %d\n", sock_buf_size);
  dada_udp_sock_set_buffer_size (ctx->log, ctx->sock->fd, ctx->verbose, sock_buf_size);

  // set the socket to non-blocking
  if (ctx->verbose)
    multilog(ctx->log, LOG_INFO, "prepare: setting non_block\n");
  sock_nonblock(ctx->sock->fd);

  // clear any packets buffered by the kernel
  if (ctx->verbose)
    multilog(ctx->log, LOG_INFO, "prepare: clearing packets at socket\n");
  size_t cleared = dada_sock_clear_buffered_packets(ctx->sock->fd, UDP_PAYLOAD);

  // setup the next_seq to the initial value
  ctx->last_seq = 0;
  ctx->last_byte = 0;
  ctx->n_sleeps = 0;

  for (i=0; i<ctx->nhdus; i++)
  {
    // lock as writer on the HDU
    if (dada_hdu_lock_write (ctx->hdus[i]) < 0)
    {
      multilog (ctx->log, LOG_ERR, "open_hdu: could not lock write on header hdu%d \n", i);
      return -1;
    }
  }

  if (ctx->verbose)
     multilog(ctx->log, LOG_INFO, "leda_udpNdb_prepare() complete\n");

  return 0;
}

/*
 *  start the observation on the data block, completing the header and marking
 *  the buffer as filled
 */
time_t leda_udpNdb_start (udpNdb_t * ctx, char * obs_header)
{
  unsigned i;

  for (i=0; i< ctx->nhdus; i++)
  {

    // get the next available header block
    uint64_t header_size = ipcbuf_get_bufsz (ctx->hdus[i]->header_block);
    char * header = ipcbuf_get_next_write (ctx->hdus[i]->header_block);

    // copy the current observation's header to the header block
    memcpy (header, obs_header, header_size);

    // note to jkocz: here you could connect to ROACH'es and reg_arm, that way we
    // can insert the UTC_START into the DADA metadata if desirable


    // set any additional parameters that need setting
    uint64_t obs_offset = 0;
    if (ascii_header_set (header, "OBS_OFFSET", "%"PRIu64, obs_offset) < 0)
      multilog (ctx->log, LOG_WARNING, "Could not write OBS_OFFSET to header\n");
  
    if (ascii_header_set (header, "HDR_SIZE", "%"PRIu64, header_size) < 0)
      multilog (ctx->log, LOG_WARNING, "Could not write HDR_SIZE to header\n");
  
    if (ctx->verbose > 1)
      multilog (ctx->log, LOG_INFO, "header=%s\n", header);

    // mark the header as filled
    if (ipcbuf_mark_filled (ctx->hdus[i]->header_block, header_size) < 0)
    {
      multilog (ctx->log, LOG_ERR, "start: could not mark filled Header Block\n");
      return -1;
    }
  
    // open a block of the data block, ready for writing
    if (leda_udpNdb_open_buffer (ctx,i) < 0)
    {
      multilog (ctx->log, LOG_ERR, "start: leda_udpNdb_open_buffer failed\n");
      return -1;
    }
  }

  if (ctx->verbose)
     multilog(ctx->log, LOG_INFO, "leda_udpNdb_start() complete\n");


  return 0;

}


/* 
 *  open a data block buffer ready for direct access
 */
int leda_udpNdb_open_buffer (udpNdb_t * ctx, int nhdu)
{

  if (ctx->verbose > 1)
    multilog (ctx->log, LOG_INFO, "leda_udpNdb_open_buffer()\n");

  if (ctx->block_open[nhdu])
  {
    multilog (ctx->log, LOG_ERR, "open_buffer: buffer already opened, buffer: %d\n",nhdu);
    return -1;
  }

  if (ctx->verbose > 1)
    multilog (ctx->log, LOG_INFO, "open_buffer: ipcio_open_block_write\n");

  uint64_t block_id = 0;

  ctx->block[nhdu] = ipcio_open_block_write (ctx->hdus[nhdu]->data_block, &block_id);
  if (!ctx->block[nhdu])
  { 
    multilog (ctx->log, LOG_ERR, "open_buffer: ipcio_open_block_write failed\n");
    return -1;
  }

  ctx->block_open[nhdu] = 1;
  ctx->block_count[nhdu] = 0;

  return 0;
}

/*
 *  close a data buffer, assuming a full block has been written
 */
int leda_udpNdb_close_buffer (udpNdb_t * ctx, uint64_t bytes_written, unsigned eod, int nhdu)
{

  if (ctx->verbose && stop_pending || ctx->verbose > 1)
    multilog (ctx->log, LOG_INFO, "leda_udpNdb_close_buffer(%"PRIu64", %d)\n", bytes_written, eod);

  if (!ctx->block_open[nhdu])
  { 
    multilog (ctx->log, LOG_ERR, "close_buffer: buffer already closed\n");
    return -1;
  }

  // log any buffers that are not full, except for the 1 byte "EOD" buffer
  if ((bytes_written != 1) && (bytes_written != ctx->hdu_bufsz[nhdu]))
    multilog (ctx->log, (eod ? LOG_INFO : LOG_WARNING), "close_buffer: "
              "bytes_written[%"PRIu64"] != hdu_bufsz[%"PRIu64"]\n", 
              bytes_written, ctx->hdu_bufsz);

  if (eod)
  {
    if (ipcio_update_block_write (ctx->hdus[nhdu]->data_block, bytes_written) < 0)
    {
      multilog (ctx->log, LOG_ERR, "close_buffer: ipcio_update_block_write failed\n");
      return -1;
    }
  }
  else 
  {
    if (ipcio_close_block_write (ctx->hdus[nhdu]->data_block, bytes_written) < 0)
    {
      multilog (ctx->log, LOG_ERR, "close_buffer: ipcio_close_block_write failed\n");
      return -1;
    }
  }

  ctx->block[nhdu] = 0;
  ctx->block_open[nhdu] = 0;

  return 0;
}


/* 
 *  move to the next ring buffer element. return pointer to base address of new buffer
 */
int leda_udpNdb_new_buffer (udpNdb_t * ctx, int nhdu)
{

  if (ctx->verbose > 1)
    multilog (ctx->log, LOG_INFO, "leda_udpNdb_new_buffer()\n");

  if (leda_udpNdb_close_buffer (ctx, ctx->hdu_bufsz[nhdu], 0,nhdu) < 0)
  {
    multilog (ctx->log, LOG_INFO, "new_buffer: leda_udpNdb_close_buffer failed\n");
    return -1;
  }

  if (leda_udpNdb_open_buffer (ctx,nhdu) < 0) 
  {
    multilog (ctx->log, LOG_INFO, "new_buffer: leda_udpNdb_open_buffer failed\n");
    return -1;
  }

  // increment buffer byte markers
  ctx->block_start_byte[nhdu] = ctx->block_end_byte[nhdu] + UDP_DATA;
  ctx->block_end_byte[nhdu] = ctx->block_start_byte[nhdu] + ( ctx->packets_per_buffer - 1) * UDP_DATA;

  if (ctx->verbose > 1)
    multilog(ctx->log, LOG_INFO, "new_buffer: buffer_bytes [%"PRIu64" - %"PRIu64"]\n", 
             ctx->block_start_byte[nhdu], ctx->block_end_byte[nhdu]);

  return 0;

}

/*
 * Receive UDP data for 1 observation, continually writing it to 
 * datablocks
 */
void * leda_udpNdb_receive_obs (void * arg)
{
  udpNdb_t * ctx = (udpNdb_t *) arg;

  // multilogging facility
  multilog_t * log = ctx->log;

  // decoded sequence number
  uint64_t seq_no = 0;
  uint64_t raw_header;
  uint64_t tmp;
  unsigned char * b = (unsigned char *) ctx->sock->buf;

  // decoded channel id
  uint16_t ant_id = 0;
  unsigned int      fid = 0;
  unsigned int      xid = 0;

  // data received from a recv_from call
  size_t got = 0;

  // determine the sequence number boundaries for curr and next buffers
  int errsv;

  // offset of current packet in bytes from start of block
  int64_t byte_offset = 0;

  // offset of current packet in bytes from start of obs
  uint64_t seq_byte = 0;

  // for "saving" out of order packets near edges of blocks
  unsigned temp_idx[ctx->nhdus];
  unsigned temp_max = 80;
  char * temp_buffers[ctx->nhdus][temp_max][UDP_DATA];
  uint64_t temp_seq_byte[ctx->nhdus][temp_max];
  //unsigned int tmp_xid[temp_max];


  unsigned i = 0;
  int thread_result = 0;

  //temp_idx = (unsigned*) malloc(sizeof(unsigned) * ctx->nhdus);
  //assert (temp_idx);

  if (ctx->verbose)
    multilog(log, LOG_INFO, "leda_udpNdb_receive_obs()\n");

  // set the CPU that this thread shall run on
  if (ctx->recv_core >= 0)
  {
    multilog(log, LOG_INFO, "receive_obs: binding to core %d\n", ctx->recv_core);
    if (dada_bind_thread_to_core(ctx->recv_core) < 0)
      multilog(ctx->log, LOG_WARNING, "receive_obs: failed to bind to core %d\n", ctx->recv_core);
    multilog(log, LOG_INFO, "receive_obs: bound\n");
  }

  // set recording state once we enter this main loop
  recording = 1;

  // open hdus and first buffer for each

  for (i=0; i < ctx->nhdus; i++)
  {
    ctx->block_start_byte[i] = 0;
    ctx->block_end_byte[i] = ctx->block_start_byte[i] + ( ctx->packets_per_buffer - 1) * UDP_DATA;
    ctx->capture_started[i] = 0;
    temp_idx[i] = 0;
  }
  // TODO move the opening of the first block here ?
  //
  uint64_t timeouts = 0;
  uint64_t timeout_max = 1000000;

  // Continue to receive packets
  while (!quit_threads && !stop_pending) 
  {
    ctx->sock->have_packet = 0; 

    // incredibly tight loop to try and get a packet
    while (!ctx->sock->have_packet && !quit_threads && !stop_pending)
    {
      // receive 1 packet into the socket buffer
      got = recvfrom ( ctx->sock->fd, ctx->sock->buf, UDP_PAYLOAD, 0, NULL, NULL );

      if (got == UDP_PAYLOAD) 
      {
        ctx->sock->have_packet = 1;
      } 
      else if (got == -1) 
      {
        errsv = errno;
        if (errsv == EAGAIN) 
        {
          ctx->n_sleeps++;
          for (i = 0; i < ctx->nhdus; i++)
	  {
	          if (ctx->capture_started[i])
        	    timeouts++;
	  }
          if (timeouts > timeout_max)
          {
            multilog(log, LOG_INFO, "timeouts[%"PRIu64"] > timeout_max[%"PRIu64"]\n",timeouts, timeout_max);
            stop_byte = ctx->last_byte;
            stop_pending = 1;
          }
        } 
        else 
        {
          multilog (log, LOG_ERR, "receive_obs: recvfrom failed %s\n", strerror(errsv));
          thread_result = -1;
          pthread_exit((void *) &thread_result);
        }
      } 
      else // we received a packet of the WRONG size, ignore it
      {
        multilog (log, LOG_ERR, "receive_obs: received %d bytes, expected %d\n", got, UDP_PAYLOAD);
      }
    }
    timeouts = 0;

    // we have a valid packet within the timeout
    if (ctx->sock->have_packet) 
    {
      seq_no = UINT64_C(0);
      raw_header = be64toh (*(unsigned long long *) b); 
      seq_no = raw_header >> 16;
      xid = raw_header        & 0x00000000000000FF;
      fid = (raw_header >> 8) & 0x00000000000000FF;

      if (ctx->verbose > 2)
         multilog (ctx->log, LOG_INFO, "seq_no: [%"PRIu64"], xid: [%d], fid: [%d]\n",seq_no, xid, fid);
     

      //if (ctx->num_inputs == 1)
      //  fid = 0;

      

      // decode sequence number
      //leda_decode_header(ctx->sock->buf, &seq_no, &ant_id);

      // if first packet
      if (!ctx->capture_started[xid])
      {
        ctx->block_start_byte[xid] = ctx->num_inputs * seq_no * UDP_DATA;
        ctx->block_end_byte[xid]   = (ctx->block_start_byte[xid] + ctx->hdu_bufsz[xid]) - UDP_DATA;
        ctx->capture_started[xid] = 1;

        if (ctx->verbose)
          multilog (ctx->log, LOG_INFO, "receive_obs: START [%"PRIu64
                    " - %"PRIu64"], XID:%d\n", ctx->block_start_byte[xid], ctx->block_end_byte[xid],xid);
      }

      if (ctx->capture_started[xid])
      {
        seq_byte = (ctx->num_inputs * seq_no * UDP_DATA) + (fid * UDP_DATA);
        if (ctx->verbose > 3)
           multilog(ctx->log, LOG_INFO, "seq_byte=%"PRIu64", num_inputs=%d, UDP_DATA=%d\n",seq_byte,ctx->num_inputs, UDP_DATA);

        ctx->last_seq = seq_no;
        ctx->last_byte = seq_byte;

        // if packet arrived too late, ignore
        if (seq_byte < ctx->block_start_byte[xid])
        {
          multilog (ctx->log, LOG_INFO, "receive_obs: seq_byte < block_start_byte\n");
          ctx->packets->dropped++;
          ctx->bytes->dropped += UDP_DATA;
        }
        else
        {
          // packet belongs in this block
          if (seq_byte <= ctx->block_end_byte[xid])
          {
            byte_offset = seq_byte - ctx->block_start_byte[xid];
            memcpy (ctx->block[xid] + byte_offset, ctx->sock->buf + UDP_HEADER, UDP_DATA);
            ctx->packets->received++;
            ctx->bytes->received += UDP_DATA;
            ctx->block_count[xid]++;
          }
          // packet belongs in subsequent block
          else
          {
            if (ctx->verbose > 1)
	       multilog (log, LOG_INFO, "receive_obs: received packet for subsequent buffer: temp_idx=%d, ant_id=%d, seq_no=%"PRIu64", seq_byte=%"PRIu64", XID=%d\n",temp_idx[xid],fid,seq_no, seq_byte,xid);
            //multilog (log, LOG_INFO, "receive_obs: received packet for subsequent buffer: temp_idx=%d\n",temp_idx);
            if (temp_idx[xid] < temp_max)
            {
              // save packet to temp buffer
              memcpy (temp_buffers[xid][temp_idx[xid]], ctx->sock->buf, UDP_DATA);
              temp_seq_byte[xid][temp_idx[xid]] = seq_byte;
              //temp_xid[temp_idx] = xid;
              temp_idx[xid]++;
              if (ctx->verbose > 1)
	         multilog (log, LOG_INFO, "packet saved\n");
            }
            else
            {
              ctx->packets->dropped++;
              ctx->bytes->dropped += UDP_DATA;
            }
          }
        }
      }

      // now check for a full buffer or full temp queue
      if ((ctx->block_count[xid] >= ctx->packets_per_buffer) || (temp_idx[xid] >= temp_max))
      {
        if (ctx->verbose)
          multilog (log, LOG_INFO, "BLOCK COMPLETE seq_no=%"PRIu64", "
                    "ant_id=%"PRIu16", block_count=%"PRIu64", "
                    "temp_idx=%d, XID=%d\n", seq_no, ant_id,  ctx->block_count[xid], 
                    temp_idx[xid], xid);

        uint64_t dropped = ctx->packets_per_buffer - ctx->block_count[xid];
        if (dropped)
        {
          ctx->packets->dropped += dropped;
          ctx->bytes->dropped += (dropped * UDP_DATA);
        }

        // get a new buffer and write any temp packets saved 
        if (leda_udpNdb_new_buffer (ctx, xid) < 0)
        {
          multilog(ctx->log, LOG_ERR, "receive_obs: leda_udpNdb_new_buffer failed\n");
          thread_result = -1;
          pthread_exit((void *) &thread_result);
        }

        if (ctx->verbose > 1)
          multilog(log, LOG_INFO, "block bytes: %"PRIu64" - %"PRIu64"\n", ctx->block_start_byte[xid], ctx->block_end_byte[xid]);
  
        // include any futuristic packets we saved
        for (i=0; i < temp_idx[xid]; i++)
        {
          if (ctx->verbose > 1)
            multilog(log, LOG_INFO, "copying temp_idx data\n");
          seq_byte = temp_seq_byte[xid][i];
          byte_offset = seq_byte - ctx->block_start_byte[xid];
          if (byte_offset < ctx->hdu_bufsz[xid])
          {
            memcpy (ctx->block[xid] + byte_offset, temp_buffers[xid][i], UDP_DATA);
            ctx->block_count[xid]++;
            ctx->packets->received++;
            ctx->bytes->received += UDP_DATA;
          }
          else
          {
            ctx->packets->dropped++;
            ctx->bytes->dropped += UDP_DATA;
          }
        }
        temp_idx[xid] = 0;
      }
    }

    // packet has been inserted or saved by this point
    ctx->sock->have_packet = 0;

    // check for the stopping condition
    if (stop_byte)
    {
      if (seq_byte >= stop_byte)
      {
        if (ctx->verbose)
        {
          multilog(ctx->log, LOG_INFO, "receive_obs: STOP seq_byte[%"PRIu64"]"
                   " >= stop_byte[%"PRIu64"], stopping\n", seq_byte, stop_byte);
          multilog(ctx->log, LOG_INFO, "receive_obs: STOP buffer[%"PRIu64" - "
                   "%"PRIu64"]\n", ctx->block_start_byte[xid], ctx->block_end_byte[xid]);
        }
        stop_pending = 1;

        // try to determine how much data has been written
        uint64_t bytes_just_written = 0;
        if (seq_byte <= ctx->block_start_byte[xid])
          bytes_just_written = 1;
        else if (seq_byte < ctx->block_end_byte[xid])
          bytes_just_written = seq_byte - ctx->block_start_byte[xid];
        else
          bytes_just_written = ctx->hdu_bufsz[xid];

        if (ctx->verbose)
        {
          multilog(ctx->log, LOG_INFO, "receive_obs: STOP bytes_just_written=%"PRIu64"\n",
                   bytes_just_written);
        }

        // close buffer signalling EOD

        // while signal was only received for 1 xid, close all.
        for (i=0; i<ctx->nhdus; i++) {

          if (leda_udpNdb_close_buffer (ctx, bytes_just_written, 1, i) < 0)
          {
            multilog(ctx->log, LOG_ERR, "receive_obs: leda_udpNdb_close_hdu failed\n");
            thread_result = -1;
            pthread_exit((void *) &thread_result);
          }
        }
        stop_byte = 0;
        break;
      }
    }

    if (stop_pending) 
    {
      multilog(ctx->log, LOG_ERR, "receive_obs: stop_pending after break - SHOULD NOT HAPPEN!\n");
    }
  }

  // TODO move the closing of datablock here

  stop_pending = 0;

  if (quit_threads && ctx->verbose) 
    multilog (ctx->log, LOG_INFO, "main_function: quit_threads detected\n");
 
  if (ctx->verbose) 
    multilog(log, LOG_INFO, "receiving thread exiting\n");

  /* return 0 */
  pthread_exit((void *) &thread_result);
}

/*
 * Close the udp socket and file
 */

int udpNdb_stop_function (udpNdb_t* ctx)
{
  unsigned i;
  multilog_t * log = ctx->log;

  multilog(log, LOG_INFO, "stop: dada_hdu_unlock_write()\n");
  
  for (i=0; i < ctx->nhdus; i++)
  {
    if (dada_hdu_unlock_write (ctx->hdus[i]) < 0)
    {
      multilog (log, LOG_ERR, "stop: could not unlock write on\n");
      return -1;
    }
  }

  // close the UDP socket
  close(ctx->sock->fd);

  if (ctx->packets->dropped)
  {
    double percent = (double) ctx->bytes->dropped / (double) ctx->last_byte;
    percent *= 100;

    multilog(log, LOG_INFO, "bytes dropped %"PRIu64" / %"PRIu64 " = %8.6f %\n",
             ctx->bytes->dropped, ctx->last_byte, percent);
  }

  recording = 0;
  return 0;
}

int main (int argc, char **argv)
{

  /* DADA Logger */ 
  multilog_t* log = 0;

  /* Interface on which to listen for udp packets */
  char * interface = "any";

  /* port for control commands */
  int control_port = 0;

  /* port for incoming UDP packets */
  int inc_port = LEDA_DEFAULT_UDPDB_PORT;

  /* multilog output port */
  int l_port = LEDA_DEFAULT_PWC_LOGPORT;

  /* Flag set in daemon mode */
  char daemon = 0;

  /* Flag set in verbose mode */
  int verbose = 0;

  /* Number of x-engines to use */
  int nxeng = 1;

  /* number of seconds/bytes to acquire for */
  unsigned nsecs = 0;

  /* actual struct with info */
  udpNdb_t udpNdb;

  /* custom header from a file, implies no controlling pwcc */
  char * header_file = NULL;

  /* Pointer to array of "read" data */
  char *src;

  /* Ignore dropped packets */
  unsigned ignore_dropped = 0;

  // default shared memory key
  key_t dada_key = DADA_DEFAULT_BLOCK_KEY;

  // DADA Header + Data unit
  dada_hdu_t * hdu = 0;

  int arg = 0;

  int cpu_core = -1;

  unsigned int num_inputs = 1;

  /* statistics thread */
  pthread_t stats_thread_id;

  /* control thread */
  pthread_t control_thread_id;

  /* receiving thread */
  pthread_t receiving_thread_id;

  while ((arg=getopt(argc,argv,"b:c:df:i:x:l:n:o:p:t:vh")) != -1) {
    switch (arg) {

    case 'b':
      cpu_core = atoi(optarg);
      break; 

    case 'c':
      control_port = atoi(optarg);
      break; 

    case 'd':
      daemon = 1;
      break; 

    case 'f':
      header_file = strdup(optarg);
      break; 

    case 'i':
      if (optarg)
        interface = optarg;
      break;
    
    case 'l':
      if (optarg) {
        l_port = atoi(optarg);
        break;
      } else {
        usage();
        return EXIT_FAILURE;
      }

    case 'n':
      num_inputs = atoi(optarg);
      break;

    case 'o':
      control_port = atoi(optarg);
      break;

    case 'p':
      inc_port = atoi (optarg);
      break;

    case 't':
      nsecs = atoi (optarg);
      break;

    case 'x':
      nxeng = atoi (optarg);
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
  
  char * obs_header = 0;

  if (!control_port && !header_file)
  {
    fprintf(stderr, "ERROR: no control port or header file specified\n");
    usage();
    exit(EXIT_FAILURE);
  }

  // check the command line arguments
  if (!control_port)
  {
    obs_header = (char *) malloc(sizeof(char) * DADA_DEFAULT_HEADER_SIZE);
    if (!obs_header)
    {
      fprintf (stderr, "could not allocate memory\n");
      return (EXIT_FAILURE);
    }
    
    // read the ASCII DADA header from the file
    if (fileread (header_file, obs_header, DADA_DEFAULT_HEADER_SIZE) < 0)
    {
      free (obs_header);
      fprintf (stderr, "ERROR: could not read ASCII header from %s\n", header_file);
      return (EXIT_FAILURE);
    }
  }
    

  int i = 0;
  int rval = 0;
  void* result = 0;

  log = multilog_open ("leda_udpNdb_thread", 0);

  if (daemon)
    be_a_daemon ();
  else
    multilog_add (log, stderr);
  udpNdb.log = log;

  // initialize the data structure
  multilog (log, LOG_INFO, "main: leda_udpNdb_init_receiver()\n");
  if (leda_udpNdb_init_receiver (&udpNdb) < 0)
  {
    multilog (log, LOG_ERR, "could not initialize socket\n");
    return EXIT_FAILURE;
  }

  udpNdb.verbose = verbose;
  udpNdb.port = inc_port;
  udpNdb.recv_core = cpu_core;
  udpNdb.interface = strdup(interface);
  udpNdb.control_port = control_port;
  udpNdb.packets_per_buffer = 0;
  udpNdb.bytes_to_acquire = -1;
  udpNdb.num_inputs = num_inputs;
  udpNdb.nhdus = nxeng;

  leda_udpNdb_connect_hdus(&udpNdb, &(argv[optind]), nxeng);


  if (verbose)
    multilog(log, LOG_INFO, "main: leda_udpNdb_prepare()\n");
  if (leda_udpNdb_prepare (&udpNdb) < 0)
  {
    multilog(log, LOG_ERR, "could allocate required resources\n");
    return EXIT_FAILURE;
  }

  signal(SIGINT, signal_handler);

  // start the control thread
  if (control_port) 
  {
    if (verbose)
      multilog(log, LOG_INFO, "starting control_thread()\n");
    rval = pthread_create (&control_thread_id, 0, (void *) control_thread, (void *) &udpNdb);
    if (rval != 0) {
      multilog(log, LOG_INFO, "Error creating control_thread: %s\n", strerror(rval));
      return -1;
    }
  }

  if (verbose)
    multilog(log, LOG_INFO, "starting stats_thread()\n");
  rval = pthread_create (&stats_thread_id, 0, (void *) stats_thread, (void *) &udpNdb);
  if (rval != 0) {
    multilog(log, LOG_INFO, "Error creating stats_thread: %s\n", strerror(rval));
    return -1;
  }

  // main control loop
  while (!quit_threads) 
  {
    if (verbose)
      multilog(log, LOG_INFO, "main: leda_udpNdb_reset_receiver()\n");
    leda_udpNdb_reset_receiver (&udpNdb);

    // wait for a START command before initialising receivers
    while (!start_pending && !quit_threads && control_port) 
      sleep(1);

    if (quit_threads)
      break;

    // if header was supplied via text file, begin immediately
    if (header_file)
    {
      if (verbose)
        multilog(log, LOG_INFO, "main: leda_udpNdb_start()\n");
      time_t utc = leda_udpNdb_start (&udpNdb, obs_header);
      if (utc == -1 ) {
        multilog(log, LOG_ERR, "Could not run start function\n");
        return EXIT_FAILURE;
      }
    }

    /* set the total number of bytes to acquire */
    udpNdb.bytes_to_acquire = 1600 * 1000 * 1000 * (int64_t) nsecs;

    if (verbose)
    { 
      if (udpNdb.bytes_to_acquire) 
        multilog(log, LOG_INFO, "bytes_to_acquire = %"PRIu64" Million Bytes, nsecs=%d\n", udpNdb.bytes_to_acquire/1000000, nsecs);
      else
        multilog(log, LOG_INFO, "Acquiring data indefinitely\n");
    }

    //rval = pthread_create (&receiving_thread_id, &recv_attr, (void *) leda_udpNdb_receive_obs , (void *) &udpNdb);
    if (verbose)
      multilog(log, LOG_INFO, "starting leda_udpNdb_receive_obs thread\n");
    rval = pthread_create (&receiving_thread_id, 0, (void *) leda_udpNdb_receive_obs , (void *) &udpNdb);
    if (rval != 0) {
      multilog(log, LOG_INFO, "Error creating leda_udpNdb_receive_obs thread: %s\n", strerror(rval));
      return -1;
    }

    if (verbose) 
      multilog(log, LOG_INFO, "joining leda_udpNdb_receive_obs thread\n");
    pthread_join (receiving_thread_id, &result);

    if (verbose) 
      multilog(log, LOG_INFO, "udpNdb_stop_function\n");
    if ( udpNdb_stop_function(&udpNdb) != 0)
      fprintf(stderr, "Error stopping acquisition");


    if (!control_port)
      quit_threads = 1;

  }

  if (control_port)
  {
    if (verbose)
      multilog(log, LOG_INFO, "joining control_thread\n");
    pthread_join (control_thread_id, &result);
  }

  if (verbose)
    multilog(log, LOG_INFO, "joining stats_thread\n");
  pthread_join (stats_thread_id, &result);

  // clean up memory 
  if ( leda_udpNdb_destroy_receiver (&udpNdb) < 0) 
    fprintf(stderr, "failed to clean up receivers\n");

  // disconnect from HDU
  leda_udpNdb_destroy_hdus (&udpNdb);

  return EXIT_SUCCESS;
}


/*
 *  Thread to control the acquisition of data, allows only 1 connection at a time
 */
void control_thread (void * arg) 
{

  udpNdb_t * ctx = (udpNdb_t *) arg;

  if (ctx->verbose)
    multilog(ctx->log, LOG_INFO, "control_thread: starting\n");

  // port on which to listen for control commands
  int port = ctx->control_port;

  // buffer for incoming command strings
  int bufsize = 1024;
  char* buffer = (char *) malloc (sizeof(char) * bufsize);
  assert (buffer != 0);

  const char* whitespace = " \r\t\n";
  char * command = 0;
  char * args = 0;
  time_t utc_start = 0;

  FILE *sockin = 0;
  FILE *sockout = 0;
  int listen_fd = 0;
  int fd = 0;
  char *rgot = 0;
  int readsocks = 0;
  fd_set socks;
  struct timeval timeout;

  // create a socket on which to listen
  if (ctx->verbose)
    multilog(ctx->log, LOG_INFO, "control_thread: creating socket on port %d\n", port);

  listen_fd = sock_create (&port);
  if (listen_fd < 0)  {
    multilog(ctx->log, LOG_ERR, "Failed to create socket for control commands: %s\n", strerror(errno));
    free (buffer);
    return;
  }

  while (!quit_threads) {

    // reset the FD set for selecting  
    FD_ZERO(&socks);
    FD_SET(listen_fd, &socks);
    timeout.tv_sec = 1;
    timeout.tv_usec = 0;

    readsocks = select(listen_fd+1, &socks, (fd_set *) 0, (fd_set *) 0, &timeout);

    // error on select
    if (readsocks < 0) 
    {
      perror("select");
      exit(EXIT_FAILURE);
    }

    // no connections, just ignore
    else if (readsocks == 0) 
    {
    } 

    // accept the connection  
    else 
    {
   
      if (ctx->verbose) 
        multilog(ctx->log, LOG_INFO, "control_thread: accepting conection\n");

      fd =  sock_accept (listen_fd);
      if (fd < 0)  {
        multilog(ctx->log, LOG_WARNING, "control_thread: Error accepting "
                                        "connection %s\n", strerror(errno));
        break;
      }

      sockin = fdopen(fd,"r");
      if (!sockin)
        multilog(ctx->log, LOG_WARNING, "control_thread: error creating input "
                                        "stream %s\n", strerror(errno));


      sockout = fdopen(fd,"w");
      if (!sockout)
        multilog(ctx->log, LOG_WARNING, "control_thread: error creating output "
                                        "stream %s\n", strerror(errno));

      setbuf (sockin, 0);
      setbuf (sockout, 0);

      rgot = fgets (buffer, bufsize, sockin);

      if (rgot && !feof(sockin)) {

        buffer[strlen(buffer)-2] = '\0';

        args = buffer;

        // parse the command and arguements
        command = strsep (&args, whitespace);

        if (ctx->verbose)
        {
          multilog(ctx->log, LOG_INFO, "control_thread: command=%s\n", command);
          if (args != NULL)
            multilog(ctx->log, LOG_INFO, "control_thread: args=%s\n", args);
        }

        // REQUEST STATISTICS
        if (strcmp(command, "STATS") == 0) 
        {
          fprintf (sockout, "mb_rcv_ps=%4.1f,mb_drp_ps=%4.1f,"
                            "ooo_pkts=%"PRIu64",mb_free=%4.1f,mb_total=%4.1f\r\n", 
                             ctx->mb_rcv_ps, ctx->mb_drp_ps, 
                             ctx->ooo_packets, ctx->mb_free, ctx->mb_total);
          fprintf (sockout, "ok\r\n");
        }

        else if (strcmp(command, "SET_UTC_START") == 0)
        {
          if (ctx->verbose)
            multilog(ctx->log, LOG_INFO, "control_thread: SET_UTC_START command received\n");
          if (args == NULL)
          {
            multilog(ctx->log, LOG_ERR, "control_thread: no time specified for SET_UTC_START\n");
            fprintf(sockout, "fail\r\n");
          }
          else
          {
            time_t utc = str2utctime (args);
            if (utc == (time_t)-1)
            {
              multilog(ctx->log, LOG_WARNING, "control_thread: could not parse "
                       "UTC_START time from %s\n", args);
              fprintf(sockout, "fail\r\n");
            }
            else
            {
              if (ctx->verbose)
                multilog(ctx->log, LOG_INFO, "control_thread: parsed UTC_START as %d\n", utc);
              utc_start = utc;
              fprintf(sockout, "ok\r\n");
              multilog(ctx->log, LOG_INFO, "set_utc_start %s\n", args);
            }
          }
        }

        // START COMMAND
        else if (strcmp(command, "START") == 0) {

          if (ctx->verbose)
            multilog(ctx->log, LOG_INFO, "control_thread: START command received\n");

          start_pending = 1;
          while (recording != 1) 
          {
            sleep(1);
          }
          start_pending = 0;
          fprintf(sockout, "ok\r\n");

          if (ctx->verbose)
            multilog(ctx->log, LOG_INFO, "control_thread: recording started\n");
        }

        // FLUSH COMMAND - stop acquisition of data, but flush all packets already received
        else if (strcmp(command, "FLUSH") == 0)
        {
          if (ctx->verbose)
            multilog(ctx->log, LOG_INFO, "control_thread: FLUSH command received, stopping recording\n");

          stop_pending = 1;
          while (recording != 0)
          {
            sleep(1);
          }
          stop_pending = 0;
          fprintf(sockout, "ok\r\n");

          if (ctx->verbose)
            multilog(ctx->log, LOG_INFO, "control_thread: recording stopped\n");
        }

        // UTC_STOP command
        else if (strcmp(command, "UTC_STOP") == 0)
        {
          if (ctx->verbose)
            multilog(ctx->log, LOG_INFO, "control_thread: UTC_STOP command received\n");

          if (args == NULL) 
          {
            multilog(ctx->log, LOG_ERR, "control_thread: no UTC specified for UTC_STOP\n");
            fprintf(sockout, "fail\r\n");
          }
          else
          {
            time_t utc = str2utctime (args);
            if (utc == (time_t)-1) 
            {
              multilog(ctx->log, LOG_WARNING, "control_thread: could not parse "
                       "UTC_STOP time from %s\n", args);
              fprintf(sockout, "fail\r\n");
            }
            else
            {
              if (ctx->verbose)
                multilog(ctx->log, LOG_INFO, "control_thread: parsed UTC_STOP as %d\n", utc); 
              uint64_t byte_to_stop = (utc - utc_start);
              byte_to_stop *= 800 * 1000 * 1000;
              if (ctx->verbose)
                multilog(ctx->log, LOG_INFO, "control_thread: total_secs=%d, "
                         "stopping byte=%"PRIu64"\n", (utc - utc_start), byte_to_stop);
              stop_byte = byte_to_stop;
              stop_pending = 0;
              utc_start = 0;
              fprintf(sockout, "ok\r\n");
              multilog(ctx->log, LOG_INFO, "utc_stop %s\n", args);
            }
          }
        }

        // STOP command, stops immediately
        else if (strcmp(command, "STOP") == 0)
        {
          if (ctx->verbose)
            multilog(ctx->log, LOG_INFO, "control_thread: STOP command received, stopping immediately\n");

          stop_pending = 2;
          while (recording != 0)
          {
            sleep(1);
          }
          stop_pending = 0;
          fprintf(sockout, "ok\r\n");

          if (ctx->verbose)
            multilog(ctx->log, LOG_INFO, "control_thread: recording stopped\n");
        }


        // QUIT COMMAND, immediately exit 
        else if (strcmp(command, "QUIT") == 0) 
        {
          multilog(ctx->log, LOG_INFO, "control_thread: QUIT command received, exiting\n");
          quit_threads = 1;
          fprintf(sockout, "ok\r\n");
        }

        // UNRECOGNISED COMMAND
        else 
        {
          multilog(ctx->log, LOG_WARNING, "control_thread: unrecognised command: %s\n", buffer);
          fprintf(sockout, "fail\r\n");
        }
      }
    }

    close(fd);
  }
  close(listen_fd);

  free (buffer);

  if (ctx->verbose)
    multilog(ctx->log, LOG_INFO, "control_thread: exiting\n");

}

/* 
 *  Thread to print simple capture statistics
 */
void stats_thread(void * arg) {

  udpNdb_t * ctx = (udpNdb_t *) arg;
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
    fprintf (stderr,"R=%6.3f [Gb/s], D=%4.1f [MB/s], D=%"PRIu64" pkts, s_s=%"PRIu64"\n", gb_rcv_ps, mb_drp_ps, ctx->packets->dropped, s_rcv_1sec);

    sleep(1);
  }

}

/*
 *  Simple signal handler to exit more gracefully
 */
void signal_handler(int signalValue) {

  if (quit_threads) {
    fprintf(stderr, "received signal %d twice, hard exit\n", signalValue);
    exit(EXIT_FAILURE);
  }
  quit_threads = 1;

}
