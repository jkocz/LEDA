/* 
* Lconvert64ov.c
* L-file converter, Owen's Valley LEDA-64 flavor
*/

#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <math.h>
#include <limits.h>
#include <time.h>
#include <unistd.h>
#include <string.h>
#include "src/commander.h"

typedef char ReImInput;

typedef struct ComplexInputStruct {
  ReImInput real;
  ReImInput imag;
} ComplexInput;

typedef struct ComplexStruct {
  float real;
  float imag;
} Complex;

#define npol 2
#define nstation 32
#define nfrequency 600

/*
  Data ordering for input vectors is (running from slowest to fastest)
  [time][channel][station][polarization][complexity]

  Output matrix has ordering (mostly - with a few extra terms!)
  [channel][station][station][polarization][polarization][complexity]
*/

void xgpuReorderMatrix(Complex *matrix, size_t matLength);
void xgpuExtractMatrix(Complex *matrix, Complex *packed);


/* 
    Command line parsed arguments 
*/

char* header[4096];

unsigned long filenameOffset = 1044480000;
unsigned long  offsetCount = 0;

int n_chans_out     = 600;
int debug           = 1;
int n_acc_per_file  = 50;
int start_chan      = 0;
int n_acc_to_read   = 99999;
int write_autos_only      = 0;

const char* filename_in  = NULL;
const char* fileroot_out = NULL;


static void
set_verbose(command_t *self) {
      printf("verbose: enabled\n");
      debug = 2;
}

static void
set_silent(command_t *self) {
    printf("silent mode.");
    debug = 0;
}

static void set_n_chans_out(command_t *self) {
    if(debug > 0) {
        printf("Number of channels:                      %s\n", self->arg);
    }
    n_chans_out = atoi(self->arg);
}

static void set_autos_only(command_t *self) {
    if(debug > 0) {
        printf("Write Autocorrs ONLY   \n");
    }
    write_autos_only = 1;
}

static void set_n_acc_per_file(command_t *self) {
    if(debug > 0) {
        printf("Number of accumulations per output file: %s\n", self->arg);
    }
    n_acc_per_file = atoi(self->arg);
}

static void set_n_acc_to_read(command_t *self) {
    if(debug > 0) {
        printf("Num. of accums. from this file to read:  %s\n", self->arg);
    }
    n_acc_to_read = atoi(self->arg);
}

static void set_start_chan(command_t *self) {
    if(debug > 0) {
        printf("First channel offset:                    %s\n", self->arg);
    }
    start_chan = atoi(self->arg);
}

static void set_file_in(command_t *self) {
    if(debug > 0) {
        printf("Input filename:   %s\n", self->arg);
    }
    filename_in = self->arg;
}

static void set_file_out(command_t *self) {
    if(debug > 0) {
        printf("Output file root: %s\n", self->arg);
    }
    fileroot_out = self->arg;
}


/*
    Start of main
*/

int main(int argc, char** argv) {
    
    if(debug >= 1) {
        fprintf(stdout,"Initializing....\n");
    }

    command_t cmd;
    command_init(&cmd, argv[0], "1.0.0");
    command_option(&cmd, "-v", "--verbose", "enable verbose info", set_verbose);
    command_option(&cmd, "-s", "--silent", "set silent (no print to stdout)", set_silent);
    command_option(&cmd, "-A", "--autosonly", "Only output autocorrelations (.LA)", set_autos_only);  
    command_option(&cmd, "-i", "--input <arg>", "input filename", set_file_in);
    command_option(&cmd, "-o", "--output <arg>", "output filename root", set_file_out);
    command_option(&cmd, "-n", "--numchans [arg]",  "Number of channels to read (defaults to 600)", set_n_chans_out);
    command_option(&cmd, "-f", "--startchan [arg]", "First channel to write (defaults to 0)", set_start_chan);
    command_option(&cmd, "-t", "--accperfile [arg]", "Number of accumulations per output file (defaults to 50)", set_n_acc_per_file);
    command_option(&cmd, "-T", "--acctoread [arg]", "Number of accumulations from input file to read (defaults to all)", set_n_acc_per_file);
   
    command_parse(&cmd, argc, argv);
    
    FILE * inputFile;
    FILE * outputFileA;
    FILE * outputFileC;
    unsigned  bytes_read;
    int outerL, innerL;
    int i;
    char inputFile_full[100];
    char fname_outA[100]; 
    char fname_outC[100]; 
    
    double total, per_call, max_bw;
    int fullMatLength = nfrequency*nstation*nstation*npol*npol;
    int strideLength;
    int matrix_len = nfrequency * ((nstation/2 + 1) * (nstation/4)*npol*npol*4) ;
    
    int remainder = 0;
    int bytes_offset = 0;
    int bytes_printed = 0;
    int acount = 0;
    int aflip = 0;
    int ccount = 2;
    int cflip = 1;
    int oflip = 0;
    
    if(filename_in == NULL || fileroot_out == NULL) {
        fprintf(stderr, "Error: Input and output filename required, use -i and -o flags. Run with -h for help\n");
        exit(1);
    }
    
    Complex *full_matrix_h = (Complex *) malloc(fullMatLength*sizeof(Complex));
    Complex *cuda_matrix_h = (Complex *) malloc(matrix_len*sizeof(Complex));
    if(debug >= 2) {
        fprintf(stdout,"Memory allocated\n");
    }

    inputFile = fopen(filename_in, "rb");
    bytes_read = fread(header,sizeof(char),4096,inputFile);
    fprintf(stdout,"Header Read (%d bytes)\n",bytes_read);
    
    for (outerL=0;outerL<n_acc_to_read/n_acc_per_file;outerL++)
    {
        if(debug >=2){
            fprintf(stdout,"Will read %d slices\n",n_acc_to_read/n_acc_per_file);   
        }
      
      sprintf(fname_outA,"%s_%d.LA",fileroot_out, outerL);
      sprintf(fname_outC,"%s_%d.LC",fileroot_out, outerL);
      
      outputFileA = fopen(fname_outA, "a");
      if(write_autos_only == 0){
          outputFileC = fopen(fname_outC, "a");
      }
      
          for (innerL=0;innerL<n_acc_per_file;innerL++)
      {
          if(debug >=2){
              fprintf(stdout,"In inner loop...%d\n",innerL);
          }
          
          bytes_read = fread(cuda_matrix_h,sizeof(Complex),matrix_len,inputFile);
          
          if(debug >=2){
              fprintf(stdout, "Expected %d bytes, Read %d bytes\n",matrix_len,bytes_read);
          }
          
          if (bytes_read < matrix_len)
          {
              if(debug >=1){
                  fprintf(stdout, "EOF Reached\n");
              }
              offsetCount += filenameOffset;
              sprintf(inputFile_full,"%s_%016lu.000000.dada",filename_in,offsetCount);
              inputFile = fopen(inputFile_full, "rb");
              
              if (inputFile <= 0)
              {
                  fclose(outputFileA);
                  
                  if(write_autos_only == 0){
                      fclose(outputFileC);
                  }
                  free(full_matrix_h);
                  free(cuda_matrix_h);
                  return 0;
              }
              
              bytes_offset = bytes_read;
              bytes_read = fread(header,sizeof(char),4096,inputFile);
              //fprintf(stdout,"Header Read (%d bytes)\n",bytes_read);
              
              if(debug >=1) {
                  fprintf(stdout,"Input File: %s\n",inputFile_full);
              }
              remainder = matrix_len - bytes_offset;
                          bytes_read = fread(cuda_matrix_h,sizeof(Complex),remainder,inputFile);
                          
              //fprintf(stdout, "Expected %d bytes, Read %d bytes\n",remainder,bytes_read);
              // set cuda_matrix_h to zero for this one to ensure no corruption of data?
              // memset(cuda_matrix_h, '\0', matrix_len*sizeof(Complex));
    
          }  
          if(debug >=2){
              fprintf(stdout,"Reordering stage 1.... \n");  
          }
          xgpuReorderMatrix(cuda_matrix_h,matrix_len);
          // convert from packed triangular to full matrix
          if(debug >=2){
              fprintf(stdout,"Reordering stage 2.... \n");
          }
          xgpuExtractMatrix(full_matrix_h, cuda_matrix_h);
          if(debug >=2){
              fprintf(stdout,"Reordering complete\n");
          }
          // write to output
          strideLength       = 2080+2016;
          int bytes_printed  = 0;
                  acount     = 0;
                  aflip      = 0;
                  ccount     = 2;
                  cflip      = 1;
                  oflip      = 0;
                  
          for (int acIndex=0;acIndex<nstation*2;acIndex++)
          {
              for (int freqCh=0;freqCh<n_chans_out+start_chan;freqCh++)
              {   

                  bytes_printed = bytes_printed+4;    
                  //fprintf(outputFileA,"%I32f",full_matrix_h[acIndex*300+strideLength*freqCh].real);
                  //fprintf(outputFileA,"%f",full_matrix_h[acIndex*814+strideLength*freqCh].imag);
                  if(freqCh >= start_chan) {
                      fwrite(&full_matrix_h[acount+strideLength*freqCh].real,1,4,outputFileA);
                  }
    
              }
                          //acount += (nstation*2+1);
                          if (aflip == 0)
                          {
                                  acount += 3;
                                  aflip = 1;
                          }
                          else
                          {
                                  //acount +=65;
                                  acount +=129;
                                  aflip = 0;
                          }
          }
          
          if(debug >=2){
              fprintf (stdout, "AC writen, bytes printed: %d\n",bytes_printed);
          }
          
          if(write_autos_only == 0){
            for (int ccIndex=0;ccIndex<64;ccIndex++)
            {
                  for (int xcount=ccIndex;xcount<63;xcount++)
                  {
                          // need to reset start count after each column of the matrix...
              
                          for (int freqCh=0;freqCh<n_chans_out+start_chan;freqCh++)
                          {
                              if(freqCh >= start_chan) {        
                                  fwrite(&full_matrix_h[ccount+strideLength*freqCh].real,1,4,outputFileC);
                                  fwrite(&full_matrix_h[ccount+strideLength*freqCh].imag,1,4,outputFileC);
                              }
                          }
                          if (cflip == 0)
                          {
                                  ccount += 2;
                                  cflip = 1;
                          }
                          else
                          {
                                  //ccount +=62;
                                  ccount +=126;
                                  cflip = 0;
                          }
                  }
                  ccount = 2;
                  //cflip = 0;    
                  oflip = 0;
                  for (int xcount=0;xcount<=ccIndex;xcount++)
                  {
                          if (oflip == 0)
                          {
                                  ccount +=127;
                                  oflip = 1;
                                  cflip = 0;
                          }
                          else
                          {
                                  ccount += 5;
                                  oflip = 0;
                                  cflip = 1;
                          }
                  }
            }
            
            if(debug >=2){
                fprintf(stdout, "CC written\n");
            }
          }
      }
      
      fclose(outputFileA);
      if(write_autos_only == 0) {
          fclose(outputFileC);
      }
      
    }
    
    free(full_matrix_h);
    free(cuda_matrix_h);
    
    return 0;
}

void xgpuReorderMatrix(Complex *matrix, size_t matLength) {

  // reorder the matrix from REGISTER_TILE_TRIANGULAR_ORDER to TRIANGULAR_ORDER

  int f, i, rx, j, ry, pol1, pol2;
  Complex *tmp = (Complex *) malloc(matLength * sizeof(Complex));
  memset(tmp, '0', matLength);

  for(f=0; f<nfrequency; f++) {
    for(i=0; i<nstation/2; i++) {
      for (rx=0; rx<2; rx++) {
    for (j=0; j<=i; j++) {
      for (ry=0; ry<2; ry++) {
        int k = f*(nstation+1)*(nstation/2) + (2*i+rx)*(2*i+rx+1)/2 + 2*j+ry;
        int l = f*4*(nstation/2+1)*(nstation/4) + (2*ry+rx)*(nstation/2+1)*(nstation/4) + i*(i+1)/2 + j;
        for (pol1=0; pol1<npol; pol1++) {
          for (pol2=0; pol2<npol; pol2++) {
        size_t tri_index = (k*npol+pol1)*npol+pol2;
        size_t reg_index = (l*npol+pol1)*npol+pol2;
        //tmp[tri_index] = 
        //  Complex(((float*)matrix)[reg_index], ((float*)matrix)[reg_index+matLength]);
        tmp[tri_index].real = 
          ((float*)matrix)[reg_index];
        tmp[tri_index].imag = 
          ((float*)matrix)[reg_index+matLength];
          }
        }
      }
    }
      }
    }
  }
   
  memcpy(matrix, tmp, matLength*sizeof(Complex));

  free(tmp);

  return;
}

// Extracts the full matrix from the packed Hermitian form
void xgpuExtractMatrix(Complex *matrix, Complex *packed) {

  int f, i, j, pol1, pol2;
  for(f=0; f<nfrequency; f++){
    for(i=0; i<nstation; i++){
      for (j=0; j<=i; j++) {
    int k = f*(nstation+1)*(nstation/2) + i*(i+1)/2 + j;
        for (pol1=0; pol1<npol; pol1++) {
      for (pol2=0; pol2<npol; pol2++) {
        int index = (k*npol+pol1)*npol+pol2;
        matrix[(((f*nstation + i)*nstation + j)*npol + pol1)*npol+pol2].real = packed[index].real;
        matrix[(((f*nstation + i)*nstation + j)*npol + pol1)*npol+pol2].imag = packed[index].imag;
        matrix[(((f*nstation + j)*nstation + i)*npol + pol2)*npol+pol1].real =  packed[index].real;
        matrix[(((f*nstation + j)*nstation + i)*npol + pol2)*npol+pol1].imag = -packed[index].imag;
        //printf("%d %d %d %d %d %d %d\n",f,i,j,k,pol1,pol2,index);
      }
    }
      }
    }
  }

}
