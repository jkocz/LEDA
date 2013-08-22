#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <math.h>
#include <limits.h>
#include <time.h>
#include <unistd.h>
#include <string.h>

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
#define nstation 16
#define nfrequency 814

/*
  Data ordering for input vectors is (running from slowest to fastest)
  [time][channel][station][polarization][complexity]

  Output matrix has ordering (mostly - with a few extra terms!)
  [channel][station][station][polarization][polarization][complexity]
*/

void xgpuReorderMatrix(Complex *matrix, size_t matLength);
void xgpuExtractMatrix(Complex *matrix, Complex *packed);


int main(int argc, char** argv) {

  int i;
  struct timespec start, stop;
  double total, per_call, max_bw;
  int slicePerFile = 60;
  int fullMatLength = 814*16*16*2*2; // nfrequency*nstation*nstation*npol*npol;
  int strideLength;
  char* header[4096];
  int matrix_len = nfrequency * ((nstation/2 + 1) * (nstation/4)*npol*npol*4) ;
  //Complex* datagulp = (Complex *) malloc (matrix_len*sizeof(Complex));
  //char* input_file = "testin.L"; 
  char* input_file = argv[1];
  int   sliceToRead = atoi(argv[2]);
  unsigned  bytes_read;
  int outerL,innerL;
  FILE * inputFile = fopen(input_file, "rb");
  fprintf(stdout,"Input File: %s\n",input_file);
   

 
  bytes_read = fread(header,sizeof(char),4096,inputFile);
  fprintf(stdout,"Header Read (%d bytes)\n",bytes_read);

  //fprintf(stdout,"%s\n",header);

  Complex *full_matrix_h = (Complex *) malloc(fullMatLength*sizeof(Complex));
  Complex *cuda_matrix_h = (Complex *) malloc(matrix_len*sizeof(Complex));
  fprintf(stdout,"Memory allocated\n");
  
  char output_fileA[100]; 
  char output_fileC[100];

  int bytes_printed = 0;
  int acount = 0;
  int aflip = 0;
  int ccount = 2;
  int cflip = 1;
  int oflip = 0;

  for (outerL=0;outerL<sliceToRead/slicePerFile;outerL++)
  {
	fprintf(stdout,"Will read %d slices\n",sliceToRead/slicePerFile);
	sprintf(output_fileA,"Test_%d.LA",outerL);
	sprintf(output_fileC,"Test_%d.LC",outerL);
  	FILE * outputFileA = fopen(output_fileA, "a");
        FILE * outputFileC = fopen(output_fileC,"a");
        fprintf(stdout,"Output files open\n");


	//for (int zz=0;zz<100;zz++)
	//{
	//	bytes_read = fread(cuda_matrix_h,sizeof(Complex),matrix_len,inputFile);
	//	fprintf(stdout,"bytes: %d\n", bytes_read);
	//}

        //for (int innerL=0;innerL=innerL+1;innerL<slicePerFile);
        for (innerL=0;innerL<slicePerFile;innerL++)
	{
		//fprintf(stdout,"In inner loop...%d\n",innerL);
		bytes_read = fread(cuda_matrix_h,sizeof(Complex),matrix_len,inputFile);

		//fprintf(stdout, "Expected %d bytes, Read %d bytes\n",matrix_len,bytes_read);
		if (bytes_read < matrix_len)
		{
			fprintf(stdout, "EOF Reached\n");
			fclose(outputFileA);
			fclose(outputFileC);
			free(full_matrix_h);
			free(cuda_matrix_h);
			return 0;
		}  
		//fprintf(stdout,"Reordering stage 1.... \n");	
		xgpuReorderMatrix(cuda_matrix_h,matrix_len);
  		// convert from packed triangular to full matrix
		//fprintf(stdout,"Reordering stage 2.... \n");
  		xgpuExtractMatrix(full_matrix_h, cuda_matrix_h);
		//fprintf(stdout,"Reordering complete\n");
		// write to output
		strideLength= 528+496;
		bytes_printed = 0;
		acount = 0;
		aflip = 0;
		ccount = 2;
		cflip = 1;
		oflip = 0;
               	for (int acIndex=0;acIndex<nstation*2;acIndex++)
		{
			for (int freqCh=0;freqCh<nfrequency;freqCh++)
			{	

				//fprintf(stdout,"Printing AC channel: 4 bytes, %d\n",sizeof(full_matrix_h[acIndex*814+strideLength*freqCh].real));
				bytes_printed = bytes_printed+4;	
				//fprintf(stdout,"%d\n",acount+strideLength*freqCh);
				//fprintf(stdout,"%I32f\n",full_matrix_h[acIndex*814+strideLength*freqCh].real);
				//fprintf(outputFileA,"%f",full_matrix_h[acIndex*814+strideLength*freqCh].real);
				//fwrite(&full_matrix_h[acIndex*814+strideLength*freqCh].real,1,4,outputFileA);
				fwrite(&full_matrix_h[acount+strideLength*freqCh].real,1,4,outputFileA);
			}
			//acount += (nstation*2+1);
			if (aflip == 0)
			{
				acount += 3;
				aflip = 1;
			}
			else
			{
				acount +=65;
				aflip = 0;
			}

			
		}
		//fprintf (stdout, "AC writen, bytes printed: %d\n",bytes_printed);
		//for (int ccIndex=0;ccIndex<496;ccIndex++)
		for (int ccIndex=0;ccIndex<32;ccIndex++)
		{
			for (int xcount=ccIndex;xcount<31;xcount++)
			{
				// need to reset start count after each column of the matrix...
	
				for (int freqCh=0;freqCh<nfrequency;freqCh++)
				{
					fwrite(&full_matrix_h[ccount+strideLength*freqCh].real,1,4,outputFileC);
					fwrite(&full_matrix_h[ccount+strideLength*freqCh].imag,1,4,outputFileC);
				}
				if (cflip == 0)
				{
					ccount += 2;
					cflip = 1;
				}
				else
				{
					ccount +=62;
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
					ccount +=63;
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
	        //fprintf(stdout, "CC written\n");
	}
	fclose(outputFileA);
	fclose(outputFileC);
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

// changed order of upper/lower matrix from default xgpu for lfile writeout

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
	    matrix[(((f*nstation + i)*nstation + j)*npol + pol1)*npol+pol2].imag = -packed[index].imag;
	    matrix[(((f*nstation + j)*nstation + i)*npol + pol2)*npol+pol1].real =  packed[index].real;
	    matrix[(((f*nstation + j)*nstation + i)*npol + pol2)*npol+pol1].imag = packed[index].imag;
	    //printf("%d %d %d %d %d %d %d\n",f,i,j,k,pol1,pol2,index);
	    //printf("Mat1: %d\n",(((f*nstation + i)*nstation + j)*npol + pol1)*npol+pol2);
	    //printf("Mat2: %d\n",(((f*nstation + j)*nstation + i)*npol + pol2)*npol+pol1);
	  }
	}
      }
    }
  }

}
