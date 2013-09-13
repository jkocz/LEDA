/***************************************************************************
 *  
 *    Copyright (C) 2011 by Andrew Jameson
 *    Modified 2011/2012 by J.Kocz
 *    Licensed under the Academic Free License version 2.1
 * 
 ****************************************************************************/

#include "dada_client.h"
#include "dada_hdu.h"
#include "dada_def.h"
#include "leda_def.h"
#include "dada_generator.h"
#include "dada_affinity.h"
#include "ascii_header.h"

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <assert.h>
#include <math.h>
#include <byteswap.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <pthread.h>
#include <inttypes.h>

#define IDLE 1
#define ACTIVE 2
#define QUIT 3

void usage()
{
  fprintf (stdout,
           "leda_dbupdb_lookup [options] in_key out_key\n"
           " -c core   use core for thread 0, thread n uses core + n\n"
           " -n nthr   use nthr threads [defualt 1]\n"
           " -b num    bit promotion factor [default 2]\n"
           " -s        1 transfer, then exit\n"
           " -v        verbose mode\n");
}

#define UDP_DATA_64 UDP_DATA/4

typedef struct {

  // output DADA key
  key_t key;

  // output HDU
  dada_hdu_t * hdu;

  // bit promotion factor
  // arbitary bit promotion is not yet implemented
  // currently converts 4R+4C data into 8R+8C for 
  // efficient GPU reading
  unsigned bit_p;

  // number of bytes read
  uint64_t bytes_in;

  // number of bytes written
  uint64_t bytes_out;

  // verbose output
  int verbose;

  uint8_t * block;

  unsigned block_open;

  uint64_t bytes_written;

  pthread_cond_t * cond;

  pthread_mutex_t * mutex;

  unsigned nthreads;

  unsigned state;

  unsigned * thr_states;

  int * thr_cores;

  uint64_t * thr_start_packet;

  uint64_t * thr_end_packet;

  unsigned thread_count;

  uint8_t * d;

  unsigned nchan;

  unsigned npol;

  unsigned ndim;

} leda_dbupdb_t;

#define LEDA_DBUPDB_INIT { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }

/*! Function that opens the data transfer target */
int dbupdb_open (dada_client_t* client)
{

  // the leda_dbupdb specific data
  leda_dbupdb_t* ctx = 0;

  // status and error logging facilty
  multilog_t* log = 0;

  // header to copy from in to out
  char * header = 0;

  // header parameters that will be adjusted
  unsigned old_nbit = 0;
  unsigned new_nbit = 0;

  assert (client != 0);

  log = client->log;
  assert (log != 0);

  ctx = (leda_dbupdb_t *) client->context;
  assert (ctx != 0);

  if (ctx->verbose)
    multilog (log, LOG_INFO, "dbupdb_open()\n");

  // lock writer status on the out HDU
  if (dada_hdu_lock_write (ctx->hdu) < 0)
  {
    multilog (log, LOG_ERR, "cannot lock write DADA HDU (key=%x)\n", ctx->key);
    return -1;
  }

  if (ascii_header_get (client->header, "NBIT", "%d", &old_nbit) != 1)
  {
    old_nbit = 4; 
    multilog (log, LOG_WARNING, "header had no NBIT, assuming %d\n", old_nbit);
  }

  if (ascii_header_get (client->header, "NCHAN", "%d", &(ctx->nchan)) != 1)
  {
    ctx->nchan = 814;
    multilog (log, LOG_WARNING, "header had no NCHAN, assuming %d\n", ctx->nchan);
  }

  if (ascii_header_get (client->header, "NPOL", "%d", &(ctx->npol)) != 1)
  {
    ctx->npol = 2;
    multilog (log, LOG_WARNING, "header had no NPOL assuming %d\n", ctx->npol);
  }

  if (ascii_header_get (client->header, "NDIM", "%d", &(ctx->ndim)) != 1)
  {
    ctx->ndim = 2;
    multilog (log, LOG_WARNING, "header had no NDIM assuming %d\n", ctx->ndim);
  }

  if (ctx->verbose)
    multilog (log, LOG_INFO, "parsed old NBIT=%d, NCHAN=%d NPOL=%d NDIM=%d\n",
                             old_nbit, ctx->nchan, ctx->npol, ctx->ndim);

  new_nbit = ctx->bit_p * old_nbit;

  // get the header from the input data block
  uint64_t header_size = ipcbuf_get_bufsz (client->header_block);
  assert( header_size == ipcbuf_get_bufsz (ctx->hdu->header_block) );

  // get the next free header block on the out HDU
  header = ipcbuf_get_next_write (ctx->hdu->header_block);
  if (!header)  {
    multilog (log, LOG_ERR, "could not get next header block\n");
    return -1;
  }

  // copy the header from the in to the out
  memcpy ( header, client->header, header_size );

  // mark the outgoing header as filled
  if (ipcbuf_mark_filled (ctx->hdu->header_block, header_size) < 0)  {
    multilog (log, LOG_ERR, "Could not mark filled Header Block\n");
    return -1;
  }

  if (ctx->verbose) 
    multilog (log, LOG_INFO, "HDU (key=%x) opened for writing\n", ctx->key);

  client->transfer_bytes = 0;
  client->optimal_bytes = 64*1024*1024;

  ctx->bytes_in = 0;
  ctx->bytes_out = 0;
  ctx->bytes_written = 0; 
  client->header_transfer = 0;

  return 0;
}

/*! Function that closes the data transfer */
int dbupdb_close (dada_client_t* client, uint64_t bytes_written)
{
  // the leda_dbupdb specific data
  leda_dbupdb_t* ctx = 0;

  // status and error logging facility
  multilog_t* log;

  assert (client != 0);

  ctx = (leda_dbupdb_t*) client->context;

  assert (ctx != 0);
  assert (ctx->hdu != 0);

  log = client->log;
  assert (log != 0);

  if (ctx->verbose)
    multilog (log, LOG_INFO, "bytes_in=%llu, bytes_out=%llu\n", ctx->bytes_in, ctx->bytes_out );

  if (ctx->block_open)
  {
    if (ipcio_close_block_write (ctx->hdu->data_block, ctx->bytes_written) < 0)
    {
      multilog (log, LOG_ERR, "dbupdb_close: ipcio_close_block_write failed\n");
      return -1;
    }
    ctx->block_open = 0;
    ctx->bytes_written = 0;
  }


  if (dada_hdu_unlock_write (ctx->hdu) < 0)
  {
    multilog (log, LOG_ERR, "dbupdb_close: cannot unlock DADA HDU (key=%x)\n", ctx->key);
    return -1;
  }

  return 0;
}

/*! Pointer to the function that transfers data to/from the target via direct block IO*/
int64_t dbupdb_write_block (dada_client_t* client, void* in_data, uint64_t in_data_size, uint64_t in_block_id)
{

  assert (client != 0);
  leda_dbupdb_t* ctx = (leda_dbupdb_t*) client->context;
  multilog_t * log = client->log;

  if (ctx->verbose) 
    multilog (log, LOG_INFO, "write_block: processing %llu bytes\n", in_data_size);

  // current DADA buffer block ID (unused)
  uint64_t out_block_id = 0;

  int64_t bytes_read = in_data_size;

  // number of bytes to be written to out DB
  uint64_t bytes_to_write = in_data_size * ctx->bit_p;

  // input data pointer
  ctx->d = (uint8_t *) in_data;  

  if (ctx->verbose > 1)
    multilog (log, LOG_INFO, "block_write: opening block\n");

  // open output DB for writing
  if (!ctx->block_open)
  {
    ctx->block = (uint8_t *) ipcio_open_block_write(ctx->hdu->data_block, &out_block_id);
    ctx->block_open = 1;
  }

  // lock mutex
  pthread_mutex_lock (ctx->mutex);

  // prepare thread boundaries
  float n_pkts = (float) in_data_size / (float) UDP_DATA;
  float pkts_per_thr = n_pkts / ctx->nthreads;
  unsigned int_pkts_per_thr = (unsigned) floor (pkts_per_thr);
  unsigned mod_pkts_per_thr = int_pkts_per_thr - (int_pkts_per_thr % 4);
  unsigned i = 0;

  // adjust the bytes to write if this is not a nice multiple
  bytes_to_write = mod_pkts_per_thr * ctx->nthreads * UDP_DATA * ctx->bit_p;

  for (i=0; i < ctx->nthreads; i++)
  {
    ctx->thr_start_packet[i] = i * mod_pkts_per_thr;
    ctx->thr_end_packet[i]   = ctx->thr_start_packet[i] + mod_pkts_per_thr;
    ctx->thr_states[i] = ACTIVE;
  }
  ctx->state = ACTIVE;

  // AJ dont do this any more as we only want complete time samples to process
  //if (int_pkts_per_thr % 4 != 0)
  //  ctx->thr_end_packet[ctx->nthreads - 1] = (unsigned) n_pkts;

  // activate threads
  pthread_cond_broadcast (ctx->cond);
  pthread_mutex_unlock (ctx->mutex);

  // threads a working here...

  // wait for threads to finish
  pthread_mutex_lock (ctx->mutex);
  while (ctx->state == ACTIVE)
  {
    unsigned threads_finished = 0;
    while (!threads_finished)
    {
      threads_finished = 1;
      for (i=0; i<ctx->nthreads; i++)
      {
        if (ctx->thr_states[i] != IDLE)
          threads_finished = 0;
      }

      if (threads_finished)
        ctx->state = IDLE;
      else
        pthread_cond_wait (ctx->cond, ctx->mutex);
    }
  }
  pthread_mutex_unlock (ctx->mutex);

#ifdef _DEBUG_0_CHECK
  // check for any 0's in the output data block
  uint64_t j = 0;
  uint64_t nzeros = 0;
  for (j=0; j<in_data_size; j++)
  {
    if (j < (bytes_to_write/ctx->bit_p) && ((ctx->d[j] == 0) || (ctx->block[2*j] == 0) || (ctx->block[2*j+1] == 0)))
    {
      nzeros++;
      if (nzeros < 100)
        fprintf(stderr, "write_block: zeros j=%"PRIu64", in=%d, outp0=%d, outp1=%d\n", j, ctx->d[j], ctx->block[2*j], ctx->block[2*j+1]);
    } 
    else
    {
      if (nzeros > 0)
      {
        fprintf(stderr, "write_block:  recovery at j=%"PRIu64", in=%d, outp0=%d, outp1=%d\n", j, ctx->d[j], ctx->block[2*j], ctx->block[2*j+1]);
        nzeros = 0;

      } 
    }
  }
#endif

  // close output DB for writing
  if (ctx->block_open)
  {
    ipcio_close_block_write(ctx->hdu->data_block, bytes_to_write);
    ctx->block_open = 0;
    ctx->block = 0;
  }

  ctx->bytes_in += bytes_read;
  ctx->bytes_out += bytes_to_write;

  return bytes_read;

}

void * leda_dbudpdb_bitpromote_thread (void * arg)
{
  static const uint16_t lookup[256] =
  {
    0x0000, 0x1000, 0x2000, 0x3000, 0x4000, 0x5000, 0x6000, 0x7000,
    0x8000, 0x9000, 0xa000, 0xb000, 0xc000, 0xd000, 0xe000, 0xf000,
    0x1000, 0x1010, 0x2010, 0x3010, 0x4010, 0x5010, 0x6010, 0x7010,
    0x8010, 0x9010, 0xa010, 0xb010, 0xc010, 0xd010, 0xe010, 0xf010,
    0x2000, 0x1020, 0x2020, 0x3020, 0x4020, 0x5020, 0x6020, 0x7020,
    0x8020, 0x9020, 0xa020, 0xb020, 0xc020, 0xd020, 0xe020, 0xf020,
    0x3000, 0x1030, 0x2030, 0x3030, 0x4030, 0x5030, 0x6030, 0x7030,
    0x8030, 0x9030, 0xa030, 0xb030, 0xc030, 0xd030, 0xe030, 0xf030,
    0x4000, 0x1040, 0x2040, 0x3040, 0x4040, 0x5040, 0x6040, 0x7040,
    0x8040, 0x9040, 0xa040, 0xb040, 0xc040, 0xd040, 0xe040, 0xf040,
    0x5000, 0x1050, 0x2050, 0x3050, 0x4050, 0x5050, 0x6050, 0x7050,
    0x8050, 0x9050, 0xa050, 0xb050, 0xc050, 0xd050, 0xe050, 0xf050,
    0x6000, 0x1060, 0x2060, 0x3060, 0x4060, 0x5060, 0x6060, 0x7060,
    0x8060, 0x9060, 0xa060, 0xb060, 0xc060, 0xd060, 0xe060, 0xf060,
    0x7000, 0x1070, 0x2070, 0x3070, 0x4070, 0x5070, 0x6070, 0x7070,
    0x8070, 0x9070, 0xa070, 0xb070, 0xc070, 0xd070, 0xe070, 0xf070,
    0x8000, 0x1080, 0x2080, 0x3080, 0x4080, 0x5080, 0x6080, 0x7080,
    0x8080, 0x9080, 0xa080, 0xb080, 0xc080, 0xd080, 0xe080, 0xf080,
    0x9000, 0x1090, 0x2090, 0x3090, 0x4090, 0x5090, 0x6090, 0x7090,
    0x8090, 0x9090, 0xa090, 0xb090, 0xc090, 0xd090, 0xe090, 0xf090,
    0xa000, 0x10a0, 0x20a0, 0x30a0, 0x40a0, 0x50a0, 0x60a0, 0x70a0,
    0x80a0, 0x90a0, 0xa0a0, 0xb0a0, 0xc0a0, 0xd0a0, 0xe0a0, 0xf0a0,
    0xb000, 0x10b0, 0x20b0, 0x30b0, 0x40b0, 0x50b0, 0x60b0, 0x70b0,
    0x80b0, 0x90b0, 0xa0b0, 0xb0b0, 0xc0b0, 0xd0b0, 0xe0b0, 0xf0b0,
    0xc000, 0x10c0, 0x20c0, 0x30c0, 0x40c0, 0x50c0, 0x60c0, 0x70c0,
    0x80c0, 0x90c0, 0xa0c0, 0xb0c0, 0xc0c0, 0xd0c0, 0xe0c0, 0xf0c0,
    0xd000, 0x10d0, 0x20d0, 0x30d0, 0x40d0, 0x50d0, 0x60d0, 0x70d0,
    0x80d0, 0x90d0, 0xa0d0, 0xb0d0, 0xc0d0, 0xd0d0, 0xe0d0, 0xf0d0,
    0xe000, 0x10e0, 0x20e0, 0x30e0, 0x40e0, 0x50e0, 0x60e0, 0x70e0,
    0x80e0, 0x90e0, 0xa0e0, 0xb0e0, 0xc0e0, 0xd0e0, 0xe0e0, 0xf0e0,
    0xf000, 0x10f0, 0x20f0, 0x30f0, 0x40f0, 0x50f0, 0x60f0, 0x70f0,
    0x80f0, 0x90f0, 0xa0f0, 0xb0f0, 0xc0f0, 0xd0f0, 0xe0f0, 0xf0f0
  };

  leda_dbupdb_t* ctx = (leda_dbupdb_t*) arg;

  // lock the mutex to 
  pthread_mutex_lock (ctx->mutex);
  const unsigned ithread = ctx->thread_count;
  ctx->thread_count++;

  if (ctx->verbose > 1)
    fprintf(stderr, "[%d] bit promote thread starting\n", ithread);

  if (ctx->thr_cores[ithread] > 0)
  {
    if (ctx->verbose > 1)
      fprintf(stderr, "[%d] bit promote thread binding to %d\n", ithread, ctx->thr_cores[ithread]);
    if (dada_bind_thread_to_core ((int)ctx->thr_cores[ithread]) < 0)
      fprintf(stderr, "[%d] cannot bind to core %d\n",ithread,  ctx->thr_cores[ithread]);
  }

 
  // buffer for doing 4->8 bit coversion in vector, 4 packets in a loop
  uint8_t * in_dat = 0;
  uint8_t * out_dat = 0;
  uint16_t * out_dat_16 = 0;

  uint64_t ipkt;
  unsigned j = 0;
  const unsigned int nant_per_packet = 4; // how many _antennas_ (both pol) present per packet
  const unsigned int npacket_per_resolution = 64; // 64 (16*4 because 4 "fengines" / roach how many packets until complete set from different roachs 
  const unsigned int ntime_per_packet = 2;
  uint64_t out_time_sample_stride = 0;

  unsigned int in = 0;
  unsigned int ou = 0;
 
  unsigned int curr_chan = 0;


  while (ctx->thr_states[ithread] != QUIT)
  {
    while (ctx->thr_states[ithread] == IDLE)
      pthread_cond_wait (ctx->cond, ctx->mutex);

    if (ctx->thr_states[ithread] == QUIT)
    {
      pthread_mutex_unlock (ctx->mutex);
      pthread_exit (NULL);
    }
    // added "* ntime_per_packet" for the paper format 
    out_time_sample_stride = npacket_per_resolution * ctx->nchan * ntime_per_packet *  
                             nant_per_packet * ctx->ndim * ctx->npol; 

    if (ctx->verbose > 1)
    {
      fprintf(stderr, "out_time_sample_stride=%"PRIu64"\n", out_time_sample_stride);
      fprintf(stderr, "[%d] processing packets %lu - %lu\n", 
                    ithread, ctx->thr_start_packet[ithread],  ctx->thr_end_packet[ithread]);
    }

    // setup input and output pointers
    in_dat = (uint8_t *) ctx->d;
    in_dat += UDP_DATA * ctx->thr_start_packet[ithread];

    out_dat = (uint8_t *) ctx->block;
    out_dat += (UDP_DATA * ctx->thr_start_packet[ithread] * 2);

    out_dat_16 = (uint16_t *) out_dat;

    pthread_mutex_unlock (ctx->mutex);

    // First half of each packet contains 1 time sample for 407 chan, 4 Antenna, 2 pol, 2 dim, 4 bits / sample
    // changed to 1 time sample for 814 chan, 4 antenna, 2 pol, 2 dim, 4 bits/sample
    // changed to multiple time samples for variable chan, antenna, 2 pol, 2dim, 4bits/sample

    for (ipkt=ctx->thr_start_packet[ithread]; ipkt < ctx->thr_end_packet[ithread]; ipkt+=npacket_per_resolution)
    {
      // do 1 channel at a time for 4 pkts (j=8 --> j=nant_per_packet * npol);
      //for (j=0; j<UDP_DATA; j+=nant_per_packet*ctx->npol)
      for (j=0; j<UDP_DATA; j+=8)
      {
        in = j;
        ou = npacket_per_resolution * j;
	// having this in a loop costs ~ 400MB/s in throughput... (benchmarked for L64)

        //for (curr_chan = 0; curr_chan < (npacket_per_resolution-1); curr_chan++) 
        //for (curr_chan = 0; curr_chan < 3; curr_chan++) 

        //{

        // pkt 1 - npacket_per_resolution (LEDA32=4, LEDA64=8, LEDA512=64)
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a0p0
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a0p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1p1
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a3p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a3p1
        
        in += UDP_DATA_64;
        ou += 8;
     

        // pkt 2
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a4p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a4p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a5p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a5p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a6p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a6p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a7p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a7p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 3
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a8p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a8p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a9p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a9p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a10p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a10p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a11p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a11p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 4
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a12p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a12p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a13p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a13p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a14p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a14p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a15p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a15p1

        in += UDP_DATA_64;
        ou += 8;
  
        // pkt 5
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a16p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a16p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a17p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a17p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a18p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a18p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a19p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a19p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 6
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a20p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a20p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a21p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a21p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a22p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a22p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a23p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a23p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 7
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a24p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a24p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a25p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a25p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a26p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a26p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a27p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a27p1

        in += UDP_DATA_64;
        ou += 8;
        //}

        // pkt 8
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a28p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a28p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a29p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a29p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a30p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a30p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a31p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a31p1

        in += UDP_DATA_64;
        ou += 8;


        // pkt 9
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a32p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a32p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a33p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a33p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a34p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a34p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a35p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a35p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 10
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a36p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a36p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a37p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a37p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a38p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a38p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a39p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a39p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 11
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a40p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a40p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a41p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a41p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a42p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a42p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a43p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a43p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 12
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a44p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a44p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a45p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a45p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a46p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a46p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a47p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a47p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 13
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a48p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a48p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a49p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a49p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a50p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a50p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a51p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a51p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 14
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a52p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a52p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a53p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a53p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a54p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a54p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a55p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a55p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 15
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a56p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a56p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a57p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a57p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a58p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a58p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a59p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a59p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 16
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a60p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a60p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a61p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a61p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a62p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a62p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a63p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a63p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 17
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a64p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a64p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a65p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a65p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a66p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a66p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a67p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a67p1

        in += UDP_DATA_64;
        ou += 8;


        // pkt 18
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a68p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a68p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a69p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a69p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a70p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a70p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a71p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a71p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 19
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a72p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a72p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a73p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a73p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a74p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a74p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a75p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a75p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 20
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a76p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a76p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a77p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a77p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a78p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a78p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a79p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a79p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 21
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a80p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a80p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a81p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a81p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a82p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a82p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a83p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a83p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 22
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a84p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a84p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a85p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a85p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a86p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a86p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a87p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a87p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 23
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a88p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a88p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a89p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a89p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a90p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a90p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a91p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a91p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 24
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a92p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a92p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a93p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a93p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a94p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a94p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a95p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a95p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 25
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a96p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a96p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a97p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a97p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a98p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a98p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a99p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a9971

        in += UDP_DATA_64;
        ou += 8;

        // pkt 26
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a100p0   
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a100p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a101p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a101p1
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a102p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a102p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1030
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1031

        in += UDP_DATA_64;
        ou += 8;

        // pkt 27
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1040    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1041
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1050
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1051 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1060
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1061
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1070
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1071

        in += UDP_DATA_64;
        ou += 8;

        // pkt 28
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1080    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1081
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1090
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1091 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1100
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1101
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1110
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1111

        in += UDP_DATA_64;
        ou += 8;

        // pkt 29
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1120    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1121
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1130
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1131 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1140
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1141
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1150
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1151

        in += UDP_DATA_64;
        ou += 8;

        // pkt 30
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1160    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1161
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1170
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1171 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1180
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1181
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1190
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1991

        in += UDP_DATA_64;
        ou += 8;

        // pkt 31
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1200    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1201
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1210
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1211 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1220
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1221
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1230
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1231

        in += UDP_DATA_64;
        ou += 8;

        // pkt 32
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1240    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1241
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1250
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1251 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1260
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1261
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1270
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1271

        in += UDP_DATA_64;
        ou += 8;

        // pkt 33
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a128p0    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a128p1
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a129p0
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a129p1 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a130p0
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a130p1
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a131p0
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a131p1

        in += UDP_DATA_64;
        ou += 8;

        // pkt 34
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1320    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1321
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1330
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1331 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1340
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1341
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1350
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1351

        in += UDP_DATA_64;
        ou += 8;

        // pkt 35
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1360    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1361
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1370
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1371 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1380
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1381
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1390
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1391

        in += UDP_DATA_64;
        ou += 8;

        // pkt 36
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1400    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1401
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1410
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1411 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1420
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1421
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1430
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1431

        in += UDP_DATA_64;
        ou += 8;

        // pkt 37
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1440    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1441
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1450
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1451 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1460
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1461
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1470
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1471

        in += UDP_DATA_64;
        ou += 8;

        // pkt 38
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1480    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1481
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1490
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1491 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1500
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1501
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1510
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1511

        in += UDP_DATA_64;
        ou += 8;


        // pkt 39
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1520    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1521
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1530
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1531 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1540
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1541
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1550
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1551

        in += UDP_DATA_64;
        ou += 8;

        // pkt 40
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1560    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1561
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1570
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1571 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1580
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1581
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1590
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1591

        in += UDP_DATA_64;
        ou += 8;

        // pkt 41
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1600    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1601
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1610
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1611 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1620
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1621
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1630
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1631

        in += UDP_DATA_64;
        ou += 8;

        // pkt 42
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1640    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1641
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1650
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1651 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1660
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1661
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1670
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1671

        in += UDP_DATA_64;
        ou += 8;

        // pkt 43
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1680    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1681
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1690
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1691 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1700
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1701
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1710
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1711

        in += UDP_DATA_64;
        ou += 8;

        // pkt 44
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1720    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1721
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1730
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1731 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1740
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1741
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1750
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1751

        in += UDP_DATA_64;
        ou += 8;

        // pkt 45
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1760    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1761
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1770
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1771 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1780
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1781
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1790
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1791

        in += UDP_DATA_64;
        ou += 8;

        // pkt 46
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1800    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1801
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1810
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1811 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1820
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1821
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1830
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1831

        in += UDP_DATA_64;
        ou += 8;

        // pkt 47
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1840    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1841
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1850
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1851 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1860
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1861
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1870
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1871

        in += UDP_DATA_64;
        ou += 8;

        // pkt 48
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1880    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1881
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1890
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1891 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1900
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1901
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1910
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1911

        in += UDP_DATA_64;
        ou += 8;

        // pkt 49
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1920    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1921
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1930
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1931 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1940
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1941
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1950
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1951

        in += UDP_DATA_64;
        ou += 8;

        // pkt 50
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a1960    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a1961
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a1970
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a1971 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a1980
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a1981
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a1990
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a1991

        in += UDP_DATA_64;
        ou += 8;

        // pkt 51
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2000    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2001
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2010
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2011 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2020
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2021
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2030
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2031

        in += UDP_DATA_64;
        ou += 8;

        // pkt 52
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2040    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2041
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2050
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2051 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2060
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2061
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2070
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2071

        in += UDP_DATA_64;
        ou += 8;

        // pkt 53
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2080    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2081
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2090
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2091 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2100
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2101
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2110
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2111

        in += UDP_DATA_64;
        ou += 8;

        // pkt 54
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2120    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2121
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2130
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2131 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2140
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2141
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2150
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2151

        in += UDP_DATA_64;
        ou += 8;

        // pkt 55
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2160    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2161
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2170
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2171 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2180
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2181
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2190
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2191

        in += UDP_DATA_64;
        ou += 8;

        // pkt 56
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2200   
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2201
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2210
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2211 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2220
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2221
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2230
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2231

        in += UDP_DATA_64;
        ou += 8;

        // pkt 57
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2240    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2241
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2250
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2251 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2260
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2261
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2270
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2271

        in += UDP_DATA_64;
        ou += 8;

        // pkt 58
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2280    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2281
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2290
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2291 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2300
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2301
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2310
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2311

        in += UDP_DATA_64;
        ou += 8;

        // pkt 59
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2320    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2321
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2330
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2331 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2340
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2341
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2350
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2351

        in += UDP_DATA_64;
        ou += 8;

        // pkt 60
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2360    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2361
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2370
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2371 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2380
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2381
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2390
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2391

        in += UDP_DATA_64;
        ou += 8;

        // pkt 61
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2400    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2401
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2410
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2411 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2420
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2421
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2430
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2431

        in += UDP_DATA_64;
        ou += 8;

        // pkt 62
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2440    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2441
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2450
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2451 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2460
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2461
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2470
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2471

        in += UDP_DATA_64;
        ou += 8;

        // pkt 63
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2480    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2481
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2490
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2491 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2500
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2501
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2510
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2511

        in += UDP_DATA_64;
        ou += 8;

        // final packet
        out_dat_16[ou+0] = lookup[in_dat[in+0]];    // a2520    
        out_dat_16[ou+1] = lookup[in_dat[in+1]];    // a2521
        out_dat_16[ou+2] = lookup[in_dat[in+2]];    // a2530
        out_dat_16[ou+3] = lookup[in_dat[in+3]];    // a2531 
        out_dat_16[ou+4] = lookup[in_dat[in+4]];    // a2540
        out_dat_16[ou+5] = lookup[in_dat[in+5]];    // a2541
        out_dat_16[ou+6] = lookup[in_dat[in+6]];    // a2550
        out_dat_16[ou+7] = lookup[in_dat[in+7]];    // a2551


        // not required for final packet
        //in += UDP_DATA_64;
        //ou += 8;
      }

      // increment input ptr to next packet
      in_dat += UDP_DATA_64 * npacket_per_resolution;// * ntime_per_packet;
      out_dat += out_time_sample_stride * 4; // * 4 to account for the UDP_DATA_64 increment

      out_dat_16 = (uint16_t *) out_dat;
    }

    pthread_mutex_lock (ctx->mutex);
    ctx->thr_states[ithread] = IDLE;
    pthread_cond_broadcast (ctx->cond);
  }

  return 0;
}



/*! Pointer to the function that transfers data to/from the target */
int64_t dbupdb_write (dada_client_t* client, void* data, uint64_t data_size)
{
  fprintf(stderr, "dbupdb_write should be disabled!!!!!\n");

  return data_size;
}


int main (int argc, char **argv)
{
  /* DADA Data Block to Disk configuration */
  leda_dbupdb_t dbupdb = LEDA_DBUPDB_INIT;

  /* DADA Header plus Data Unit */
  dada_hdu_t* hdu = 0;

  /* DADA Primary Read Client main loop */
  dada_client_t* client = 0;

  /* DADA Logger */
  multilog_t* log = 0;

  /* Flag set in verbose mode */
  char verbose = 0;

  // bit promotion fator
  unsigned bit_p = 2;

  // number of processing threads
  unsigned n_threads = 1;

  // number of transfers
  unsigned single_transfer = 0;

  // core to run on
  int core = -1;

  // input data block HDU key
  key_t in_key = 0;

  // thread IDs
  pthread_t * ids = 0;

  int arg = 0;

  while ((arg=getopt(argc,argv,"c:dn:sv")) != -1)
  {
    switch (arg) 
    {
      
      case 'c':
        core = atoi(optarg);
        break;

      case 'n':
        n_threads= atoi(optarg);
        break;

      case 's':
        single_transfer = 1;
        break;

      case 'b':
        if (!optarg)
        {
          fprintf (stderr, "leda_dbupdb: -b requires argument\n");
          usage();
          return EXIT_FAILURE;
        }
        if (sscanf (optarg, "%d", &bit_p) != 1)
        {
          fprintf (stderr, "leda_dbupdb: could not parse bit_p from %s\n",optarg);
          usage();
          return EXIT_FAILURE;
        }
        break;
        
      case 'v':
        verbose++;
        break;
        
      default:
        usage ();
        return 0;
      
    }
  }

  dbupdb.verbose = verbose;
  dbupdb.bit_p = bit_p;

  int num_args = argc-optind;
  unsigned i = 0;
   
  if (dbupdb.bit_p != 2)
  {
    fprintf(stderr, "leda_dbupdb: bit promotion of 2 only supported\n");
    usage();
    exit(EXIT_FAILURE);
  }

  if (num_args != 2)
  {
    fprintf(stderr, "leda_dbupdb: must specify 2 datablocks\n");
    usage();
    exit(EXIT_FAILURE);
  } 

  if (verbose > 1)
    fprintf (stderr, "parsing input key=%s\n", argv[optind]);
  if (sscanf (argv[optind], "%x", &in_key) != 1) {
    fprintf (stderr, "leda_dbupdb: could not parse in key from %s\n", argv[optind]);
    return EXIT_FAILURE;
  }

  if (verbose > 1)
    fprintf (stderr, "parsing output key=%s\n", argv[optind+1]);
  if (sscanf (argv[optind+1], "%x", &(dbupdb.key)) != 1) {
    fprintf (stderr, "leda_dbupdb: could not parse out key from %s\n", argv[optind+1]);
    return EXIT_FAILURE;
  }

  log = multilog_open ("leda_dbupdb", 0);

  multilog_add (log, stderr);

  if (verbose)
    multilog (log, LOG_INFO, "main: creating in hdu\n");

  // open connection to the in/read DB
  hdu = dada_hdu_create (log);

  dada_hdu_set_key (hdu, in_key);

  if (dada_hdu_connect (hdu) < 0)
    return EXIT_FAILURE;

  if (verbose)
    multilog (log, LOG_INFO, "main: lock read key=%x\n", in_key);

  if (dada_hdu_lock_read (hdu) < 0)
    return EXIT_FAILURE;


  // open connection to the out/write DB
  dbupdb.hdu = dada_hdu_create (log);
  
  // set the DADA HDU key
  dada_hdu_set_key (dbupdb.hdu, dbupdb.key);
  
  // connect to the out HDU
  if (dada_hdu_connect (dbupdb.hdu) < 0)
  {
    multilog (log, LOG_ERR, "cannot connected to DADA HDU (key=%x)\n", dbupdb.key);
    return -1;
  } 

  pthread_cond_t cond = PTHREAD_COND_INITIALIZER;
  pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;

  // output DB block size must be bit_p times the input DB block size
  dbupdb.nthreads = n_threads;

  int64_t in_block_size = ipcbuf_get_bufsz ((ipcbuf_t *) hdu->data_block);
  int64_t out_block_size = ipcbuf_get_bufsz ((ipcbuf_t *) dbupdb.hdu->data_block);

  if (in_block_size * bit_p != out_block_size)
  {
    multilog (log, LOG_ERR, "output block size must be bit_p time the size of the input block size\n");
    dada_hdu_disconnect (hdu);
    dada_hdu_disconnect (dbupdb.hdu);
    return EXIT_FAILURE;
  }

  if (in_block_size % UDP_DATA != 0)
  {
    multilog (log, LOG_ERR, "input block size must be a multile of UDP payload\n");
    dada_hdu_disconnect (hdu);
    dada_hdu_disconnect (dbupdb.hdu);
    return EXIT_FAILURE;
  }

  dbupdb.cond = &cond;
  dbupdb.mutex = &mutex;

  pthread_cond_init( dbupdb.cond, NULL);
  pthread_mutex_init( dbupdb.mutex, NULL);

  dbupdb.thr_cores = (int *) malloc (dbupdb.nthreads * sizeof(int));
  dbupdb.thr_states = (unsigned *) malloc (dbupdb.nthreads * sizeof(unsigned));
  dbupdb.thr_start_packet = (uint64_t *) malloc (dbupdb.nthreads * sizeof(uint64_t));
  dbupdb.thr_end_packet = (uint64_t *) malloc (dbupdb.nthreads * sizeof(uint64_t));

  ids = (pthread_t *) malloc (dbupdb.nthreads * sizeof(pthread_t));
  for (i=0; i< dbupdb.nthreads; i++)
  {
    dbupdb.thr_cores[i] = -1;
    if (core >= 0)
      dbupdb.thr_cores[i] = core+i;
    else
    dbupdb.thr_states[i] = IDLE;

    pthread_create (&(ids[i]), 0,  leda_dbudpdb_bitpromote_thread, (void *) &dbupdb);
  }

  client = dada_client_create ();

  client->log = log;

  client->data_block   = hdu->data_block;
  client->header_block = hdu->header_block;

  client->open_function  = dbupdb_open;
  client->io_function    = dbupdb_write;
  client->io_block_function = dbupdb_write_block;

  client->close_function = dbupdb_close;
  client->direction      = dada_client_reader;

  client->context = &dbupdb;
  client->quiet = (verbose > 0) ? 0 : 1;

  while (!client->quit)
  {
    if (verbose)
      multilog (log, LOG_INFO, "main: dada_client_read()\n");

    if (dada_client_read (client) < 0)
      multilog (log, LOG_ERR, "Error during transfer\n");

    if (verbose)
      multilog (log, LOG_INFO, "main: dada_hdu_unlock_read()\n");

    if (dada_hdu_unlock_read (hdu) < 0)
    {
      multilog (log, LOG_ERR, "could not unlock read on hdu\n");
      return EXIT_FAILURE;
    }

    if (single_transfer)
      client->quit = 1;

    if (!client->quit)
    {
      if (dada_hdu_lock_read (hdu) < 0)
      {
        multilog (log, LOG_ERR, "could not lock read on hdu\n");
        return EXIT_FAILURE;
      }
    }
  }

  if (dada_hdu_disconnect (hdu) < 0)
    return EXIT_FAILURE;

  pthread_mutex_lock (dbupdb.mutex);
  while (dbupdb.state != IDLE)
    pthread_cond_wait (dbupdb.cond, dbupdb.mutex);

  for (i=0; i< dbupdb.nthreads; i++)
  {
    dbupdb.thr_states[i] = QUIT;
  }
  dbupdb.state = QUIT;

  pthread_cond_broadcast (dbupdb.cond);
  pthread_mutex_unlock (dbupdb.mutex);
    
  // join threads
  for (i=0; i<dbupdb.nthreads; i++)
    (void) pthread_join(ids[i], NULL);

  pthread_cond_destroy (dbupdb.cond);
  pthread_mutex_destroy (dbupdb.mutex);
  free(dbupdb.thr_states);
  free(dbupdb.thr_start_packet);
  free(dbupdb.thr_end_packet);
  free(ids);

  return EXIT_SUCCESS;
}

