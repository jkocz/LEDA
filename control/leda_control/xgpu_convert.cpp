
#include "xgpu_convert.h"

#include <cstdlib>
#include <cstring> // For memset

size_t xgpuReorderMatrix(Complex *matrix, size_t matLength,
                         size_t nfrequency, size_t nstation, size_t npol) {

	// reorder the matrix from REGISTER_TILE_TRIANGULAR_ORDER to TRIANGULAR_ORDER
	size_t count = 0;
	
	size_t f, i, rx, j, ry, pol1, pol2;
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
								++count;
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

	return count;
}

// Extracts the full matrix from the packed Hermitian form
void xgpuExtractMatrix(Complex *matrix, Complex *packed,
                       size_t nfrequency, size_t nstation, size_t npol) {

	size_t f, i, j, pol1, pol2;
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
