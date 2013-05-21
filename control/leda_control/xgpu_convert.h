
#pragma once

#include <cstdlib>

typedef struct ComplexStruct {
  float real;
  float imag;
} Complex;

size_t xgpuReorderMatrix(Complex *matrix, size_t matLength,
                         size_t nfrequency, size_t nstation, size_t npol);
void xgpuExtractMatrix(Complex *matrix, Complex *packed,
                       size_t nfrequency, size_t nstation, size_t npol);
