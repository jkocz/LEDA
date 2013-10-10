
/*
  Simple channel extractor for baseband recording
  
  Extracts and re-packs the first noutchan channels to 4+4bit format,
    allowing all signals to be written at the full time resolution over
    a (small) subset of channels.
  
  By Ben Barsdell (2013)
*/

#include <cstdio>
#include <cstdlib>
#include <cstring> // For memcpy
#include <stdexcept>
#include <vector>
#include <string>
#include <iostream>
using std::cout;
using std::cerr;
using std::endl;
#include <fstream>
#include <sstream>
#include <iterator>
#include <cmath>

#include <errno.h>       // For errno
#include <sys/syscall.h> // For SYS_gettid

#include <dada_def.h>
#include <ascii_header.h>

#include "dada_db2db.hpp"

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

struct ComplexInput {
	char real;
	char imag;
};

inline unsigned char pack44(const ComplexInput& a) {
	unsigned char x = 0;
	x |= (a.real >> 4) & 0xF;
	x |= (a.imag >> 0) & 0xF0;
	return x;
}

class dbbaseband : public dada_db2db {
	typedef ComplexInput  intype;
	typedef unsigned char outtype;
	
	size_t m_ninchan;
	size_t m_noutchan;
	size_t m_ninput;
	
protected:
	virtual void     onConnect(key_t in_key, key_t out_key) {}
	virtual void     onDisconnect() {}
	virtual uint64_t onHeader(uint64_t    header_size,
	                          const char* header_in,
	                          char*       header_out) {
		// Copy the in header to the out header
		memcpy(header_out, header_in, header_size);
		
		// Read header parameters
		int ret;
		ret = ascii_header_get(header_in, "NCHAN", "%lu", &m_ninchan);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry NCHAN"); }
		size_t nstation, npol;
		ret = ascii_header_get(header_in, "NSTATION", "%lu", &nstation);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry NSTATION"); }
		ret = ascii_header_get(header_in, "NPOL", "%lu", &npol);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry NPOL"); }
		m_ninput = nstation * npol;
		
		// Write updated header parameters
		if( ascii_header_set(header_out, "NCHAN", "%lu", m_noutchan) < 0 ) {
			logInfo("dbbaseband: Failed to set NCHAN in header_out");
		}
		if( ascii_header_set(header_out, "NBIT", "%d", 4) < 0 ) {
			logInfo("dbbaseband: Failed to set NBIT 4 in header_out");
		}
		if( ascii_header_set(header_out, "NDIM", "%d", 2) < 0 ) {
			logInfo("dbbaseband: Failed to set NDIM 2 in header_out");
		}
		uint64_t outsize = ( this->bufsize_in() *
		                     m_noutchan*sizeof(outtype) /
		                     (m_ninchan*sizeof(intype)) );
		uint64_t max_filesize = 2ull*1024*1024*1024;
		uint64_t bytes_per_second = (max_filesize-header_size) / (outsize * 10) * outsize;
		if( ascii_header_set(header_out, "BYTES_PER_SECOND", "%i", bytes_per_second) < 0 ) {
			logInfo("dbbaseband: Failed to set BYTES_PER_SECOND in header_out");
		}
		if( ascii_header_set(header_out, "DATA_ORDER", "%s", "time_chan_station_pol_cpx_4b") < 0 ) {
			logInfo("dbbaseband: Failed to set DATA_ORDER in header_out");
		}
		if( ascii_header_set(header_out, "SOURCE", "%s", "DRIFT") < 0 ) {
			logInfo("dbbaseband: Failed to set SOURCE in header_out");
		}
		if( ascii_header_set(header_out, "MODE", "%s", "BASEBAND_NARROW") < 0 ) {
			logInfo("dbbaseband: Failed to set MODE in header_out");
		}
		
		size_t bytes_per_read = this->bufsize_in();
		return bytes_per_read;
	}
	// Return no. bytes written
	virtual uint64_t onData(uint64_t    in_size,
	                        const char* data_in,
	                        char*       data_out) {
		const intype* __restrict__ in  = (const intype*)data_in;
		outtype*      __restrict__ out =      (outtype*)data_out;
		
		size_t ntime = in_size / (m_ninchan*m_ninput*sizeof(intype));
		
		// Extract and re-pack the first m_noutchan channels
		// Input data order: time freq station pol complex 8b
		for( size_t t=0; t<ntime; ++t ) {
			for( size_t oc=0; oc<m_noutchan; ++oc ) {
				for( size_t i=0; i<m_ninput; ++i ) {
					size_t ic = oc; // Extract the first m_noutchan channels
					intype   inval  =  in[i + m_ninput*(ic + m_ninchan*t)];
					outtype& outval = out[i + m_ninput*(oc + m_noutchan*t)];
					outval = pack44(inval);
				}
			}
		}
		
		size_t bytes_written = ntime*m_noutchan*m_ninput*sizeof(outtype);
		return bytes_written;
	}
	
public:
	dbbaseband(multilog_t* log, int verbose,
	           size_t noutchan)
		: dada_db2db(log, verbose),
		  m_noutchan(noutchan) {}
	virtual ~dbbaseband() {}
};

bool parse_arg_typed(int& x)                { return sscanf(optarg, "%i", &x) == 1; }
bool parse_arg_typed(unsigned& x)           { return sscanf(optarg, "%u", &x) == 1; }
bool parse_arg_typed(unsigned long& x)      { return sscanf(optarg, "%lu", &x) == 1; }
bool parse_arg_typed(long long& x)          { return sscanf(optarg, "%lli", &x) == 1; }
bool parse_arg_typed(unsigned long long& x) { return sscanf(optarg, "%llu", &x) == 1; }
bool parse_arg_typed(float& x)              { return sscanf(optarg, "%f", &x) == 1; }
bool parse_arg_typed(std::string& x)        { x = optarg; return true; }
template<typename T>
bool parse_arg(char c, T& x) {
	if( !optarg ) {
		cerr << "ERROR: -" << c << " flag requires an argument" << endl;
		return false;
	}
	else if( !parse_arg_typed(x) ) {
		cerr << "ERROR: Could not parse -" << c << " " << optarg << endl;
		return false;
	}
	else {
		return true;
	}
}

void print_usage() {
	cout << 
		"dbbaseband [options] -- in_key out_key\n"
		" -f nchan     No. channels to extract [=1]\n"
		" -c core      Bind process to CPU core\n"
		" -v           Increase verbosity\n"
		" -q           Decrease verbosity\n"
		" -h           Print usage\n" << endl;
}

int main(int argc, char* argv[])
{
	size_t      noutchan     = 1;
	int         core         = -1;
	int         verbose      = 0;
	key_t       in_key       = 0;
	key_t       out_key      = 0;
	multilog_t* log          = 0;
	
	int arg = 0;
	while( (arg = getopt(argc,argv,"f:c:hvq")) != -1 ) {
		switch( arg ) {
		case 'f': if( !parse_arg('f', noutchan) ) return -1; break;
		case 'c': if( !parse_arg('c', core) ) return -1; break;
		case 'h': print_usage(); return 0;
		case 'v': ++verbose; break;
		case 'q': --verbose; break;
		default: cerr << "WARNING: Unexpected flag -" << arg << endl; break;
		}
	}
	int num_args = argc - optind;
	if( num_args != 2 ) {
		cerr << "ERROR: Expected exactly 2 required args, got " << num_args << endl;
		print_usage();
		return -1;
	}
	unsigned int tmp;
	if( sscanf(argv[optind+0], "%x", &tmp) != 1 ) {
		cerr << "ERROR: Could not parse buffer key from "
		     << argv[optind+0] << endl;
		return -1;
	}
	in_key = tmp;
	if( sscanf(argv[optind+1], "%x", &tmp) != 1 ) {
		cerr << "ERROR: Could not parse buffer key from "
		     << argv[optind+1] << endl;
		return -1;
	}
	out_key = tmp;
	
	if( verbose >= 1 ) {
		cout << "Noutchan   = " << noutchan << endl;
		cout << "In key     = " << std::hex << in_key << std::dec << endl;
		cout << "Out key    = " << std::hex << out_key << std::dec << endl;
	}
	
	log = multilog_open("dbbaseband", 0);
	multilog_add(log, stderr);
	
	if( core >= 0 ) {
		if( dada_bind_thread_to_core(core) < 0 ) {
			cerr << "WARNING: Failed to bind to core " << core << endl;
		}
		if( verbose >= 1 ) {
			cout << "Process bound to core " << core << endl;
		}
	}
	
	dbbaseband ctx(log, verbose, noutchan);
	ctx.connect(in_key, out_key);
	ctx.run();
	ctx.disconnect();
	
	return 0;
}
