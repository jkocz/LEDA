
/*
  
  TODO
  ----
  xGPU optimisation
    Add hexhack code to repo and integrate into build operations
    Benchmark K20X power, temp and perf for 512 as function of overclock
  
  Total power (hires) recording
    Limit file sizes to 1 GB like dbdisk
      Alternatively, write to a new dada buffer and use dbdisk
    Option to automatically name files with timestamp
    Confirm that this isn't cause of zero-bin real/imag non-gaussianity problem
    
  BDI
    Add functionality on top of standard xgpu model; don't bother with
      other improvements until basic functionality is sorted.
    Add to xGPU itself?
    Implement support in fringe plotter
    
  Stream splitting
    Nut out how it will integrate with dbxgpu and the rest of the pipeline
      Find original attempt to modify dbgpu to poll for available stream
        buffers and output to the corresponding out buffer.
    Nut out discrepant on/off-bin time span issue for pulsars
    Check cost of GPU-based unpacking vs. xGPU kernel time (for 64 & 512)
      Packed data would halve RAM and PCI-E requirements, as well as
        freeing up some CPU time.
    Study unpacker code and add stream splitting functionality
    
  Weights
    How many?
    Where?
    Work out how to pass through pipeline
    
  Data recorder
    UDP output?
    Storage hardware?
    Packet/header format?
  
 */

/*
  out_mat = {0}
  in_pipe --> xGPU kernel --> out_mat
  if( cycle % min_dump_cycles == 0 ) {
    big_cycle = cycle / min_dump_cycles //% (max_dump_cycles/min_dump_cycles)
    if( big_cycle is a power of 2 ) {
      dump_cycle = log2(big_cycle) % (max_dump_cycle+1)
      dump_map = dump_maps[dump_cycle]
      out_dump = out_mat[dump_map]
      out_mat[dump_map] = 0
      h_out = d2h(out_dump)
    }
  }
  
  Logarithmic spacing in integration time => log spacing in baseline length?
                                          => log spacing in frequency?
  
 */
/*
inline unsigned int round_up_pow2(unsigned int v) {
	v -= 1;
	v |= v >> 1;
	v |= v >> 2;
	v |= v >> 4;
	v |= v >> 8;
	v |= v >> 16;
	v += 1;
	return v;
}
inline unsigned int round_down_pow2(unsigned int v) {
	return round_up_pow2(v) >> ((i&(i-1)!=0));
}
inline unsigned int intlog2(unsigned int v) {
	register unsigned int r; // result of log2(v) will go here
	register unsigned int shift;
	r =     (v > 0xFFFF) << 4; v >>= r;
	shift = (v > 0xFF  ) << 3; v >>= shift; r |= shift;
	shift = (v > 0xF   ) << 2; v >>= shift; r |= shift;
	shift = (v > 0x3   ) << 1; v >>= shift; r |= shift;
	r |= (v >> 1);
	return r;
}

// Note: Input is no. NTIME_PIPE sums for each baseline in
//         lower triangular visibility matrix. Values must
//         be >= 1.
void setBaselineDumpTimes(const float* times) {
	typedef unsigned int uint;
	size_t nbaseline = nstation*(nstation+1)/2;
	float  mintime   = *std::min_element(times, times + nbaseline);
	float  maxtime   = *std::max_element(times, times + nbaseline);
	uint   mindump   = intlog2((uint)mintime);
	uint   maxdump   = intlog2((uint)maxtime);
	uint   ndumps    = maxdump+1 - mindump;
	std::vector<std::vector<uint> > dump_maps;
	dump_maps.resize(ndumps);
	for( size_t b=0; b<nbaseline; ++b ) {
		float time = times[b];
		// Note: We round down to guarantee required integration times
		uint dump = intlog2((uint)t) - mindump;
		// Add this baseline to all dumps with times >= required
		for( size_t d=dump; d<ndumps; ++d ) {
			dump_maps[d].push_back(b);
		}
	}
	
	for( size_t i=0; i<dump_maps[d].size(); ++i ) {
		size_t b = dump_maps[d][i];
		out[i]    = matrix[b];
		matrix[b] = 0;
	}
	
}
*/
/*
__global__
void dump_kernel( ) {
	uint i0 = 
}
*/
/*
virtual void onData(char* data_in, char* data_out, size_t size,
                    size_t& bytes_read, size_t& bytes_written) {
	// cudaXengine_deviceonly(data_in, m_outbuf);
	// bytes_read = size;
	//if( cycle != 0 && cycle % 
	
	  //if need to dump {
	  //  dump_kernel(m_outbuf, data_out, m_dump_maps[dump_cycle]);
	  //  bytes_written = m_dump_maps[dump_cycle].size() * nchans * sizeof(Complex)
	  //}
	
	this->syncStream();
}
*/
/*
  
  NTIME --> NTIME_PIPE --> NTIME_MIN_INT --> BDI
  
  d2h_task  = sew::create_copy_source(d_in);
  //h2d_task  = sew::create_siphon(d_out, h_out);
  h2d_task  = sew::create_sink(d_out, h_out);
  dump_task = sew::create_copy_source(dada_outkey);
  dada_sink
    onRead(h_data, size):
      d2h_task->write(h_data, size);
      h2d_task->read(h_out, size);
  sew::cuda::pipe
    onData(d_in, d_out):
      xgpu_kernel(d_in, d_out)
      if integrated NTIME_MIN_INT:
        bytes_written = size;
        d_out[:] = 0;
  sew::sink
    onRead(h_data, size):
      dump = out_int_buf[p][dumpable]
      out_int_buf[p][dumpable] = 0
      dump_buf[p].write(dump)
  
  p, h_in = get next full buffer
  d2h_task->write(h_in, buf_size); // d_in = h_in
  Compute d_in --> d_out and integrate to NTIME_MIN_INT
  if integrated NTIME_MIN_INT:
    h_out = d_out
    out_int_buf[p] += h_out
    dump = out_int_buf[p][dumpable]
    out_int_buf[p][dumpable] = 0
    dump_buf[p].write(dump)
  
*/
/*
int xgpuCudaXengine_device(XGPUContext *context, int syncOp,
                           const ComplexInput* in_d,
                           Complex*            out_d)
{
	XGPUInternalContext *internal = (XGPUInternalContext *)context->internal;
	if(!internal) {
		return XGPU_NOT_INITIALIZED;
	}
	//assign the device
	cudaSetDevice(internal->device);
	
	int Nblock = compiletime_info.nstation/min(TILE_HEIGHT,TILE_WIDTH);
	dim3 dimBlock(TILE_WIDTH,TILE_HEIGHT,1);
	//allocated exactly as many thread blocks as are needed
	dim3 dimGrid(((Nblock/2+1)*(Nblock/2))/2, compiletime_info.nfrequency);
	
	const ComplexInput* array_compute = in_d;
	// set pointers to the real and imaginary components of the device matrix
	float4* matrix_real_d = (float4*)(out_d);
	float4* matrix_imag_d = (float4*)(out_d + compiletime_info.matLength/2);
	
	// Kernel Calculation
#if TEXTURE_DIM == 2
	cudaBindTexture2D(0, tex2dfloat2, array_compute, channelDesc,
	                  NFREQUENCY*NSTATION*NPOL, NTIME_PIPE, 
	                  NFREQUENCY*NSTATION*NPOL*sizeof(ComplexInput));
#else
	cudaBindTexture(0, tex1dfloat2, array_compute, channelDesc,
	                NFREQUENCY*NSTATION*NPOL*NTIME_PIPE*sizeof(ComplexInput));
#endif
	CUBE_ASYNC_KERNEL_CALL(shared2x2float2, dimGrid, dimBlock, 0, streams[1], 
	                       matrix_real_d, matrix_imag_d, NSTATION, writeMatrix);
	checkCudaError();
	
	return XGPU_OK;
}
*/
#include <cstdio>
#include <cstdlib>
#include <cstring> // For memcpy
#include <stdexcept>
#include <vector>
#include <string>
#include <iostream>
using std::cout;
using std::endl;
#include <fstream>
#include <iterator>
#include <cmath>
//#include <iomanip>
#include <errno.h>       // For errno
#include <sys/syscall.h> // For SYS_gettid

//// Note: PSRDADA has some nasty #defines that interfere with sew (e.g., LOG_INFO)
//#include "sew.hpp"

#include <dada_def.h>
#include <ascii_header.h>
#include <dada_cuda.h>

#include <xgpu.h>

#include <cuda_runtime.h> // For cudaSetDeviceFlags

#include "dada_db2db.hpp"

// For benchmarking only
//#include "stopwatch.hpp"

typedef ComplexInput InType;

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
inline unsigned short total_power(const ComplexInput& c) {
	// Note: Max power from 8+8b input = -128^2 + -128^2 = 32768
	return c.real*c.real + c.imag*c.imag;
}
*/
inline unsigned char total_power(const ComplexInput& c) {
	// Note: Max power from 4+4b input = -8^2 + -8^2 = 128
	//       The input values are actually only the high 4b of 8b memory
	return (c.real*c.real + c.imag*c.imag) >> (4+4);
}
inline ComplexInput conj_mult(const ComplexInput& a, const ComplexInput& b) {
	int real, imag;
	real  = a.real*b.real;
	real -= a.imag*b.imag;
	real >>= (4+4);
	imag  = a.imag*b.real;
	imag += a.real*b.imag;
	imag >>= (4+4);
	ComplexInput x;
	x.real = real;
	x.imag = imag;
	return x;
}
inline unsigned char pack44(const ComplexInput& a) {
	unsigned char x = 0;
	x |= (a.real >> 4) & 0xF;
	x |= (a.imag >> 0) & 0xF0;
	return x;
}
class dbgpu : public dada_db2db {
	size_t               m_ntime_integrate;
	size_t               m_subintegration;
	int                  m_gpu_device;
	XGPUContext*         m_xgpu;
	XGPUInfo             m_xgpu_info;
	bool                 m_do_register;
	
	size_t m_cycle;
	
	// Total power variables
	//typedef unsigned short tptype;
	typedef unsigned char tptype;
	//typedef ComplexInput tptype;
	std::vector<size_t>  m_tp_inputs;
	std::vector<tptype>  m_tp_out;
	std::ostream*        m_tp_outstream;
	//size_t           m_tp_size;
	//sew::ringbuffer  m_tp_buf;
	//sew::stream_sink m_tp_disktask;
	//tptype*          m_tp_ptr;
	size_t           m_tp_ncycles;
	size_t           m_tp_nrecord;
	
	std::ostream*        m_bp_outstream;
	std::vector<Complex> m_bandpasses;
public:
	dbgpu(multilog_t* log, int verbose,
	      size_t ntime_integrate,
	      int gpu_device=0,
	      bool do_register=false)
		: dada_db2db(log, verbose),
		  m_ntime_integrate(ntime_integrate),
		  m_subintegration(0),
		  m_gpu_device(gpu_device),
		  m_do_register(do_register),
		  m_cycle(0),
		  m_tp_outstream(0),
		  m_bp_outstream(0) {
		
		// Give the CPU a rest while the GPU kernel is running
		cudaSetDeviceFlags(cudaDeviceScheduleYield);
		
		xgpuInfo(&m_xgpu_info);
		
		cout << "nstation    = " << m_xgpu_info.nstation << endl;
		cout << "nfrequency  = " << m_xgpu_info.nfrequency << endl;
		cout << "ntime       = " << m_xgpu_info.ntime << endl;
		cout << "ntimepipe   = " << m_xgpu_info.ntimepipe << endl;
		cout << "InType      = " << sizeof(InType) << " bytes" << endl;
		cout << "input size  = " << m_xgpu_info.vecLength * sizeof(ComplexInput) / 1e6 << " MB" << endl;
		cout << "output size = " << m_xgpu_info.matLength * sizeof(Complex) / 1e6 << " MB" << endl;
		
		logInfo( (std::string("dbgpu: Initialising xGPU library version ")
		          + xgpuVersionString()).c_str() );
		cout << "Using device " << m_gpu_device << endl;
		
		m_xgpu = new XGPUContext;
		int xgpu_error;
		xgpu_error = xgpuInit(m_xgpu, m_gpu_device | XGPU_DONT_REGISTER);
		if( xgpu_error ) {
			logError("dbgpu: xgpuInit failed");
			throw std::runtime_error("xgpuInit failed");
		}
		
		logInfo("dbgpu: Initialisation complete");
	}
	virtual ~dbgpu() {
		xgpuFree(m_xgpu);
		delete m_xgpu;
	}
	
	void setTotalPowerInputs(const int* tp_inputs, size_t tp_ninputs,
	                         size_t tp_ncycles, size_t nrecord,
	                         std::ostream& tp_outstream=std::cout) {
		//size_t nrecord = 2;
		m_tp_nrecord = nrecord;
		if( tp_ninputs % m_tp_nrecord != 0 ) {
			throw std::runtime_error("Number of total power inputs must be a multiple of nrecord");
		}
		m_tp_inputs.assign(tp_inputs, tp_inputs + tp_ninputs);
		size_t ninputs = m_xgpu_info.nstation * 2;
		m_tp_ncycles = tp_ncycles;
		//size_t tpsize  = m_xgpu_info.vecLength / ninputs * tp_ninputs;
		size_t tpsize  = m_xgpu_info.vecLength / ninputs * m_tp_nrecord;
		m_tp_out.resize(tpsize);
		m_tp_outstream = &tp_outstream;
		/*
		m_tp_size = m_xgpu_info.vecLength / ninputs * tp_ninputs;
		size_t nbufs = 4;
		m_tp_buf.allocate(m_tp_size, nbufs);
		m_tp_ptr  = (tptype*)m_tp_buf.openWrite();
		m_tp_disktask.setStream(tp_outstream);
		m_tp_disktask.setSyncMode(sew::stream_sink::SYNC_HARD);
		m_tp_disktask.connect(m_tp_buf);
		m_tp_disktask.run();
		*/
	}
	
	void setBandpassStream(std::ostream& bp_outstream) {
		m_bp_outstream = &bp_outstream;
	}
	
	virtual void onConnect(key_t in_key, key_t out_key) {
		if( m_do_register ) {
			// Register buffers as pinned memory
			dada_cuda_select_device(m_gpu_device);
			logInfo("dbgpu: Registering input buffer");
			dada_cuda_dbregister(this->hdu_in());
			logInfo("dbgpu: Registering output buffer");
			dada_cuda_dbregister(this->hdu_out());
		}
	}
	virtual void onDisconnect() {
		/*
		if( m_tp_buf.nbufs() ) {
			bool eod = true;
			logInfo("CLOSING LAST WRITE");
			m_tp_buf.closeWrite(eod, 0);
			logInfo("WAITING FOR DISKTASK TO FINISH");
			m_tp_disktask.sync();
			logInfo("DONE");
		}
		*/
	}
	
	// Return desired no. bytes per data read
	virtual uint64_t onHeader(uint64_t header_size,
	                          const char* header_in, char* header_out) {
		// copy the in header to the out header
		memcpy(header_out, header_in, header_size);
		
		// need to change some DADA parameters
		if( ascii_header_set(header_out, "NBIT", "%d", 32) < 0 ) {
			logInfo("dbgpu: Failed to set NBIT 32 in header_out");
		}
		
		m_cycle = 0;
		
		if( m_bp_outstream ) {
			Complex zero;
			zero.real = 0;
			zero.imag = 0;
			m_bandpasses.resize(0);
			m_bandpasses.resize(m_xgpu_info.nfrequency *
			                    m_xgpu_info.nstation *
			                    m_xgpu_info.npol,
			                    zero);
		}
		
		uint64_t bytes_per_read = m_xgpu_info.vecLength * sizeof(InType);
		return bytes_per_read;
	}
	
	// Return no. bytes written
	virtual uint64_t onData(uint64_t in_size,
	                        const char* data_in, char* data_out) {
		//Stopwatch timer;
		uint64_t bytes_written = 0;
		int xgpu_error;
		
		//timer.start();
		
		m_xgpu->array_h  = (ComplexInput*)data_in;
		m_xgpu->matrix_h =      (Complex*)data_out;
		xgpu_error = xgpuSetHostInputBuffer(m_xgpu);
		if( xgpu_error ) {
			logError("dbgpu: xgpuSetHostInputBuffer failed");
			cout << xgpu_error << endl;
			throw std::runtime_error("xgpuSetHostInputBuffer failed");
		}
		xgpu_error = xgpuSetHostOutputBuffer(m_xgpu);
		if( xgpu_error ) {
			logError("dbgpu: xgpuSetHostOutputBuffer failed");
			cout << xgpu_error << endl;
			throw std::runtime_error("xgpuSetHostOutputBuffer failed");
		}
		
		int  sync_op = SYNCOP_NONE;//SYNCOP_SYNC_COMPUTE;
		bool clear_integration = false;
		
		if( ++m_subintegration == m_ntime_integrate ) {
			sync_op = SYNCOP_DUMP;
			clear_integration = true;
			m_subintegration = 0;
			bytes_written = m_xgpu_info.matLength * sizeof(Complex);
		}
		
		xgpu_error = xgpuCudaXengine(m_xgpu, sync_op);
		if( xgpu_error ) {
			logError("dbgpu: xgpuCudaXengine failed");
			cout << xgpu_error << endl;
			throw std::runtime_error("xgpuCudaXengine failed");
		}
	/*	
		// Extract, compute and write total power from specified inputs
		// Note: This will run concurrently with xGPU when not dumping
		if( m_tp_inputs.size() ) {
			size_t ninput    = m_xgpu_info.nstation * 2;
			size_t tp_ninput = m_tp_inputs.size();
			
			//size_t nrecord = 2;
			size_t is = m_cycle / m_tp_ncycles % (tp_ninput/m_tp_nrecord) * m_tp_nrecord;
			//cout << "Recording total power from antenna " << is << endl;
			cout << "Recording hires cross corr for input group " << is << endl;
			
			// TODO: Could optimise this by making m_tp_inputs a static array
			for( size_t j=0; j<m_xgpu_info.vecLength / ninput; ++j ) {
				//for( size_t i=0; i<m_tpinputs.size(); ++i ) {
				//for( size_t is=0; is<tp_ninput; is+=2 ) {
				for( size_t ip=0; ip<m_tp_nrecord; ++ip ) {
					//ComplexInput a = ((ComplexInput*)data_in)[j*ninput+m_tp_inputs[is+ip*2+0]];
					//ComplexInput b = ((ComplexInput*)data_in)[j*ninput+m_tp_inputs[is+ip*2+1]];
					//((ComplexInput*)m_tp_out)[j*2+ip] = conj_mult(a, b);
					ComplexInput a = ((ComplexInput*)data_in)[j*ninput+m_tp_inputs[is+ip]];
					m_tp_out[j*m_tp_nrecord+ip] = pack44(a);
				}
				/*
					for( size_t ip=0; ip<2; ++ip ) {
						size_t i = is + ip;
						size_t inp = m_tp_inputs[i];
						ComplexInput val = ((ComplexInput*)data_in)[j*ninput+inp];
						//m_tp_out[j*tp_ninput+i] = total_power(val);
						m_tp_out[j*2+ip] = total_power(val);
						//m_tp_ptr[j*tp_ninput+i] = total_power(val);
					}
					//}
				*/
	/*		}
			//cout << "Calling advanceWrite" << endl;
			m_tp_outstream->write((char*)&m_tp_out[0],
			                      m_tp_out.size()*sizeof(tptype));
			// Hard system IO sync
			//sync();
			//m_tp_ptr = (tptype*)m_tp_buf.advanceWrite(m_tp_size);
			//cout << "  done" << endl;
		}
		
		if( m_bp_outstream ) {
			size_t ntime    = m_xgpu_info.ntime;
			size_t nchan    = m_xgpu_info.nfrequency;
			size_t nstation = m_xgpu_info.nstation;
			const ComplexInput* in = (ComplexInput*)data_in;
			for( size_t t=0; t<ntime; ++t ) {
				for( size_t c=0; c<nchan; ++c ) {
					for( size_t s=0; s<nstation; ++s ) {
						size_t in_idx  = s + nstation*(c + nchan*t);
						size_t out_idx = s + nstation*c;
						// Note: This assumes 2 pols
						m_bandpasses[2*out_idx+0].real += in[2*in_idx+0].real*in[2*in_idx+0].real;
						m_bandpasses[2*out_idx+0].imag += in[2*in_idx+0].imag*in[2*in_idx+0].imag;
						m_bandpasses[2*out_idx+1].real += in[2*in_idx+1].real*in[2*in_idx+1].real;
						m_bandpasses[2*out_idx+1].imag += in[2*in_idx+1].imag*in[2*in_idx+1].imag;
					}
				}
			}
			// Normalise (and undo unpacking bitshift)
			for( size_t c=0; c<nchan; ++c ) {
				for( size_t s=0; s<nstation; ++s ) {
					size_t out_idx = s + nstation*c;
					m_bandpasses[2*out_idx+0].real = sqrt(m_bandpasses[2*out_idx+0].real / ((1<<4) * ntime));
					m_bandpasses[2*out_idx+0].imag = sqrt(m_bandpasses[2*out_idx+0].imag / ((1<<4) * ntime));
					m_bandpasses[2*out_idx+1].real = sqrt(m_bandpasses[2*out_idx+1].real / ((1<<4) * ntime));
					m_bandpasses[2*out_idx+1].imag = sqrt(m_bandpasses[2*out_idx+1].imag / ((1<<4) * ntime));
				}
			}
			m_bp_outstream->write((char*)&m_bandpasses[0],
			                      m_bandpasses.size()*sizeof(Complex));
		}
	*/	
		// Manually sync xGPU
		cudaThreadSynchronize();
		
		if( clear_integration ) {
			xgpu_error = xgpuClearDeviceIntegrationBuffer(m_xgpu);
			if( xgpu_error ) {
				logError("dbgpu: xgpuClearDeviceIntegrationBuffer failed");
				throw std::runtime_error("xgpuClearDeviceIntegrationBuffer failed");
			}
			
			// Note: This being done here is somewhat arbitrary
			// Hard system IO sync
			// WARNING: This caused massive packet loss at NM.
			//            It doesn't seem to be necessary.
			//sync();
		}
		
		//timer.stop();
		//cout << "xGPU speed: " << in_size / timer.getTime() / 1e6 << " MB/s" << endl;
		
		++m_cycle;
		
		return bytes_written;
	}
};

void usage() {
	cout <<
		"dbgpu [options] in_key out_key\n"
		" -v         verbose mode\n"
		" -c core    bind process to CPU core\n"
		" -d device  gpu device (default 0)\n"
		" -t count   no. NTIMEs to integrate (default 1)\n"
		" -p tpfile  filename for total power output\n"
		" -n cycles  no. NTIMEs to record each total power antenna for (100)\n"
		" -N ninputs no. inputs to record simultaneously (2)\n"
		" -b bpfile  filename for bandpass recording\n"
		" -r         disable host memory pinning\n"
		" -h         print usage" << endl;
}

int main(int argc, char* argv[])
{
	key_t       in_key  = 0;
	key_t       out_key = 0;
	multilog_t* log     = 0;
	int         verbose = 0;
	int         gpu_idx = 0;
	size_t      ntime_integrate = 1;
	int         do_register = 1;
	int         core = -1;
	std::string tp_filename = "";
	int         tp_ncycles = 100;
	int         tp_nrecord = 2; // no. inputs
	std::string bp_filename = "";
	
	int arg = 0;
	while( (arg = getopt(argc,argv,"d:t:c:p:n:b:rhv")) != -1 ) {
		switch (arg){
		case 'd':
			if( optarg ) {
				gpu_idx = atoi(optarg);
				break;
			}
			else {
				fprintf(stderr, "ERROR: -d flag requires argument\n");
				return EXIT_FAILURE;
			}
		case 't':
			if( optarg ) {
				ntime_integrate = atoi(optarg);
				break;
			}
			else {
				fprintf(stderr, "ERROR: -t flag requires argument\n");
				return EXIT_FAILURE;
			}
		case 'c':
			if( optarg ) {
				core = atoi(optarg);
				break;
			}
			else {
				fprintf(stderr, "ERROR: -c flag requires argument\n");
				return EXIT_FAILURE;
			}
		case 'p':
			if( optarg ) {
				tp_filename = optarg;
				break;
			}
			else {
				fprintf(stderr, "ERROR: -p flag requires argument\n");
				return EXIT_FAILURE;
			}
		case 'n':
			if( optarg ) {
				tp_ncycles = atoi(optarg);
				break;
			}
			else {
				fprintf(stderr, "ERROR: -n flag requires argument\n");
				return EXIT_FAILURE;
			}
		case 'b':
			if( optarg ) {
				bp_filename = optarg;
				break;
			}
			else {
				fprintf(stderr, "ERROR: -b flag requires argument\n");
				return EXIT_FAILURE;
			}
		case 'N':
			if( optarg ) {
				tp_nrecord = atoi(optarg);
				break;
			}
			else {
				fprintf(stderr, "ERROR: -N flag requires argument\n");
				return EXIT_FAILURE;
			}
		case 'h':
			usage();
			return EXIT_SUCCESS;
		case 'v':
			verbose++;
			break;
		case 'r':
			do_register = 0;
			break;
		}
	}
	
	int num_args = argc-optind;
	if( num_args != 2 ) {
		usage();
		return EXIT_FAILURE;
	}
	
	if( verbose ) {
		fprintf(stderr, "dbgpu: parsing input key=%s\n", argv[optind]);
	}
	
	unsigned int tmp; // WAR for sscanf into signed key_t
	if( sscanf(argv[optind], "%x", &tmp) != 1 ) {
		fprintf(stderr, "dbgpu: could not parse in key from %s\n",
		         argv[optind]);
		return EXIT_FAILURE;
	}
	in_key = tmp;
	
	if( verbose ) {
		fprintf(stderr, "dbgpu: parsing output key=%s\n", argv[optind+1]);
	}
	if( sscanf(argv[optind+1], "%x", &tmp) != 1 ) {
		fprintf(stderr, "dbgpu: could not parse out key from %s\n",
		        argv[optind+1]);
		return EXIT_FAILURE;
	}
	out_key = tmp;
	
	if( core >= 0 ) {
		if( verbose ) {
			fprintf(stderr, "dbgpu: binding to core %d\n", core);
		}
		if( dada_bind_thread_to_core(core) < 0 ) {
			fprintf(stderr, "dbgpu: failed to bind to core %d\n", core);
		}
	}
	
	log = multilog_open("dbgpu", 0);
	
	multilog_add(log, stderr);
	
	dbgpu ctx(log, verbose, ntime_integrate, gpu_idx, do_register);
	
	std::ofstream tp_outfile;
	if( tp_filename != "" ) {
		
		std::string      tp_inputs_filename = "total_power_inputs.txt";
		std::ifstream    tp_inputs_file(tp_inputs_filename.c_str());
		if( !tp_inputs_file ) {
			fprintf(stderr,
			        "dbgpu: failed to open %s\n",tp_inputs_filename.c_str());
			return -1;
		}
		std::vector<int> tp_inputs;
		tp_inputs.assign(std::istream_iterator<int>(tp_inputs_file),
		                 std::istream_iterator<int>());
		if( verbose ) {
			fprintf(stderr, "dbgpu: read %lu total power inputs from %s\n",
			        tp_inputs.size(),
			        tp_inputs_filename.c_str());
		}
		tp_outfile.open(tp_filename.c_str(), std::ios::binary);
		if( !tp_outfile ) {
			fprintf(stderr,
			        "dbgpu: failed to open output file %s\n",tp_filename.c_str());
			return -1;
		}
		ctx.setTotalPowerInputs(&tp_inputs[0], tp_inputs.size(),
		                        tp_ncycles, tp_nrecord, tp_outfile);
	}
	
	std::ofstream bp_outfile;
	if( bp_filename != "" ) {
		bp_outfile.open(bp_filename.c_str(), std::ios::binary);
		if( !tp_outfile ) {
			fprintf(stderr,
			        "dbgpu: failed to open output file %s\n",bp_filename.c_str());
			return -1;
		}
		ctx.setBandpassStream(bp_outfile);
	}
	
	ctx.connect(in_key, out_key);
	ctx.run();
	ctx.disconnect();
	
	return 0;
}
