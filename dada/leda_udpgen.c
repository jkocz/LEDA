#include <stdlib.h> 
#include <stdio.h> 
#include <errno.h> 
#include <string.h> 
#include <sys/types.h> 
#include <netinet/in.h> 
#include <netdb.h> 
#include <sys/socket.h> 
#include <sys/wait.h> 
#include <sys/timeb.h> 
#include <math.h>
#include <pthread.h>
#include <assert.h>

#include "daemon.h"
#include "multilog.h"
#include "leda_def.h"
#include "leda_udp.h"

#include "arch.h"
#include "Statistics.h"
#include "RealTime.h"
#include "StopWatch.h"

#define MIN(x,y) (x < y ? x : y)
#define MAX(x,y) (x > y ? x : y)

#define LEDA_UDPGEN_LOG  49200

/* Cross thread global variables */
unsigned int scale0 = 4096;
unsigned int scale1 = 4096;
int bit_value = 0;
int regenerate_signal = 0;
int reselect_bits = 0;
int reset_sequence = 0;
int num_arrays = 1;

/* 32 bit values before bit selection */
unsigned int ** pol0_raw;
unsigned int ** pol1_raw;

/* Bit selected values 8 bit */
char ** pol0_bits;
char ** pol1_bits;

/* packet bits */
char ** packed_signals;

/* the current signal to send */
int s = 0;

/* Generation & encoding functions */
void create_memory_arrays(int num, int length);
void generate_test_data(int num, int length, int noise, int gain); 
void free_memory_arrays(int num);
void bit_select(int num, int length, int bit_value);
void pack_pols();

/* Debug / display functions */
void print_bram_line(FILE * fp, unsigned int i, unsigned int value, char * binary);
void signal_handler(int signalValue);
void usage();
void quit();
void tcpip_control(void);
unsigned reverse (unsigned value, unsigned N);
void reverse_array(char *array, int array_size);

int main(int argc, char *argv[])
{

  /* number of microseconds between packets */
  double sleep_time = 22;
 
  /* be verbose */ 
  int verbose = 0;

  /* udp port to send data to */
  int dest_port = LEDA_DEFAULT_UDPDB_PORT;

  /* UDP socket struct */
  struct sockaddr_in dagram;

  /* total time to transmit for */ 
  uint64_t transmission_time = 5;   

  /* DADA logger */
  multilog_t *log = 0;

  /* Hostname to send UDP packets to */
  char *dest_host;

  /* udp file descriptor */
  int udpfd;

  /* The generated signal arrays */
  char packet[UDP_PAYLOAD];

  /* data rate */
  unsigned int data_rate_mbytes = 50;

  /* number of packets to send every second */
  uint64_t packets_ps = 0;

  /* start of transmission */
  time_t start_time;

  /* end of transmission */
  time_t end_time;

  // packet sequence number
  uint64_t seq_no = 0;

  // antenna Identifier
  uint16_t ant_id;

  unsigned num_ant = 1;

  opterr = 0;
  int c;
  while ((c = getopt(argc, argv, "a:hn:p:r:v")) != EOF) {
    switch(c) {

      case 'a':
        num_ant = atoi(optarg);
        break;

      case 'h':
        usage();
        exit(EXIT_SUCCESS);
        break;

      case 'n':
        transmission_time = atoi(optarg);
        break;

      case 'p':
        dest_port = atoi(optarg);
        break;

      case 'r':
        data_rate_mbytes = atoi(optarg);
        break;

      case 'v':
        verbose++;
        break;

      default:
        usage();
        return EXIT_FAILURE;
        break;
    }
  }

  // Check arguments
  if ((argc - optind) != 1) 
  {
    fprintf(stderr,"ERROR: 1 command line argument expected [destination host]\n");
    usage();
    return EXIT_FAILURE;
  }

  // destination host
  dest_host = strdup(argv[optind]);

  seq_no = 0;
  ant_id = 0;

  signal(SIGINT, signal_handler);

  // do not use the syslog facility
  log = multilog_open ("leda_udpgen", 0);

  multilog_add(log, stderr);

  double data_rate = (double) data_rate_mbytes;
  data_rate *= 1024*1024;

  if (verbose)
  {
    multilog(log, LOG_INFO, "sending UDP data to %s:%d\n", dest_host, dest_port);
    if (data_rate)
      multilog(log, LOG_INFO, "data rate: %5.2f MB/s \n", data_rate/(1024*1024));
    else
      multilog(log, LOG_INFO, "data_rate: fast as possible\n");
    multilog(log, LOG_INFO, "transmission length: %d seconds\n", transmission_time);
  }

  // create the socket for outgoing UDP data
  dada_udp_sock_out(&udpfd, &dagram, dest_host, dest_port, 0, "192.168.1.255");

  uint64_t data_counter = 0;

  // initialise data rate timing library 
  StopWatch wait_sw;
  RealTime_Initialise(1);
  StopWatch_Initialise(1);

  /* If we have a desired data rate, then we need to adjust our sleep time
   * accordingly */
  if (data_rate > 0)
  {
    packets_ps = floor(((double) data_rate) / ((double) UDP_PAYLOAD));
    sleep_time = (1.0/packets_ps) * 1000000.0;

    if (verbose)
    {
      multilog(log, LOG_INFO, "packets/sec %"PRIu64"\n",packets_ps);
      multilog(log, LOG_INFO, "sleep_time %f us\n",sleep_time);
    }
  }

  // seed the random number generator with current time
  srand ( time(NULL) );

  uint64_t total_bytes_to_send = data_rate * transmission_time;

  // assume 10GbE speeds
  if (data_rate == 0)
    total_bytes_to_send = 1*1024*1024*1024 * transmission_time;

  size_t bytes_sent = 0;
  uint64_t total_bytes_sent = 0;

  uint64_t bytes_sent_thistime = 0;
  uint64_t prev_bytes_sent = 0;
  
  time_t current_time = time(0);
  time_t prev_time = time(0);

  multilog(log,LOG_INFO,"Total bytes to send = %"PRIu64"\n",total_bytes_to_send);
  multilog(log,LOG_INFO,"UDP payload = %"PRIu64" bytes\n",UDP_PAYLOAD);
  multilog(log,LOG_INFO,"UDP data size = %"PRIu64" bytes\n",UDP_DATA);
  multilog(log,LOG_INFO,"Wire Rate\t\tUseful Rate\tPacket\tSleep Time\n");

  unsigned int s_off = 0;

  while (total_bytes_sent < total_bytes_to_send) 
  {
    if (data_rate)
      StopWatch_Start(&wait_sw);

    // write the custom header into the packet
    leda_encode_header(packet, seq_no, ant_id);

    bytes_sent = dada_sock_send(udpfd, dagram, packet, (size_t) UDP_PAYLOAD); 

    if (bytes_sent != UDP_PAYLOAD) 
      multilog(log,LOG_ERR,"Error. Attempted to send %d bytes, but only "
                           "%"PRIu64" bytes were sent\n",UDP_PAYLOAD,
                           bytes_sent);

    // this is how much useful data we actaully sent
    total_bytes_sent += (bytes_sent - UDP_HEADER);

    data_counter++;
    prev_time = current_time;
    current_time = time(0);
    
    if (prev_time != current_time) 
    {
      double complete_udp_packet = (double) bytes_sent;
      double useful_data_only = (double) (bytes_sent - UDP_HEADER);
      double complete_packet = 28.0 + complete_udp_packet;

      double wire_ratio = complete_packet / complete_udp_packet;
      double useful_ratio = useful_data_only / complete_udp_packet;
        
      uint64_t bytes_per_second = total_bytes_sent - prev_bytes_sent;
      prev_bytes_sent = total_bytes_sent;
      double rate = ((double) bytes_per_second) / (1024*1024);

      double wire_rate = rate * wire_ratio;
      double useful_rate = rate * useful_ratio;
             
      multilog(log,LOG_INFO,"%5.2f MB/s  %5.2f MB/s  %"PRIu64
                            "  %5.2f, %"PRIu64"\n",
                            wire_rate, useful_rate, data_counter, sleep_time,
                            bytes_sent);
    }

    ant_id = (ant_id + 1) % num_ant;
    if (num_ant == 1)
      seq_no++;
    else if (ant_id == 0)
      seq_no++;
    else
      ;

    if (data_rate)
      StopWatch_Delay(&wait_sw, sleep_time);
  }

  uint64_t packets_sent = seq_no;

  multilog(log, LOG_INFO, "Sent %"PRIu64" bytes\n",total_bytes_sent);
  multilog(log, LOG_INFO, "Sent %"PRIu64" packets\n",packets_sent);

  close(udpfd);
  free (dest_host);

  return 0;
}


void signal_handler(int signalValue) {
  exit(EXIT_SUCCESS);
}

void usage() 
{
  fprintf(stdout,
    "leda_udpgen [options] host\n"
    "-a ant        number of antennae to simulate\n"
    "-h            print this help text\n"
    "-n secs       number of seconds to transmit [default 5]\n"
    "-p port       destination udp port [default %d]\n"
    "-r rate       transmit at rate MB/s [default 50]\n"
    "-v            verbose output\n"
    "host          destination host name\n\n"
    ,LEDA_DEFAULT_UDPDB_PORT);
}
