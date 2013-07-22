
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

struct uchar8 {
	unsigned char s0, s1, s2, s3, s4, s5, s6, s7;
};
struct ushort4 {
	unsigned short x, y, z, w;
};

class dbupdb512 : public dada_db2db {
	size_t m_ntime, m_nchan, m_nstation, m_npol;
	
protected:
	virtual void     onConnect(key_t in_key, key_t out_key) {}
	virtual void     onDisconnect() {}
	// Return desired no. bytes per data read
	virtual uint64_t onHeader(uint64_t    header_size,
	                          const char* header_in,
	                          char*       header_out) {
		// Copy the in header to the out header
		memcpy(header_out, header_in, header_size);
		/*
		size_t nchan, nstation, npol;
		ret = ascii_header_get(header_in, "NCHAN", "%lu", &nchan);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry NCHAN"); }
		ret = ascii_header_get(header_in, "NSTATION", "%lu", &nstation);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry NSTATION"); }
		ret = ascii_header_get(header_in, "NPOL", "%lu", &npol);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry NPOL"); }
		*/
		//size_t bytes_per_read = ntime * nchan * nstation * npol * sizeof(unsigned char);
		size_t bytes_per_read = this->bufsize_in();
		return bytes_per_read;
	}
	// Return no. bytes written
	virtual uint64_t onData(uint64_t    in_size,
	                        const char* data_in,
	                        char*       data_out) {
		static const uint16_t four2eight[256] = {
			0x0000, 0x1000, 0x2000, 0x3000, 0x4000, 0x5000, 0x6000, 0x7000,
			0x8000, 0x9000, 0xa000, 0xb000, 0xc000, 0xd000, 0xe000, 0xf000,
			0x1000, 0x1010, 0x2010, 0x3010, 0x4010, 0x5010, 0x6010, 0x7010,
			0x8010, 0x9010, 0xa010, 0xb010, 0xc010, 0xd010, 0xe010, 0xf010,
			0x2000, 0x1020, 0x2020, 0x3020, 0x4020, 0x5020, 0x6020, 0x7020,
			0x8020, 0x9020, 0xa020, 0xb020, 0xc020, 0xd020, 0xe020, 0xf020,
			0x3000, 0x1030, 0x2030, 0x3030, 0x4030, 0x5030, 0x6030, 0x7030,
			0x8030, 0x9030, 0xa030, 0xb030, 0xc030, 0xd030, 0xe030, 0xf030,
			0x4000, 0x1040, 0x2040, 0x3040, 0x4040, 0x5040, 0x6040, 0x7040,
			0x8040, 0x9040, 0xa040, 0xb040, 0xc040, 0xd040, 0xe040, 0xf040,
			0x5000, 0x1050, 0x2050, 0x3050, 0x4050, 0x5050, 0x6050, 0x7050,
			0x8050, 0x9050, 0xa050, 0xb050, 0xc050, 0xd050, 0xe050, 0xf050,
			0x6000, 0x1060, 0x2060, 0x3060, 0x4060, 0x5060, 0x6060, 0x7060,
			0x8060, 0x9060, 0xa060, 0xb060, 0xc060, 0xd060, 0xe060, 0xf060,
			0x7000, 0x1070, 0x2070, 0x3070, 0x4070, 0x5070, 0x6070, 0x7070,
			0x8070, 0x9070, 0xa070, 0xb070, 0xc070, 0xd070, 0xe070, 0xf070,
			0x8000, 0x1080, 0x2080, 0x3080, 0x4080, 0x5080, 0x6080, 0x7080,
			0x8080, 0x9080, 0xa080, 0xb080, 0xc080, 0xd080, 0xe080, 0xf080,
			0x9000, 0x1090, 0x2090, 0x3090, 0x4090, 0x5090, 0x6090, 0x7090,
			0x8090, 0x9090, 0xa090, 0xb090, 0xc090, 0xd090, 0xe090, 0xf090,
			0xa000, 0x10a0, 0x20a0, 0x30a0, 0x40a0, 0x50a0, 0x60a0, 0x70a0,
			0x80a0, 0x90a0, 0xa0a0, 0xb0a0, 0xc0a0, 0xd0a0, 0xe0a0, 0xf0a0,
			0xb000, 0x10b0, 0x20b0, 0x30b0, 0x40b0, 0x50b0, 0x60b0, 0x70b0,
			0x80b0, 0x90b0, 0xa0b0, 0xb0b0, 0xc0b0, 0xd0b0, 0xe0b0, 0xf0b0,
			0xc000, 0x10c0, 0x20c0, 0x30c0, 0x40c0, 0x50c0, 0x60c0, 0x70c0,
			0x80c0, 0x90c0, 0xa0c0, 0xb0c0, 0xc0c0, 0xd0c0, 0xe0c0, 0xf0c0,
			0xd000, 0x10d0, 0x20d0, 0x30d0, 0x40d0, 0x50d0, 0x60d0, 0x70d0,
			0x80d0, 0x90d0, 0xa0d0, 0xb0d0, 0xc0d0, 0xd0d0, 0xe0d0, 0xf0d0,
			0xe000, 0x10e0, 0x20e0, 0x30e0, 0x40e0, 0x50e0, 0x60e0, 0x70e0,
			0x80e0, 0x90e0, 0xa0e0, 0xb0e0, 0xc0e0, 0xd0e0, 0xe0e0, 0xf0e0,
			0xf000, 0x10f0, 0x20f0, 0x30f0, 0x40f0, 0x50f0, 0x60f0, 0x70f0,
			0x80f0, 0x90f0, 0xa0f0, 0xb0f0, 0xc0f0, 0xd0f0, 0xe0f0, 0xf0f0
		};
		/*
		  Input:  [N sequence numbers][16 roaches][4 input groups][2 time samples][109 chans][4 stations][2 pols][2 dims][4 bits]
		  Output: [2*N time samples][109 chans][256 stations][2 pols][2 dims][8 bits]
		
		  This is the approach used here:
		    [16 roaches 4 input groups][2 time samples 109 chans][4 stations 2 pols 2 dims 4 bits]
		    Transpose dims 0<->1, where each input element is 64 bits
		    [2 time samples 109 chans][16 roaches 4 input groups][4 stations 2 pols 2 dims 4 bits]
		*/
#define UNPACK_64_BITS {	\
	uint64_t inword = *in; \
	uchar8   invals = *(uchar8*)&inword; \
	ushort4  outvals0; \
	outvals0.x = four2eight[invals.s0]; \
	outvals0.y = four2eight[invals.s1]; \
	outvals0.z = four2eight[invals.s2]; \
	outvals0.w = four2eight[invals.s3]; \
	ushort4  outvals1; \
	outvals1.x = four2eight[invals.s4]; \
	outvals1.y = four2eight[invals.s5]; \
	outvals1.z = four2eight[invals.s6]; \
	outvals1.w = four2eight[invals.s7]; \
	uint64_t outword0 = *(uint64_t*)&outvals0; \
	uint64_t outword1 = *(uint64_t*)&outvals1; \
	out[0] = outword0; \
	out[1] = outword1; \
	in  += NCHAN*NTIME_PER_PKT; \
	out += 2; \
  }
		
		enum {
			NCHAN          = 109,
			NTIME_PER_PKT  = 2,
			NGROUP_PER_PKT = 4,
			NROACH         = 16,
			GULP_SIZE = NCHAN*NTIME_PER_PKT*NGROUP_PER_PKT*NROACH
		};
		const uint64_t* in  = ((uint64_t*)data_in);
		      uint64_t* out = ((uint64_t*)data_out);
		size_t nwords = in_size / sizeof(uint64_t);
		//#pragma omp parallel for
		for( size_t t=0; t<nwords; t+=GULP_SIZE ) {
			for( size_t tc=0; tc<NCHAN*NTIME_PER_PKT; ++tc ) {
				for( size_t rg=0; rg<NGROUP_PER_PKT*NROACH /* / 16*/; ++rg ) {
					UNPACK_64_BITS;
					/*
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					UNPACK_64_BITS;
					*/
				}
				in -= GULP_SIZE;
				in += 1;
			}
		}
		size_t bytes_written = in_size*2;
		return bytes_written;
	}
public:
	dbupdb512(multilog_t* log, int verbose, int nthreads)
		: dada_db2db(log, verbose) {
		if( nthreads > 1 ) {
			cerr << "WARNING: Ignoring nthreads parameter; not yet implemented!" << endl;
		}
	}
	virtual ~dbupdb512() {}
};

bool parse_arg_typed(int& x)                { return sscanf(optarg, "%i", &x) == 1; }
bool parse_arg_typed(unsigned& x)           { return sscanf(optarg, "%u", &x) == 1; }
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
		"leda_dbupdb_512_new [options] in_key out_key\n"
		" -c core      Bind process to CPU core\n"
		" -n nthreads  Use nthreads threads [1]\n"
		" -b factor    Bit-promotion factor [2]\n"
		" -v           Increase verbosity\n"
		" -q           Decrease verbosity\n"
		" -h           Print usage\n" << endl;
}

int main(int argc, char* argv[])
{
	int         core          = -1;
	int         nthreads      = 1;
	int         bit_promotion = 2;
	int         verbose       = 0;
	key_t       in_key        = 0;
	key_t       out_key       = 0;
	multilog_t* log           = 0;
	
	int arg = 0;
	while( (arg = getopt(argc,argv,"c:n:b:hvq")) != -1 ) {
		switch( arg ) {
		case 'c': if( !parse_arg('c', core) ) return -1; break;
		case 'n': if( !parse_arg('n', nthreads) ) return -1; break;
		case 'b': if( !parse_arg('b', bit_promotion) ) return -1; break;
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
	
	log = multilog_open("leda_dbupdb", 0);
	multilog_add(log, stderr);
	
	if( bit_promotion != 2 ) {
		cerr << "ERROR: Only a bit-promotion factor of 2 is supported" << endl;
		return -1;
	}
	
	if( core >= 0 ) {
		if( dada_bind_thread_to_core(core) < 0 ) {
			cerr << "WARNING: Failed to bind to core " << core << endl;
		}
		if( verbose >= 1 ) {
			cout << "Process bound to core " << core << endl;
		}
	}
	
	dbupdb512 ctx(log, verbose, nthreads);
	ctx.connect(in_key, out_key);
	ctx.run();
	ctx.disconnect();
	
	return 0;
}
