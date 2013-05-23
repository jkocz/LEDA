// -*- c++ -*-

#include "dada_cuda.h"
#include "dada_client.h"
#include "dada_hdu.h"
#include "dada_def.h"
#include "multilog.h"
#include "ipcio.h"
#include "ipcbuf.h"
#include "dada_affinity.h"
#include "ascii_header.h"
#include "daemon.h"

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <assert.h>
#include <math.h>
#include <complex>
#include <limits.h>
#include <omp.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <inttypes.h>

/*
  Data ordering for input vectors is (running from slowest to fastest)
  [time][channel][station][polarization][complexity]

  actual data:
  we will have dropped some packets (udp)
  this will have to be compensated for in the unpacker. 
  - insert zeros/random repeat random sample?

  [frequency][station][pol][complex]

  Output matrix has ordering
  [channel][station][station][polarization][polarization][complexity]
*/

// uncomment to use 8-bit fixed point, comment out for 32-bit floating point

#define FIXED_POINT

// set the data type accordingly
#ifndef FIXED_POINT
typedef std::complex<float> ComplexInput;
#define COMPLEX_INPUT float2
#define SCALE 1.0f // no rescale required for FP32
#else
typedef std::complex<char> ComplexInput;
#define COMPLEX_INPUT char2 
#define SCALE 16129.0f // need to rescale result 
//#define SCALE 1.0f
#endif

#define REGISTER_TILE_TRIANGULAR_ORDER 3000
#define MATRIX_ORDER REGISTER_TILE_TRIANGULAR_ORDER

// size = freq * time * station * pol *sizeof(ComplexInput)
#define GBYTE (1024llu*1024llu*1024llu) 

//#define NFREQUENCY 814ll // num freq channels
//#define NFREQUENCY 40ll // num freq channels
#define NFREQUENCY 600ll // num freq channels
//#define NFREQUENCY 814ll // num freq channels
//#define NFREQUENCY 52ll // num freq channels
#define NPOL 2
//#define NSTATION 16ll
#define NSTATION 32ll
//#define NSTATION 256ll
#define NTIME 8192ll //SAMPLES / NFREQUENCY
//#define NTIME 24000ll //SAMPLES / NFREQUENCY
//#define NSTATION 16ll
//#define NSTATION 256ll
//#define NTIME 8192ll //SAMPLES / NFREQUENCY

//#define SIGNAL_SIZE GBYTE
#define TEST_BYTE (NFREQUENCY*NTIME*NSTATION*NPOL*sizeof(ComplexInput))
#define SIGNAL_SIZE TEST_BYTE
#define SAMPLES SIGNAL_SIZE / (NSTATION*NPOL*sizeof(ComplexInput))

#define NBASELINE ((NSTATION+1)*(NSTATION/2))
#define NDIM 2

#define NTIME_PIPE 1024
//#define NTIME_PIPE 4096

#define PIPE_LENGTH NTIME / NTIME_PIPE


// how many pulsars are we binning for (Not implemented yet)
#define NPULSAR 0

// whether we are writing the matrix back to device memory (used for benchmarking)
int writeMatrix = 1;
// this must be enabled for this option to work though, slightly hurts performance
//#define WRITE_OPTION 

/* 
  enable this option to receive data way the dada key
  system. Otherwise, random data will be generated locally
  and used.
*/
void leda_dbgpu_cleanup (dada_hdu_t * hdu_in, dada_hdu_t * hdu_out, multilog_t * log);
int dada_bind_thread_to_core (int core);


#define FROM_CPU 0
#define FROM_DADA 1

typedef std::complex<float> Complex;

Complex convert(const ComplexInput &b) {
  return Complex(real(b), imag(b));
}

int dada_bind_thread_to_core(int core)
{

  cpu_set_t set;
  pid_t tpid;

  CPU_ZERO(&set);
  CPU_SET(core, &set);
  tpid = syscall(SYS_gettid);

  if (sched_setaffinity(tpid, sizeof(cpu_set_t), &set) < 0) {
    fprintf(stderr, "failed to set cpu affinity: %s", strerror(errno));
    return -1;
  }

  CPU_ZERO(&set);
  if ( sched_getaffinity(tpid, sizeof(cpu_set_t), &set) < 0 ) {
    fprintf(stderr, "failed to get cpu affinity: %s", strerror(errno));
    return -1;
  }

  return 0;
}

/* 
   this file shouldn't need an output key, as it will write 
   the information to hd after unloading the gpu

*/

void usage()
{
  fprintf (stdout,
           "leda_dbgpu [options] in_key out_key\n"
           " -c core   bind process to CPU core\n"
           " -g dev    use specified cuda device [default 0]\n"
           " -v        verbose mode\n"
           " -h        print usage\n");
}

#include "cuda_xengine.cu"
#include "omp_xengine.cc"
#include "cpu_util.cc"

int main (int argc, char **argv)
{

  /* DADA Header plus Data Unit */
  dada_hdu_t* hdu_in = 0;
  dada_hdu_t* hdu_out = 0;

  /* DADA Logger */
  multilog_t* log = 0;

  /* Flag set in daemon mode */
  //char daemon = 0;

  /* Flag set in verbose mode */
  char verbose = 0;

  /* CUDA device to use */
  int device = 0;

  int core = -1;

  // input data block HDU key
  key_t in_key = 0;

  // output data block HDU key
  key_t out_key = 0;

  int arg = 0;

  while ((arg=getopt(argc,argv,"c:g:hv")) != -1)
  {
    switch (arg)
    {
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

      case 'g':
        device = atoi(optarg);
        break;

      case 'h':
        usage();
        return EXIT_SUCCESS;

      case 'v':
        verbose++;
        break;
    }
  }

  int num_args = argc-optind;

  if (num_args != 2)
  {
    usage();
    return EXIT_FAILURE;
  }

#if (FROM_DADA)      
  if (verbose)
    fprintf (stderr, "leda_dbgpu: parsing input key=%s\n", argv[optind]);
  if (sscanf (argv[optind], "%x", &in_key) != 1)
  {
    fprintf (stderr, "leda_dbgpu: could not parse in key from %s\n", argv[optind]);
    return EXIT_FAILURE;
  }

  if (verbose)
    fprintf (stderr, "leda_dbgpu: parsing output key=%s\n", argv[optind+1]);
  if (sscanf (argv[optind+1], "%x", &out_key) != 1)
  {
    fprintf (stderr, "leda_dbgpu: could not parse out key from %s\n", argv[optind+1]);
    return EXIT_FAILURE;
  }

  log = multilog_open ("leda_dbgpu", 0);

  multilog_add (log, stderr);

  if (verbose)
    multilog (log, LOG_INFO, "leda_dbgpu: creating in hdu\n");

  // open connection to the in/read DB
  hdu_in  = dada_hdu_create (log);
  dada_hdu_set_key (hdu_in, in_key);
  if (dada_hdu_connect (hdu_in) < 0)
    return EXIT_FAILURE;
  if (dada_hdu_lock_read (hdu_in) < 0)
    return EXIT_FAILURE;

  // open connection to the out/write DB
  hdu_out = dada_hdu_create (log);
  dada_hdu_set_key (hdu_out, out_key);
  if (dada_hdu_connect (hdu_out) < 0)
  { 
    leda_dbgpu_cleanup (hdu_in, hdu_out, log);
    return EXIT_FAILURE;
  }
  if (dada_hdu_lock_write(hdu_out) < 0)
  {
    leda_dbgpu_cleanup (hdu_in, hdu_out, log);
    return EXIT_FAILURE;
  }
#endif
  
  if (core >= 0)
  {
    if (verbose)
      fprintf(stderr, "binding to core %d\n", core);
    if (dada_bind_thread_to_core(core) < 0)
      fprintf(stderr, "dbgpu: failed to bind to core %d\n", core);
  }

  //int64_t bytes_read=0;
  bool observation_complete=0;

  // AJ: I think there should be a NDIM in here 2 JK: also a sizeof(element) -> taken care of below
  uint64_t bytes=NFREQUENCY*NSTATION*NPOL*NTIME; 

  // bytes to read times sizeof(ComplexInput) 
  bytes *= 2;
  //fprintf(stderr, "sizeof(ComplexInput): %d\n",sizeof(ComplexInput));

  fprintf(stderr, "main: bytes_to_read=%llu\n", bytes);
  //fprintf(stderr, "main: bytes_to_read=%"PRIu64"\n", bytes);

  int nstation = NSTATION;

#if FROM_DADA

  uint64_t header_size = 0;

  // read the header from the input HDU
  char * header_in = ipcbuf_get_next_read (hdu_in->header_block, &header_size);
  if (!header_in)
  {
    multilog(log ,LOG_ERR, "main: could not read next header\n");
    leda_dbgpu_cleanup (hdu_in, hdu_out, log);
    return EXIT_FAILURE;
  }

  // read the number of statinon from the header
  if (ascii_header_get (header_in, "NSTATIONS", "%d", &nstation) != 1)
  {
    nstation = NSTATION;
    multilog(log, LOG_WARNING, "Header with no nstation. Setting to %d\n", NSTATION);
  }

  // now write the output DADA header
  char * header_out = ipcbuf_get_next_write (hdu_out->header_block);
  if (!header_out)
  {
    multilog(log, LOG_ERR, "could not get next header block [output]\n");
    leda_dbgpu_cleanup (hdu_in, hdu_out, log);
    return EXIT_FAILURE;
  }

  // copy the in header to the out header
  memcpy (header_out, header_in, header_size);

  // need to change some DADA parameters
  if (ascii_header_set (header_out, "NBIT", "%d", 32) < 0)
    multilog(log, LOG_WARNING, "failed to set NBIT 32 in header_out\n");

  // mark the input header as cleared
  if (ipcbuf_mark_cleared (hdu_in->header_block) < 0)
  {
    multilog (log, LOG_ERR, "could not mark header block cleared [input]\n");
    leda_dbgpu_cleanup (hdu_in, hdu_out, log);
    return EXIT_FAILURE;
  }

  // mark the output header buffer as filled
  if (ipcbuf_mark_filled (hdu_out->header_block, header_size) < 0)
  {
    multilog (log, LOG_ERR, "could not mark header block filled [output]\n");
    leda_dbgpu_cleanup (hdu_in, hdu_out, log);
    return EXIT_FAILURE;
  }

#endif 

  printf("Correlating %llu stations with %llu signals, with %llu channels and integration length %llu\n",
	 NSTATION, SAMPLES, NFREQUENCY, NTIME);
    
  //unsigned long long vecLength = NFREQUENCY * NTIME * NSTATION * NPOL;
    
  // perform host memory allocation
  //int packedMatLength = NFREQUENCY * ((NSTATION+1)*(NSTATION/2)*NPOL*NPOL);
  
  // allocate the GPU X-engine memory
  
  // int64_t bytes_read = ipcio_read(hdu->data_block, (char*)buffer, bytes);
  ComplexInput *array_h = 0;
  Complex *cuda_matrix_h = 0;
  Complex *cuda_matrix_h_avg = 0;
  xInit(&array_h, &cuda_matrix_h, NSTATION, device);

#if (FROM_CPU)
  random_complex(array_h, vecLength);
#endif

  // register the data_block buffers with cuda_host_register
  dada_cuda_dbregister (hdu_in);

  uint64_t block_size = ipcbuf_get_bufsz ((ipcbuf_t *) hdu_in->data_block);
  uint64_t bytes_to_read;
  uint64_t block_id;
  char *   block;
  uint64_t ibyte;
  int      avg_index = 0;
#if (FROM_CPU)
  int      fd;
  char     filename [50];
#endif
  //uint64_t matrix_index=0;
  int      bytes_to_write = 0;
  uint64_t bytes_written=0;
  uint64_t written=0;

  matLength = NFREQUENCY * ((Nstation/2+1)*(Nstation/4)*NPOL*NPOL*4);// * (NPULSAR + 1);
  cuda_matrix_h_avg = (Complex *) malloc (matLength*sizeof(Complex));
  bytes_to_write = matLength*sizeof(Complex);

  while (!observation_complete)
  {
    
    // open a DADA block
    block = ipcio_open_block_read (hdu_in->data_block, &bytes_to_read, &block_id); 
    if (verbose)
    	multilog(log, LOG_INFO, "main: opened block %llu which contains %llu bytes\n", block_id, bytes_to_read);

    for (ibyte=0; ibyte < bytes_to_read; ibyte += bytes)
    {
      if (verbose)
      	multilog(log, LOG_INFO, "main: [%llu] ibyte=%llu bytes_to_read=%llu bytes=%llu\n", block_id, ibyte, bytes_to_read, bytes);

      // can cudaXengine handle non full buffer? probably not...
      if (ibyte + bytes > bytes_to_read)
        multilog(log, LOG_INFO, "main: skipping cudaXEngine as non full block\n");
      else
        cudaXengine(cuda_matrix_h,  (ComplexInput *) block);

      //for (matrix_index =0; matrix_index < matLength; matrix_index+=1) 
	//      fprintf(stdout, "block[%d]: %d\n",matrix_index,block[matrix_index]); 

      // increment the block pointer by the gulp amount (in bytes)
      block += bytes;

      //multilog(log, LOG_INFO, "main: xengine complete\n");

      //for (int matrix_index =0; matrix_index < matLength; matrix_index+=1) 
        //      fprintf(stdout, "cuda_matrix_h[%d]: %f + %fi\n",matrix_index,real(cuda_matrix_h[matrix_index]),imag(cuda_matrix_h[matrix_index])); 

	for (int matrix_index = 0; matrix_index < matLength; matrix_index++)
	 cuda_matrix_h_avg[matrix_index] += cuda_matrix_h[matrix_index];
//	for (int matrix_index = 0; matrix_index < matLength; matrix_index++)
//		cuda_matrix_h_avg[matrix_index] += cuda_matrix_h[matrix_index];

       if (avg_index < 25)
       {
          avg_index++;
	   //fprintf(stdout, "avg index %d\n",avg_index); 
       }
       else
       {
 	    avg_index=0;
#if FROM_DADA
           //if (verbose)
             multilog(log, LOG_INFO, "main: writing to datablock [output] %d bytes\n", bytes_to_write);
           //written = ipcio_write (hdu_out->data_block, (char *) cuda_matrix_h, bytes_to_write);
           written = ipcio_write (hdu_out->data_block, (char *) cuda_matrix_h_avg, bytes_to_write);
           if (written < bytes_to_write)
           {
             multilog(log, LOG_ERR, "main: failed to write all data to datablock [output]\n");
             leda_dbgpu_cleanup (hdu_in, hdu_out, log);
             return EXIT_FAILURE;
           }
           bytes_written += written;
           if (verbose)
             multilog(log, LOG_INFO, "main: write %llu bytes, %llu total\n", written, bytes_written);
	
#else
           //Complex *matrix_reorder = cuda_matrix_h;
           //reorderMatrix(matrix_reorder);
              
           //for (matrix_index = 0; matrix_index < matLength; matrix_index++)
		//fprintf(stdout, "outputMatrix[%d]: [%f] + [%f]i\n",matrix_index,real(matrix_reorder[matrix_index]),imag(matrix_reorder[matrix_index]));
           //for (matrix_index = 0; matrix_index < matLength; matrix_index++)
		//fprintf(stdout, "OrigMatrix[%d]: [%f] + [%f]i\n",matrix_index,real(cuda_matrix_h[matrix_index]),imag(cuda_matrix_h[matrix_index]));
           // print out matrix
           sprintf(filename, "%s_%llu", "utc_start", bytes_written); 
           fd = open (filename,O_WRONLY|O_CREAT, S_IWRITE);
           written = write(fd,cuda_matrix_h, bytes_to_write);
	   bytes_written = bytes_written + written;
	   close(fd);
	   multilog(log, LOG_INFO, "main: writing complete, wrote: %d\n", bytes_to_write);
#endif
          	   
           memset(cuda_matrix_h_avg, '\0', matLength*sizeof(Complex));
       }

    }

    if (bytes_to_read < block_size)
      observation_complete = 1;

    ipcio_close_block_read (hdu_in->data_block, bytes_to_read);

    // check for end of data in the DADA block
    if (ipcbuf_eod((ipcbuf_t*) hdu_in->data_block))
    {
      multilog(log, LOG_INFO, "main: end of data reached, exiting\n");
      observation_complete = 1;
    }

#if (FROM_CPU)
    observation_complete = 1;
#endif

  }
  
  // free gpu memory
  xFree(array_h, cuda_matrix_h);  
  free(cuda_matrix_h_avg);

#if (FROM_DADA)
  leda_dbgpu_cleanup (hdu_in, hdu_out, log);
#endif
    
  return EXIT_SUCCESS;
}


void leda_dbgpu_cleanup (dada_hdu_t * in, dada_hdu_t * out, multilog_t * log)
{
  if (dada_hdu_unlock_read (in) < 0)
  {
    multilog(log, LOG_ERR, "could not unlock read on hdu_in\n");
  }
  dada_hdu_destroy (in);

  if (dada_hdu_unlock_write (out) < 0)
  {
    multilog(log, LOG_ERR, "could not unlock write on hdu_out\n");
  }
  dada_hdu_destroy (out);
}
