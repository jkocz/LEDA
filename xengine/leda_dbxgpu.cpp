
#include <cstdio>
#include <cstdlib>
#include <cstring> // For memcpy
#include <stdexcept>
#include <vector>
#include <string>
#include <iostream>
using std::cout;
using std::endl;
#include <errno.h>       // For errno
#include <sys/syscall.h> // For SYS_gettid

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

class dbgpu : public dada_db2db {
	size_t               m_ntime_integrate;
	size_t               m_subintegration;
	int                  m_gpu_device;
	XGPUContext*         m_xgpu;
	XGPUInfo             m_xgpu_info;
	bool                 m_do_register;
public:
	dbgpu(multilog_t* log, int verbose,
	      size_t ntime_integrate,
	      int gpu_device=0,
	      bool do_register=false)
		: dada_db2db(log, verbose),
		  m_ntime_integrate(ntime_integrate),
		  m_subintegration(0),
		  m_gpu_device(gpu_device),
		  m_do_register(do_register) {
		
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
	
	// Return desired no. bytes per data read
	virtual uint64_t onHeader(uint64_t header_size,
	                          const char* header_in, char* header_out) {
		// copy the in header to the out header
		memcpy(header_out, header_in, header_size);
		
		// need to change some DADA parameters
		if( ascii_header_set(header_out, "NBIT", "%d", 32) < 0 ) {
			logInfo("dbgpu: Failed to set NBIT 32 in header_out");
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
		
		int  sync_op = SYNCOP_SYNC_COMPUTE;
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
		
		if( clear_integration ) {
			xgpu_error = xgpuClearDeviceIntegrationBuffer(m_xgpu);
			if( xgpu_error ) {
				logError("dbgpu: xgpuClearDeviceIntegrationBuffer failed");
				throw std::runtime_error("xgpuClearDeviceIntegrationBuffer failed");
			}
		}
		
		//timer.stop();
		//cout << "xGPU speed: " << in_size / timer.getTime() / 1e6 << " MB/s" << endl;
		
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
	
	int arg = 0;
	while( (arg = getopt(argc,argv,"d:t:c:rhv")) != -1 ) {
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
	ctx.connect(in_key, out_key);
	ctx.run();
	
	return 0;
}
