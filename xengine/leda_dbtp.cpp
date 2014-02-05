
/*
  leda_dbtp
  Deals with total power inputs by blanking samples on state transition edges,
    blanking non-sky states and integrating total power samples.
  
  Ben Barsdell (2014)
  
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
#include <sstream>
#include <errno.h>       // For errno
#include <sys/syscall.h> // For SYS_gettid

#include <dada_def.h>
#include <dada_affinity.h>
#include <ascii_header.h>

#include "dada_db2db.hpp"

// For benchmarking only
#include "stopwatch.hpp"

struct ComplexInput {
	char real;
	char imag;
};

inline unsigned char total_power(const ComplexInput& c) {
	// Note: Max power from 4+4b input = -8^2 + -8^2 = 128
	//       The input values are actually only the high 4b of 8b memory
	return (c.real*c.real + c.imag*c.imag) >> (4+4);
}

class dbtp : public dada_db2db {
	size_t m_buf_idx;
	size_t m_bufs_per_state;
	size_t m_state_idx;
	size_t m_nstates;
	
	int   m_ntime;
	int   m_nchan;
	int   m_ninput;
	float m_chan_width_mhz;
	
	// Total power variables
	typedef float tptype;
	int                  m_tp_navg;
	std::vector<size_t>  m_tp_inputs;
	std::vector<tptype>  m_tp_accums;
	std::ofstream        m_tp_outstream;
	std::string          m_tp_outpath;
	float                m_tp_edge_time_s;
	int                  m_tp_sky_state;
public:
	dbtp(multilog_t* log, int verbose)
		: dada_db2db(log, verbose),
		  m_buf_idx(0),
		  m_bufs_per_state(3), // TODO: Set dynamically?
		  m_state_idx(0),
		  m_nstates(3), // TODO: Set dynamically?
		  m_tp_edge_time_s(0) {}
	virtual ~dbtp() {}
	
	void setTotalPowerInputs(const int* tp_inputs, size_t tp_ninputs,
	                         float tp_switch_edge_time_secs,
	                         const char* tp_outpath) {
		m_tp_inputs.assign(tp_inputs, tp_inputs + tp_ninputs);
		m_tp_edge_time_s = tp_switch_edge_time_secs;
		m_tp_outpath = tp_outpath;
	}
	
	virtual void onConnect(key_t in_key, key_t out_key) {}
	virtual void onDisconnect() {}
	
	// Return desired no. bytes per data read
	virtual uint64_t onHeader(uint64_t header_size,
	                          const char* header_in, char* header_out) {
		// copy the in header to the out header
		memcpy(header_out, header_in, header_size);
		
		if( ascii_header_get(header_in, "XENGINE_NTIME", "%i", &m_ntime) < 0 ) {
			throw std::runtime_error("Missing header entry XENGINE_NTIME");
		}
		if( ascii_header_get(header_in, "NCHAN", "%i", &m_nchan) < 0 ) {
			throw std::runtime_error("Missing header entry NCHAN");
		}
		int nstation;
		if( ascii_header_get(header_in, "NSTATION", "%i", &nstation) < 0 ) {
			throw std::runtime_error("Missing header entry NSTATION");
		}
		int npol;
		if( ascii_header_get(header_in, "NPOL", "%i", &npol) < 0 ) {
			throw std::runtime_error("Missing header entry NPOL");
		}
		m_ninput = nstation * npol;
		if( ascii_header_get(header_in, "SKY_STATE_PHASE", "%i", &m_tp_sky_state) < 0 ) {
			//throw std::runtime_error("Missing header entry SKY_STATE_PHASE");
			logWarning("dbtp: Missing header entry SKY_STATE_PHASE; defaulting to 0");
			m_tp_sky_state = 0;
		}
		
		if( ascii_header_get(header_in, "CHAN_WIDTH", "%f", &m_chan_width_mhz) < 0 ) {
			float tsamp_us;
			if( ascii_header_get(header_in, "TSAMP", "%f", &tsamp_us) < 0 ) {
				throw std::runtime_error("Missing header entry CHAN_WIDTH or TSAMP");
			}
			m_chan_width_mhz = 1. / tsamp_us;
		}
		// TODO: This assumes TP averages are 1s
		m_tp_navg = (size_t)(1. * m_chan_width_mhz*1e6 + 0.5);
		
		// Create header for total power data
		// TODO: Add info about starting state!
		std::vector<char> tp_header(header_in, header_in + header_size);
		if( ascii_header_set(&tp_header[0], "NBIT", "%d", 32) < 0 ) {
			logInfo("dbtp: Failed to set NBIT 32 in tp_header");
		}
		if( ascii_header_set(&tp_header[0], "NDIM", "%d", 1) < 0 ) {
			logInfo("dbtp: Failed to set NDIM 1 in tp_header");
		}
		if( ascii_header_set(&tp_header[0], "NSTATION", "%d", m_tp_inputs.size()/2) < 0 ) {
			logInfo("dbtp: Failed to set NSTATION in tp_header");
		}
		if( ascii_header_set(&tp_header[0], "NAVG", "%d", m_tp_navg) < 0 ) {
			logInfo("dbtp: Failed to set NAVG in tp_header");
		}
		if( ascii_header_set(&tp_header[0], "SOURCE", "%s", "SWITCHING_TOTAL_POWER") < 0 ) {
			logInfo("dbtp: Failed to set SOURCE in tp_header");
		}
		if( ascii_header_set(&tp_header[0], "DATA_ORDER", "%s", "STATE_CHAN_INPUT") < 0 ) {
			logInfo("dbtp: Failed to set DATA_ORDER in tp_header");
		}
		// Create string listing TP inputs
		int tp_ninputs = m_tp_inputs.size();
		std::stringstream ss;
		ss << "[";
		for( int tpi=0; tpi<tp_ninputs-1; ++tpi ) {
			// Note: Converts to 1-based indexing
			ss << m_tp_inputs[tpi] + 1 << ",";
		}
		ss << m_tp_inputs[tp_ninputs-1] << "]";
		const char* tp_inputs_string = ss.str().c_str();
		if( ascii_header_set(&tp_header[0], "INPUTS", "%s", tp_inputs_string) < 0 ) {
			logInfo("dbtp: Failed to set DATA_ORDER in tp_header");
		}
		
		char utc_start_str[32];
		if( ascii_header_get(header_in, "UTC_START", "%s", utc_start_str) < 0 ) {
			throw std::runtime_error("Missing header entry UTC_START");
		}
		
		// Open total power output file
		// TODO: This should probably be less hard-coded
		if( m_tp_outpath != "" ) {
			std::string tp_filename = m_tp_outpath + "/" + utc_start_str + ".tp";
			m_tp_outstream.open(tp_filename.c_str());
			
			// Write the total power header
			m_tp_outstream.write(&tp_header[0],
			                     tp_header.size()*sizeof(char));
		}
		
		m_buf_idx   = 0;
		m_state_idx = 0;
		
		// Allocate total power accumulation memory
		size_t tpsize = m_nchan * tp_ninputs * m_nstates;
		m_tp_accums.resize(tpsize, 0);
		std::fill(m_tp_accums.begin(), m_tp_accums.end(), 0);
		
		size_t   sample_count   = m_ntime * m_nchan * m_ninput;
		uint64_t bytes_per_read = sample_count * sizeof(ComplexInput);
		return bytes_per_read;
	}
	
	// Return no. bytes written
	virtual uint64_t onData(uint64_t in_size,
	                        const char* data_in, char* data_out) {
		uint64_t bytes_written = 0;
		
		Stopwatch timer;
		timer.start();
		
		// Copy input to output
		memcpy(data_out, data_in, in_size);
		bytes_written = in_size;
		
		// Note: data_in order is (time, chan, station, pol, dim)
		
		ComplexInput* samples = (ComplexInput*)data_out;
		
		// First we zap samples that are on the edge of a state transition
		int m_tp_ninputs = m_tp_inputs.size();
		int nedge = m_chan_width_mhz*1e6*m_tp_edge_time_s/2;
		int buf_position = m_buf_idx % m_bufs_per_state;
		int tp_offset;
		
		// TODO: Remove this when done testing
		cout << "nedge = " << nedge << endl;
		
		if( buf_position == 0 ) {
			tp_offset = 0;
		}
		else if( buf_position == (m_bufs_per_state-1) ) {
			tp_offset = m_ntime - nedge;
		}
		if( buf_position == 0 || buf_position == (m_bufs_per_state-1) ) {
			for( int t=tp_offset; t<tp_offset+nedge; ++t ) {
				for( int c=0; c<m_nchan; ++c ) {
					for( int tpi=0; tpi<m_tp_ninputs; ++tpi ) {
						int i = m_tp_inputs[tpi];
						size_t idx = i + m_ninput*(c + m_nchan*t);
						samples[idx].real = 0;
						samples[idx].imag = 0;
					}
				}
			}
		}
		
		// Next we extract and integrate samples from total power inputs
		// Note: TP output order is: (state, chan, tp_input)
		// We also zero-out samples from TP inputs when in off-sky states
		int switch_state = m_state_idx % m_nstates;
		for( int t=0; t<m_ntime; ++t ) {
			for( int c=0; c<m_nchan; ++c ) {
				for( int tpi=0; tpi<m_tp_ninputs; ++tpi ) {
					int i = m_tp_inputs[tpi];
					// Extract
					size_t src_idx = i + m_ninput*(c + m_nchan*t);
					ComplexInput samp = samples[src_idx];
					// Integrate
					size_t dst_idx = tpi + m_tp_ninputs*(c + m_nchan*switch_state);
					m_tp_accums[dst_idx] += total_power(samp);
					// Zero-out
					if( switch_state != m_tp_sky_state ) {
						samples[src_idx].real = 0;
						samples[src_idx].imag = 0;
					}
				}
			}
		}
		
		// Now dump the TP integrations to disk if this is the end of a cycle
		// Note: This will run concurrently with xGPU when it's not dumping
		if( switch_state == (m_nstates-1) &&
		    buf_position == (m_bufs_per_state-1) ) {
			if( m_tp_outstream ) {
				size_t tp_size = m_tp_accums.size() * sizeof(tptype);
				cout << "Writing " << tp_size/1e3 << " kB "
				     << "of total power data to disk" << endl;
				m_tp_outstream.write((char*)&m_tp_accums[0],
				                     tp_size);
			}
			cout << "Resetting total power integrations" << endl;
			std::fill(m_tp_accums.begin(), m_tp_accums.end(), 0);
		}
		
		timer.stop();
		size_t nsamps = in_size / sizeof(ComplexInput) / m_ninput;
		cout << "Processing time:  " << timer.getTime() << " s" << endl;
		cout << "           speed: " << in_size / timer.getTime() / 1e9 << " GB/s" << endl;
		cout << "           BW:    " << nsamps / timer.getTime() / 1e6 << " MHz" << endl;
		
		++m_buf_idx;
		buf_position = m_buf_idx % m_bufs_per_state;
		if( buf_position == 0 ) {
			++m_state_idx;
		}
		
		return bytes_written;
	}
};

void usage() {
	cout <<
		"dbtp [options] in_key out_key\n"
		" -v         verbose mode\n"
		" -c core    bind process to CPU core\n"
		" -p path    path for total power output (default: no TP output)\n"
		" -e ms      time to blank around state change edges (default 1.5 ms)\n"
		" -h         print usage" << endl;
}

int main(int argc, char* argv[])
{
	key_t       in_key  = 0;
	key_t       out_key = 0;
	multilog_t* log     = 0;
	int         verbose = 0;
	int         core = -1;
	std::string tp_outpath = "";
	float       tp_edge_time_ms = 1.5;
	
	int arg = 0;
	while( (arg = getopt(argc,argv,"c:p:e:hv")) != -1 ) {
		switch (arg){
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
				tp_outpath = optarg;
				break;
			}
			else {
				fprintf(stderr, "ERROR: -p flag requires argument\n");
				return EXIT_FAILURE;
			}
		case 'e':
			if( optarg ) {
				tp_edge_time_ms = atof(optarg);
				break;
			}
			else {
				fprintf(stderr, "ERROR: -e flag requires argument\n");
				return EXIT_FAILURE;
			}
		case 'h':
			usage();
			return EXIT_SUCCESS;
		case 'v':
			verbose++;
			break;
		}
	}
	
	int num_args = argc-optind;
	if( num_args != 2 ) {
		usage();
		return EXIT_FAILURE;
	}
	
	if( verbose ) {
		fprintf(stderr, "dbtp: parsing input key=%s\n", argv[optind]);
	}
	
	unsigned int tmp; // WAR for sscanf into signed key_t
	if( sscanf(argv[optind], "%x", &tmp) != 1 ) {
		fprintf(stderr, "dbtp: could not parse in key from %s\n",
		        argv[optind]);
		return EXIT_FAILURE;
	}
	in_key = tmp;
	
	if( verbose ) {
		fprintf(stderr, "dbtp: parsing output key=%s\n", argv[optind+1]);
	}
	if( sscanf(argv[optind+1], "%x", &tmp) != 1 ) {
		fprintf(stderr, "dbtp: could not parse out key from %s\n",
		        argv[optind+1]);
		return EXIT_FAILURE;
	}
	out_key = tmp;
	
	if( core >= 0 ) {
		if( verbose ) {
			fprintf(stderr, "dbtp: binding to core %d\n", core);
		}
		if( dada_bind_thread_to_core(core) < 0 ) {
			fprintf(stderr, "dbtp: failed to bind to core %d\n", core);
		}
	}
	
	log = multilog_open("dbtp", 0);
	
	multilog_add(log, stderr);
	
	dbtp ctx(log, verbose);
		
	std::string      tp_inputs_filename = "total_power_inputs.txt";
	std::ifstream    tp_inputs_file(tp_inputs_filename.c_str());
	if( !tp_inputs_file ) {
		fprintf(stderr,
		        "dbtp: failed to open %s\n",tp_inputs_filename.c_str());
		return -1;
	}
	std::vector<int> tp_inputs;
	tp_inputs.assign(std::istream_iterator<int>(tp_inputs_file),
	                 std::istream_iterator<int>());
	if( verbose ) {
		fprintf(stderr, "dbtp: read %lu total power inputs from %s\n",
		        tp_inputs.size(),
		        tp_inputs_filename.c_str());
	}
		
	ctx.setTotalPowerInputs(&tp_inputs[0], tp_inputs.size(),
	                        tp_edge_time_ms * 1e-3,
	                        tp_outpath.c_str());
	
	ctx.connect(in_key, out_key);
	ctx.run();
	ctx.disconnect();
	
	return 0;
}
