/* ASP MCS software */
/**********************************************
Alpha release of ASP-MCS firmware, 6/12/10
author:  Joe Craig, University of New Mexico

Notes:
Multiple (daisy-chained) ARX boards supported (up to 33)
This release supports the RPT command with individual MIB entries only (no branching)
Real-time clock not yet implemented (MJD is always what MCS sends, MPM is what MCS sends + one msec)
Summary field is always NORMAL (ERROR does not exist)
FIL, AT1, AT2, ATS; Stand value 000 (apply to all) is not implemented
SHT command forces all to max attn, filters off, FEE pwr off (pre-INI state)
Power supply interface not implemented (RXP, FEP)
Temperature Sensors are not installed, but RPT mock data

Caveat:  The Din (feedback logic) is not implemented, so there is no guarantee that the SPI commands issued actually changed the setting in the ARX boards

Rabbit RCM4200 SPI Bus pins:
SCLK on PE7
DOUT (MOSI) on PC2
DIN (MISO) on PE3
CS on PB7
************************************************/

#class auto
#define TCPCONFIG           1
#define _PRIMARY_STATIC_IP  "192.168.25.2"		//ASP IP Address
//#define _PRIMARY_STATIC_IP  "10.1.1.40"		//ASP IP Address
#define _PRIMARY_NETMASK    "255.255.255.0"
#define MY_GATEWAY          "192.168.25.1"			//Network Gateway

#define MAX_UDP_SOCKET_BUFFERS 2

#define LOCAL_PORT 	1738
#define REMOTE_PORT 	1739

#define REMOTE_IP 	"192.100.16.226"				//MCS IP Address

#define SPI_SER_C
#define SPI_RX_PORT SPI_RX_PE
#define SPI_CLK_DIVISOR 100

#use "spi.lib"
#use rcm42xx.lib

#memmap xmem
#use "dcrtcp.lib"

udp_Socket sock;

#include MIB.h
#include funcDec.h
#include func.h

void main()
{
   initMIB();
   setSPIconst();
   brdInit();
   WrPortI(PCFR,&PCFRShadow,PCFRShadow | 0x44);     	// Serial Port C
   WrPortI(PEAHR,&PEAHRShadow,PEAHRShadow | 0xC0);    // Serial Port C
   WrPortI(PEDDR,&PEDDRShadow,PEDDRShadow | 0x80);    // Serial Port C clock on PE7
   WrPortI(PEFR,&PEFRShadow,PEFRShadow | 0x80);     	// Serial Port C
	SPIinit();
   // Start network and wait for interface to come up (or error exit).
	sock_init_or_exit(1);
   //open RX port
	if(!udp_open(&sock, LOCAL_PORT, resolve(REMOTE_IP), 0, NULL)) {
		printf("udp_open failed!\n");
		exit(0);
   }
   init = 0;	//boots up uninitialized
   nBoards = 0;
   nChP = 0;
	// receive & transmit packets/
	for(;;) {
      tcp_tick(NULL);
		if (1 == receive_packet()){
      	udp_close(&sock);		//close the RX port
         //open TX port
			if(!udp_open(&sock, LOCAL_PORT, resolve(REMOTE_IP), REMOTE_PORT, NULL)) {
				printf("udp_open failed!\n");
				exit(0);
			}
      	send_packet();
         udp_close(&sock);		//close the TX port
      }
      //reopen RX port
		if(!udp_open(&sock, LOCAL_PORT, resolve(REMOTE_IP), 0, NULL)) {
			printf("udp_open failed!\n");
			exit(0);
		}
	}
}

