/*************************************************************************
    SAXMCS.C
    Switching assembly rabbit control firmware. Previously pulse_gen.c
    Coded up by John Test   (CfA) Aug 2013.
    Modified by Danny Price (CfA) Dec 2013.

    Based off:
    Samples\SPI\spi_test.c

    ZWorld, 2001

    test out SPI driver with an NS ADC0831 chip. Uses serial channel B for
    the SPI data.

    PB7 acts as the CS line on the ADC
    PB0 is the serial B clock line(SCLK)

    PC4 is the data output(MOSI)
    PC5 is the data input(MISO)

    Reads two bytes worth with each chip select.
    The first two bits are not part of the data. They are always 1 and
    then 0 .  This is followed by 8 bits of data for the sample, and
    then 6 extra bits.

************************************************************************/

#class auto

#define SPI_SER_B
#define SPI_CLK_DIVISOR 10
#define USE_LINKLOCAL
#define TCPCONFIG       1

// LEDA-OVRO IP config
#define _PRIMARY_STATIC_IP  "192.168.25.7"
#define _PRIMARY_NETMASK    "255.0.0.0"
#define MY_GATEWAY          "192.100.16.225"
#define MY_NAMESERVER       "192.100.16.2"

// CfA IP config
//#define _PRIMARY_STATIC_IP  "131.142.12.62"
//#define _PRIMARY_NETMASK    "255.255.248.0"
//#define MY_GATEWAY          "131.142.8.1"
//#define MY_NAMESERVER       "131.142.10.1"

#use "costate.lib"
#use "dcrtcp.lib"
#use RCM42xx.LIB
#memmap xmem

#define PORT 1738
#define TRUE 1
#define FALSE 0
#define DS2_BIT 2
#define DS3_BIT 3
#define S2_BIT  4
#define S3_BIT  5

/* the default mime type for '/' must be first */
void my_isr0();
void my_isr1();
void setup_isr0( void );
void setup_isr1( void );
void disable_isr( void );
void disable_isr1( void );
void enable_isr( void );
void enable_isr1( void );
void hold_pattern( void );
void hold_pattern_hot( void );
void hold_pattern_cold( void );
void switch_mode( void );
void cycle_switch( void );

char str_start[] = "start";
char str_stop[]  = "stop";
char str_hold[]  = "hold";
char str_hot[]   = "hold_hot";
char str_cold[]  = "hold_cold";
char str_sky[]   = "hold_sky";
int count;
int index;
int switch_enable;
int line_out[] = {0, 2, 4};
int int1;
int int2;

tcp_Socket socket, socket2;

void main()
{
   char message[512] = {0};
   char buffer[512];
   char adc_reading[2];
   char func1_reg_val[3];
   char func2_reg_val[2];
   char chan_phase_offset_word[2];
   int i, j;
   int adc_sample;
   int channel_selection;
   char phase_offset[10];
   char IF_num[10];
   int bytes_read, isafloat;
   char *result;

   brdInit();
   sock_init_or_exit(1);
   BitWrPortI(PADR, &PADRShadow, 1, 0);
   BitWrPortI(PADR, &PADRShadow, 0, 1);
   BitWrPortI(PADR, &PADRShadow, 0, 2);
   setup_isr0();
   count = 0;
   index = 0;
   switch_enable = 0;

   /************************************************************************/
   /************************************************************************/

   while(1) {
        tcp_listen(&socket,PORT,0,0,NULL,0);
        printf("Waiting for connection...\n");
          while(!sock_established(&socket) && sock_bytesready(&socket)==-1)
            tcp_tick(NULL);
        printf("Connection received...\n");

        do {
            bytes_read=sock_fastread(&socket,buffer,sizeof(buffer)-1);
            isafloat = 0;
            if(bytes_read>0) {
                buffer[bytes_read]=0;
                //     printf("%s",buffer);
            result = buffer;
            result[strcspn(result,"\n")] = '\0';
            //   printf("result size is %d\n", strlen(result));
            //   parse_input(result);
            //   my_input = (strtok(result, " "));
            //   printf("The input is %s\n", result);
           if (strcmp(result, str_start) == 0){
            /*  if (int2 == 1)
                 disable_isr1();   */
              if (int1 == 0)
              {
                enable_isr();
                switch_enable = 0;
              }
           strcat(message, "start enabled\n");
           sock_fastwrite(&socket,message,512);
           message[0] = '\0';
         //     printf("Stop walshing\n");
         //     disable_isr();
           
        /*********  enable the isr register to read 1 pps  */
          }
           else if(strcmp(result, str_stop) == 0){
           //   printf("enabling \n");  a
              if(int1 == 1)
                 disable_isr();
             /* if (int2 == 0)
                 enable_isr1();  */
              strcat(message, "switch enabled\n");
              sock_fastwrite(&socket,message,512);
              message[0] = '\0';
                 switch_enable = 1;
                 switch_mode();
             /* strcat(message, "switch enabled\n");
              sock_fastwrite(&socket,message,512);
              message[0] = '\0';          */
           // disable the isr
           }
           else if(strcmp(result, str_hold) == 0){
             //  printf("reset, wait for SOW");
             //  disable_isr();
             //  enable_isr1();
             // disable the isr.  Set the read to the pushbutton
             strcat(message, "hold enabled\n");
             sock_fastwrite(&socket,message,512);
             message[0] = '\0';
             hold_pattern();
           }
           else if(strcmp(result, str_sky) == 0){
             strcat(message, "hold sky enabled\n");
             sock_fastwrite(&socket,message,512);
             message[0] = '\0';
             hold_pattern();
           }
           else if(strcmp(result, str_cold) == 0){
             strcat(message, "hold cold enabled\n");
             sock_fastwrite(&socket,message,512);
             message[0] = '\0';
             hold_pattern_cold();
           }
           else if(strcmp(result, str_hot) == 0){
             strcat(message, "hold hot enabled\n");
             sock_fastwrite(&socket,message,512);
             message[0] = '\0';
             hold_pattern_hot();
           }
           else
           {
              printf("Invalid entry\n");
           }
            }
        } while(tcp_tick(&socket));
     }
}

void toggle_pe6(void)
{
   int i;
   BitWrPortI(PEDR, &PEDRShadow, 0, 6);    // set master reset
   for (i = 0; i < 500; i++)
   BitWrPortI(PEDR, &PEDRShadow, 1, 6);    // master reset low to high pulse
   BitWrPortI(PEDR, &PEDRShadow, 0, 6);    // leave master reset low
}

void setup_isr0( void )
{
    WrPortI(PEDDR, &PEDDRShadow, 0xFC);    // lower bits of port e are interrupts
    SetVectExtern(0, my_isr0);
    SetVectExtern(1, my_isr1);
    // re-setup ISR's to show example of retrieving ISR address using GetVectExtern3000
    SetVectExtern(0, GetVectExtern(0));
    SetVectExtern(1, GetVectExtern(1));
    //    SetVectExtern3000(1, GetVectExtern3000(1));
    
    WrPortI(I0CR, &I0CRShadow, 0x09);
    WrPortI(I1CR, &I1CRShadow, 0x00);
    int1 = 1;
    //  if (isr1_enabled == 1)
    //     disable_isr1();
}

void setup_isr1( void )
{
    WrPortI(PDDDR, &PDDDRShadow, 0xFD);    // set port E as all inputs
    SetVectExtern(1, my_isr1);
    //    SetVectExtern3000(1, my_isr1);
    // re-setup ISR's to show example of retrieving ISR address using GetVectExtern3000
    SetVectExtern(1, GetVectExtern(1));
    //    SetVectExtern3000(1, GetVectExtern3000(1));
    WrPortI(I1CR, &I1CRShadow, 0x81);
    //   WrPortI(I1CR, &I1CRShadow, 0x81);
    //  enable_isr1();
}
 nodebug root interrupt void my_isr0()
{
    //     char message[512] = {0};
    //   WrPortI(PADR, &PADRShadow, 0x04);
    //   printf("send 0x%x to port a\n", line_out[index]);
    //    BitWrPortI(PEDR, &PEDRShadow, 1, 0);
    // WrPortE(PADR, &PADRShadow, line_out[index]);
    if (index == 0)
    {
     BitWrPortI(PADR, &PADRShadow, 1, 0);
     BitWrPortI(PADR, &PADRShadow, 0, 1);
     BitWrPortI(PADR, &PADRShadow, 0, 2);
     index += 1;
    }
    else if (index == 1)
    {
     BitWrPortI(PADR, &PADRShadow, 0, 0);
     BitWrPortI(PADR, &PADRShadow, 1, 1);
     BitWrPortI(PADR, &PADRShadow, 0, 2);
     index += 1;
    }
    else if (index == 2)
    {
     BitWrPortI(PADR, &PADRShadow, 0, 0);
     BitWrPortI(PADR, &PADRShadow, 0, 1);
     BitWrPortI(PADR, &PADRShadow, 1, 2);
     index = 0;
    }
    else
     index += 1;
}

 nodebug root interrupt void my_isr1()
{
 //   printf("I have seen SOW interrupt\n"); 
 //   count1 += 1;
 //   char message[512] = {0};
 //   WrPortI(PADR, &PADRShadow, 0x04);
 //   printf("send 0x%x to port a\n", line_out[index]);
 //   BitWrPortI(PEDR, &PEDRShadow, 1, 0);
 //   WrPortE(PADR, &PADRShadow, line_out[index]);
    
  if (index == 0)
  {
   BitWrPortI(PADR, &PADRShadow, 1, 0);
   BitWrPortI(PADR, &PADRShadow, 0, 1);
   BitWrPortI(PADR, &PADRShadow, 0, 2);
   index += 1;
  }
  else if (index == 1)
  {
     BitWrPortI(PADR, &PADRShadow, 0, 0);
     BitWrPortI(PADR, &PADRShadow, 1, 1);
     BitWrPortI(PADR, &PADRShadow, 0, 2);
     index += 1;
  }
  else if (index == 2)
  {
      BitWrPortI(PADR, &PADRShadow, 0, 0);
     BitWrPortI(PADR, &PADRShadow, 0, 1);
     BitWrPortI(PADR, &PADRShadow, 1, 2);
      index = 0;

  }
  else
      index += 1;
}

void disable_isr( void )
{
/* this actually enables isr0 */
//    printf("I am trying to disable HB here\n");
WrPortI(I0CR, &I0CRShadow, 0x00);
// WrPortI(I0CR, &I0CRShadow, 0x00);

//  started = 0;
int1 = 0;
}

void disable_isr1( void )
{
//printf("int1 count is %d\n", count1);
WrPortI(I1CR, &I1CRShadow, 0x00);
int2 = 0;
// started = 0;
}

void enable_isr( void )
{
/* this actually enables isr0 */
//printf("I am enabling isr0\n");
WrPortI(I0CR, &I0CRShadow, 0x09);
//WrPortI(I0CR, &I0CRShadow, 0x00);
// started = 0;
int1 = 1;
}

void enable_isr1( void )
{
/* this actually enables isr0 */
//printf("I am enabling isr0\n");
WrPortI(I1CR, &I1CRShadow, 0x09);
//WrPortI(I0CR, &I0CRShadow, 0x00);
// started = 0;
int2 = 1;
}

void hold_pattern( void )
{

   if (int1 == 1)
     disable_isr();
   if (int2 == 1)
     disable_isr1();

   BitWrPortI(PADR, &PADRShadow, 1, 0);
   BitWrPortI(PADR, &PADRShadow, 0, 1);
   BitWrPortI(PADR, &PADRShadow, 0, 2);

}

void hold_pattern_cold( void )
{

   if (int1 == 1)
     disable_isr();
   if (int2 == 1)
     disable_isr1();

   BitWrPortI(PADR, &PADRShadow, 0, 0);
   BitWrPortI(PADR, &PADRShadow, 1, 1);
   BitWrPortI(PADR, &PADRShadow, 0, 2);

}

void hold_pattern_hot( void )
{

   if (int1 == 1)
     disable_isr();
   if (int2 == 1)
     disable_isr1();

   BitWrPortI(PADR, &PADRShadow, 0, 0);
   BitWrPortI(PADR, &PADRShadow, 0, 1);
   BitWrPortI(PADR, &PADRShadow, 1, 2);

}

void switch_mode( void )
{
   auto int sw2, sw3, led2, led3;
   led2=led3=1;            //initialize leds to off value
    sw2=sw3=0;                //initialize switches to false value

   while (1)
    {
        costate
        {
            if (BitRdPortI(PBDR, S2_BIT))        //wait for switch S2 press
                   abort;
               waitfor(DelayMs(50));             //switch press detected if got to here
            if (BitRdPortI(PBDR, S2_BIT))        //wait for switch release
               {
                printf("switch 2 pressed\n");
                   sw2=!sw2;
             //set valid switch
                   abort;
               }
        }
        costate
        {
            if (BitRdPortI(PBDR, S3_BIT))        //wait for switch S3 press
                abort;
            waitfor(DelayMs(50));
                         //switch press detected if got to here
            if (BitRdPortI(PBDR, S3_BIT))        //wait for switch release
            {
            printf("switch 3 pressed\n");
            cycle_switch();
                sw3=!sw3;                                //set valid switch
                abort;
            }
        }
        costate
        {    // toggle DS2 led upon valid S2 press/release and clear switch
            if (sw2)
            {
                BitWrPortI(PBDR, &PBDRShadow, led2=led2?0:1, DS2_BIT);
                sw2=!sw2;
            enable_isr();
            return;
            }
        }
        costate
        {    // toggle DS3 upon valid S3 press/release and clear switch
            if (sw3)
            {
                BitWrPortI(PBDR, &PBDRShadow, led3=led3?0:1, DS3_BIT);
                sw3=!sw3;
            }
        }
    }
}

void cycle_switch ( void )
{
 //     printf("I have seen SOW interrupt\n");
 //  count1 += 1;
 //     char message[512] = {0};
 //   WrPortI(PADR, &PADRShadow, 0x04);
 //   printf("send 0x%x to port a\n", line_out[index]);
 //    BitWrPortI(PEDR, &PEDRShadow, 1, 0);
 // WrPortE(PADR, &PADRShadow, line_out[index]);
  if (index == 0)
  {
   BitWrPortI(PADR, &PADRShadow, 1, 0);
   BitWrPortI(PADR, &PADRShadow, 0, 1);
   BitWrPortI(PADR, &PADRShadow, 0, 2);
   index += 1;
  }
  else if (index == 1)
  {
     BitWrPortI(PADR, &PADRShadow, 0, 0);
     BitWrPortI(PADR, &PADRShadow, 1, 1);
     BitWrPortI(PADR, &PADRShadow, 0, 2);
     index += 1;
  }
  else if (index == 2)
  {
     BitWrPortI(PADR, &PADRShadow, 0, 0);
     BitWrPortI(PADR, &PADRShadow, 0, 1);
     BitWrPortI(PADR, &PADRShadow, 1, 2);
     index = 0;
  }
  else
      index += 1;
}
