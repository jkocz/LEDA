
/*
The .dada output files are ordered as follows:
  [time][nfreq/nstreams][reg_tile_triangular]
LEDA64-LWA currently used 200 time dumps per file
 = 28.4444 minutes / file
 = 8.5333 secs / integration
 57.6 MHz total bandwidth = 7.2 MHz / stream (i.e., per file)

Open most recently modified .dada file
nintegrations = (file_size - header_size) / integration_size
if nintegrations == 0:
  Open 2nd most recently modified .dada file
  nintegrations = (file_size - header_size) / integration_size
Seek to header_size + (nintegrations-1)*integration_size
Read integration_size into &data[0]
Gives [300 channels][reg_tile_triangular]
Convert to triangular format
Sum over (subset of) channels
Extract to full Hermitian matrix
Extract XX and YY polarisations
Convert to amp and phase
Write to vismatrix_xx/yy.dat

Python script to generate images
Read vismatrix_xx/yy.dat into numpy arrays
Transform into colour array
Write as .png image

*/

#include <fstream>
#include <string>
#include <vector>
#include <cmath>
#include <stdexcept>
#include <algorithm>
#include <iostream>
using std::cout;
using std::endl;

#include "xgpu_convert.h"

Complex make_Complex(float real, float imag) {
	Complex c;
	c.real = real;
	c.imag = imag;
	return c;
}
Complex operator+(const Complex& a, const Complex& b) {
	Complex c;
	c.real = a.real + b.real;
	c.imag = a.imag + b.imag;
	return c;
}

void write_matrix(const float* matrix, size_t n, std::string filename) {
	cout << "Opening output file " << filename << endl;
	//std::ofstream file(filename.c_str(), std::ios::binary);
	std::ofstream file(filename.c_str());
	if( !file ) {
		throw std::runtime_error("Failed to open " + filename);
	}
	cout << "Writing matrix" << endl;
	//file.write((char*)&matrix[0], n*n*sizeof(float));
	/*
	for( size_t i=0; i<n*n; ++i ) {
		file << matrix[i] << "\n";
	}
	*/
	for( size_t i=0; i<n; ++i ) {
		for( size_t j=0; j<n; ++j ) {
			file << matrix[i*n+j] << " ";
		}
		file << "\n";
	}
	file.close();
}

std::ifstream::pos_type filesize(const char* filename)
{
    std::ifstream in(filename, std::ifstream::in | std::ifstream::binary);
    in.seekg(0, std::ifstream::end);
    return in.tellg();
}

int main(int argc, char* argv[])
{
	enum { HEADER_SIZE = 4096 };
	
	// TODO: Probably need to read these from argv, passed from host Python app
	size_t nfrequency  = 600;
	size_t nstation    = 32;
	size_t npol        = 2;
	size_t sum_nfreq   = 600;
	size_t sum_freq0   = 0;
	size_t freqlen     = ((nstation/2+1)*(nstation/4)*npol*npol*4);
	//size_t symlen      = npol*nstation*(nstation+1)/2;//(nstation*npol)*(nstation*npol+1)/2;
	size_t xgpu_matlen = nfrequency*freqlen;
	size_t xgpu_matlen_bytes = xgpu_matlen * sizeof(Complex);
	size_t full_freqlen = nstation*nstation*npol*npol;
	//size_t full_freqlen_bytes = full_freqlen * sizeof(Complex);
	//size_t full_matlen = nfrequency*nstation*nstation*npol*npol;
	//size_t full_matlen_bytes = full_matlen * sizeof(Complex);
	char   header[HEADER_SIZE];
	
	if( argc <= 2 ) {
		cout << "Usage: " << argv[0] << " in_filename.dada out_filename_stem" << endl;
		return -1;
	}
	std::string in_filename    = argv[1];
	std::string out_stem       = argv[2];
	std::string amp_xx_filename   = out_stem + "_xx.amp";
	std::string amp_yy_filename   = out_stem + "_yy.amp";
	std::string phase_xx_filename = out_stem + "_xx.phase";
	std::string phase_yy_filename = out_stem + "_yy.phase";
	
	cout << "Allocating memory..." << endl;
	std::vector<Complex> xgpu_matrix(xgpu_matlen);
	std::vector<Complex> full_matrix(nfrequency*full_freqlen);
	
	cout << "Opening input file..." << endl;
	std::ifstream inputfile(in_filename.c_str(), std::ios::binary);
	if( !inputfile ) {
		cout << "ERROR: Failed to open " << in_filename << endl;
		return -1;
	}
	cout << "Reading header..." << endl;
	inputfile.read(header, HEADER_SIZE);
	if( !inputfile ) {
		cout << "ERROR: Failed to read file header of length "
		     << HEADER_SIZE << " bytes" << endl;
		return -1;
	}
	
	cout << "Seeking to latest complete matrix" << endl;
	inputfile.seekg(0, std::ifstream::end);
	size_t filesize = inputfile.tellg();
	//cout << "filesize = " << filesize << endl;
	// Note: We want whole integrations, so rounding down is desired
	size_t nintegrations = (filesize - HEADER_SIZE) / xgpu_matlen_bytes;
	//cout << "nintegrations = " << nintegrations << endl;
	inputfile.seekg(HEADER_SIZE + (nintegrations-1)*xgpu_matlen_bytes,
	                std::ifstream::beg);
	
	cout << "Reading visibility matrix..." << endl;
	inputfile.read((char*)&xgpu_matrix[0],
	               xgpu_matlen_bytes);
	if( !inputfile ) {
		cout << "ERROR: Failed to read complete matrix of length "
		     << xgpu_matlen_bytes/1e6 << " Mbytes" << endl;
		return -1;
	}
	inputfile.close();
	
	cout << "Reordering matrix..." << endl;
	// Convert from REGISTER_TILE_TRIANGULAR_ORDER to TRIANGULAR_ORDER
	/*size_t count =*/ xgpuReorderMatrix(&xgpu_matrix[0], xgpu_matlen,
	                                 nfrequency, nstation, npol);
	
	// TODO: Trying to do the summing here failed horribly due to the
	//         uninterpretable ordering out of xgpuReorderMatrix!
	/*
	// Sum over frequency
	std::vector<Complex> sum_matrix(count/nfrequency,
	                                make_Complex(0.f,0.f));
	for( size_t c=sum_freq0; c<sum_freq0+sum_nfreq; ++c ) {
		std::transform(sum_matrix.begin(), sum_matrix.end(),
		               &xgpu_matrix[c*count/nfrequency],
		               sum_matrix.begin(),
		               std::plus<Complex>());
	}
	*/
	// Convert from packed triangular to full matrix
	cout << "Expanding to full matrix..." << endl;
	//xgpuExtractMatrix(&full_matrix[0], &sum_matrix[0],
	//1, nstation, npol);
	xgpuExtractMatrix(&full_matrix[0], &xgpu_matrix[0],
	                  nfrequency, nstation, npol);
	
	// Sum over frequency	
	std::vector<Complex> sum_matrix(full_freqlen,
	                                make_Complex(0.f,0.f));
	for( size_t c=sum_freq0; c<sum_freq0+sum_nfreq; ++c ) {
		std::transform(sum_matrix.begin(), sum_matrix.end(),
		               &full_matrix[c*full_freqlen],
		               sum_matrix.begin(),
		               std::plus<Complex>());
	}
	// Normalise
	for( size_t i=0; i<full_freqlen; ++i ) {
		sum_matrix[i].real *= 1.f/sum_nfreq;
		sum_matrix[i].imag *= 1.f/sum_nfreq;
	}
	
	cout << "Computing amplitude and phase..." << endl;
	std::vector<float> amp_matrix_xx(nstation*nstation);
	std::vector<float> amp_matrix_yy(nstation*nstation);
	std::vector<float> phase_matrix_xx(nstation*nstation);
	std::vector<float> phase_matrix_yy(nstation*nstation);
	for( size_t i=0; i<nstation*nstation; ++i ) {
		Complex x;
		x = sum_matrix[i*npol*npol + 0];
		amp_matrix_xx[i]   = sqrtf(x.real*x.real + x.imag*x.imag);
		phase_matrix_xx[i] = atan2f(x.imag, x.real);
		
		x = sum_matrix[i*npol*npol + 3];
		amp_matrix_yy[i]   = sqrt(x.real*x.real + x.imag*x.imag);
		phase_matrix_yy[i] = atan2(x.imag, x.real);
	}
	
	write_matrix(&amp_matrix_xx[0], nstation, amp_xx_filename);
	write_matrix(&amp_matrix_yy[0], nstation, amp_yy_filename);
	write_matrix(&phase_matrix_xx[0], nstation, phase_xx_filename);
	write_matrix(&phase_matrix_yy[0], nstation, phase_yy_filename);
	
	cout << "Done." << endl;
}
