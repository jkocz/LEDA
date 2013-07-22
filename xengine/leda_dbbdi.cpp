
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
#include <algorithm>
#include <numeric>

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

struct float2 {
	float x, y;
	float2() : x(), y() {}
	float2(float x_, float y_) : x(x_), y(y_) {}
};

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

inline unsigned int first_set_bit(unsigned int x) {
	// Note: This will return (uint)-1 if x==0
	return __builtin_ffs(x) - 1;
}

class dbbdi : public dada_db2db {
	enum {
		NPOL = 2,
		REG_ROWS = 2,
		REG_COLS = 2
	};
	
	typedef float  real_t;
	typedef float2 complex_t;
	typedef std::vector<std::vector<size_t> > dump_maps_t;
	typedef std::vector<complex_t>            complex_array_t;
	
	size_t          m_nchan;
	size_t          m_nstation;
	size_t          m_nbaseline;
	size_t          m_nbaseline_rtt;
	float           m_corr_dump_time;
	size_t          m_min_corr_dumps;
	size_t          m_corr_dump;
	complex_array_t m_sumbuf;
	dump_maps_t     m_dump_maps;
	size_t          m_interval;
	
	size_t get_nbaseline(size_t nstation) {
		return nstation*(nstation+1)/2;
	}
	size_t get_reg_tile_triangular_nbaseline(size_t nstation) {
		return (nstation/REG_ROWS)*(nstation/REG_COLS+1)/2*REG_ROWS*REG_COLS;
	}
	void compute_dump_maps(const float* baseline_times, float corr_dump_time) {
		float  mintime = *std::min_element(baseline_times,
		                                   baseline_times + m_nbaseline);
		float  maxtime = *std::max_element(baseline_times,
		                                   baseline_times + m_nbaseline);
		m_min_corr_dumps = size_t(mintime / corr_dump_time);
		size_t maxdump = intlog2((uint)(maxtime / mintime));
		//cout << "ndumps = " << maxdump+1 << endl;
		m_dump_maps.resize(maxdump+1);
		for( size_t b=0; b<m_nbaseline; ++b ) {
			float  time = baseline_times[b];
			size_t dump = intlog2((uint)(time / mintime));
			//cout << "dump = " << dump << endl;
			//cout << "m_dump_maps[dump].size() = " << m_dump_maps[dump].size() << endl;
			m_dump_maps[dump].push_back(b);
		}
	}
protected:
	virtual void     onConnect(key_t in_key, key_t out_key) {}
	virtual void     onDisconnect() {}
	// Return desired no. bytes per data read
	virtual uint64_t onHeader(uint64_t    header_size,
	                          const char* header_in,
	                          char*       header_out) {
		// Copy the in header to the out header
		memcpy(header_out, header_in, header_size);
		
		int ret;
		ret = ascii_header_get(header_in, "NCHAN", "%lu", &m_nchan);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry NCHAN"); }
		size_t nstation;
		ret = ascii_header_get(header_in, "NSTATION", "%lu", &nstation);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry NSTATION"); }
		if( nstation*(nstation+1)/2 != m_nbaseline ) {
			throw std::runtime_error("NSTATION in data header does not match configured value");
		}
		size_t npol;
		ret = ascii_header_get(header_in, "NPOL", "%lu", &npol);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry NPOL"); }
		if( npol != NPOL ) {
			throw std::runtime_error("NPOL in data header does not match compiled value");
		}
		
		// TODO: Change DATA_ORDER param in header to TRIANGULAR
		
		m_sumbuf.resize(0);
		m_sumbuf.resize(m_nchan*m_nbaseline*NPOL*NPOL, complex_t(0,0));
		
		m_corr_dump = 0;
		m_interval = 0;
		
		return m_nchan * m_nbaseline_rtt * NPOL*NPOL * sizeof(complex_t);
	}
	// Return no. bytes written
	virtual uint64_t onData(uint64_t    in_size,
	                        const char* data_in,
	                        char*       data_out) {
		const real_t* in = (real_t*)data_in;
		
		// TODO: Make the output order [nchan][nstation*(nstation+1)/2][npol][npol][ndim][32b]
		//         I.e., reduntantly include the auto yx cross-pol terms and have pol*pol fastest
		
		// Convert from REG_TILE_TRIANGULAR to plain triangular and accumulate
		size_t reg_tile_nbaseline = get_nbaseline(m_nstation/REG_COLS);
		size_t matlen_rtt = m_nchan * m_nbaseline_rtt * NPOL*NPOL;
		for( size_t c=0; c<m_nchan; ++c ) {
			for( size_t i=0; i<m_nstation/REG_COLS; ++i ) {
				for( size_t rcol=0; rcol<REG_COLS; ++rcol ) {
					for( size_t j=0; j<=i; ++j ) {
						for( size_t rrow=0; rrow<REG_ROWS; ++rrow ) {
							size_t k = ( c * m_nbaseline +
							             get_nbaseline(REG_COLS*i+rcol) +
							             REG_ROWS*j+rrow );
							size_t l = ( (c*REG_ROWS*REG_COLS +
							              REG_ROWS*rrow+rcol) * reg_tile_nbaseline +
							             get_nbaseline(i) + j);
							for( size_t polb=0; polb<NPOL; ++polb ) {
								for( size_t pola=0; pola<NPOL; ++pola ) {
									size_t reg_idx = pola + NPOL*(polb + NPOL*l);
									size_t tri_idx = pola + NPOL*(polb + NPOL*k);
									
									complex_t val(in[reg_idx],
									              in[reg_idx + matlen_rtt]);
									m_sumbuf[tri_idx].x += val.x;
									m_sumbuf[tri_idx].y += val.y;
								}
							}
						}
					}
				}
			}
		}
		/*
		// TODO: Perhaps try to avoid explicit equations involving %'s
		for( size_t c=0; c<m_nchan; ++c ) {
			// Note: real and *2 because rtt format separates real and imag
			real_t*    matrix_rtt = &in[c * m_nbaseline_rtt*NPOL*NPOL*2];
			complex_t* matrix     = &m_sumbuf[c * m_nbaseline*NPOL*NPOL];
			
			for( size_t m=0; m<m_nbaseline_rtt; ++m ) {
				uint row, col;
				get_reg_tile_triangular_coords(m, row, col);
				
				size_t mat_idx = col + row*(row+1)/2;
				
				real_t real = matrix_rtt[m + 0*m_nbaseline_rtt*NPOL*NPOL];
				real_t imag = matrix_rtt[m + 1*m_nbaseline_rtt*NPOL*NPOL];
				matrix[mat_idx] 
			}
		}
		*/
		
		// 1 2 3 4 5 6 7 8
		// 0 1 0 2 0 1 0 3
		// __builtin_ffs-1
		
		m_corr_dump += 1;
		if( m_corr_dump < m_min_corr_dumps ) {
			return 0;
		}
		m_corr_dump = 0;
		m_interval += 1;
		//size_t dump = intlog2((uint)m_interval);
		size_t dump = first_set_bit(m_interval);
		if( dump == m_dump_maps.size()-1 ) {
			// This is the longest dump, so reset the interval for next time
			m_interval = 0;
		}
		
		size_t ndumped = 0;
		for( size_t d=0; d<=dump; ++d ) {
			ndumped += m_dump_maps[d].size();
		}
		
		complex_t* out = (complex_t*)data_out;
		
		for( size_t c=0; c<m_nchan; ++c ) {
			complex_t* matrix = &m_sumbuf[c * m_nbaseline*NPOL*NPOL];
			
			// Go through all baselines to be dumped
			size_t j = 0;
			for( size_t d=0; d<=dump; ++d ) {
				for( size_t i=0; i<m_dump_maps[d].size(); ++i ) {
					size_t baseline = m_dump_maps[d][i];
					
					for( size_t pb=0; pb<NPOL; ++pb ) {
						for( size_t pa=0; pa<NPOL; ++pa ) {
							size_t in_idx  = pa + NPOL*(pb + NPOL*baseline);
							size_t out_idx = pa + NPOL*(pb + NPOL*j);
							
							// Extract the accumulation, then reset it
							complex_t& accum = matrix[in_idx];
							out[out_idx] = accum;
							accum = complex_t(0,0);
						}
					}
					++j;
				}
			}
		}
		
		size_t bytes_written = ndumped * m_nchan * sizeof(complex_t);
		return bytes_written;
	}
public:
	dbbdi(multilog_t* log, int verbose)
		: dada_db2db(log, verbose) {}
	virtual ~dbbdi() {}
	
	// TODO: Can re-do this method allowing proper times to be passed in, which are
	//         then adapted using the TSAMP parameter?
	
	void setMaxBaselineDumpTimes(size_t nstation, const float* times,
	                             float correlator_dump_time) {
		m_nstation       = nstation;
		m_nbaseline      = get_nbaseline(nstation);
		m_nbaseline_rtt  = get_reg_tile_triangular_nbaseline(nstation);
		m_corr_dump_time = correlator_dump_time;
		compute_dump_maps(times, correlator_dump_time);
	}
	size_t getNDumpTimes()          const { return m_dump_maps.size(); }
	float  getDumpTime(size_t dump) const {
		return (1<<dump) * m_min_corr_dumps * m_corr_dump_time;
	}
	const std::vector<size_t>& getDumpBaselines(size_t dump) const {
		return m_dump_maps[dump];
	}
	
	void generateBaselineDumpTimes() {
		
	}
	
	// Need to know for each dump: integration time, list of baselines
	
	/*
	// Note: Input is the number of raw correlator sums for each baseline in
	//         the triangular Nst*(Nst+1)/2 element matrix. Values must be >= 1.
	void setBaselineDumpIntervals(size_t nstation, size_t base_interval,
	                              const float* intervals) {
		typedef unsigned int uint;
		m_nstation      = nstation;
		m_nbaseline     = nstation*(nstation+1)/2;
		m_nbaseline_rtt = get_reg_tile_triangular_nbaseline(nstation);
		float  mininterval = *std::min_element(intervals,
		                                       intervals + m_nbaseline);
		float  maxinterval = *std::max_element(intervals,
		                                       intervals + m_nbaseline);
		size_t mindump     = intlog2((uint)mininterval);
		m_maxdump          = intlog2((uint)maxinterval);
		uint   ndumps      = m_maxdump+1 - mindump;
		m_base_interval = base_interval * (1<<mindump);
		
		m_dump_maps.resize(ndumps);
		for( size_t b=0; b<m_nbaseline; ++b ) {
			float interval = intervals[b];
			// Note: We round down to guarantee required integration times
			uint dump = intlog2((uint)interval) - mindump;
			m_dump_maps[dump].push_back(b);
		}
		
		for( size_t d=0; d<ndumps; ++d ) {
			std::copy(m_dump_maps[d].begin(), m_dump_maps[d].end(),
			          std::ostream_iterator<float>(cout, " "));
			cout << endl;
		}
	}
	*/
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
		"dbbdi [options] in_key out_key\n"
		" -s standfile Stand data file to use [stands.txt]\n"
		" -c core      Bind process to CPU core\n"
		" -D filename  Write dump info to filename and exit\n"
		" -v           Increase verbosity\n"
		" -q           Decrease verbosity\n"
		" -h           Print usage\n" << endl;
}

int main(int argc, char* argv[])
{
	// TODO: Consider reading this (also low/highfreq) from an env var
	std::string standfile    = "stands.txt";
	std::string dumpinfofile = "";
	int         core         = -1;
	int         verbose      = 0;
	key_t       in_key       = 0;
	key_t       out_key      = 0;
	multilog_t* log          = 0;
	
	int arg = 0;
	while( (arg = getopt(argc,argv,"s:c:D:hvq")) != -1 ) {
		switch( arg ) {
		case 's': if( !parse_arg('s', standfile) ) { return -1; } break;
		case 'c': if( !parse_arg('c', core) ) { return -1; } break;
		case 'D': if( !parse_arg('D', dumpinfofile) ) { return -1; } break;
		case 'h': print_usage(); return 0;
		case 'v': ++verbose; break;
		case 'q': --verbose; break;
		default: cerr << "WARNING: Unexpected flag -" << arg << endl; break;
		}
	}
	
	log = multilog_open("dbbdi", 0);
	multilog_add(log, stderr);
	
	if( verbose >= 1 ) {
		cout << "Loading station data from " << standfile << endl;
	}
	/*
	std::vector<float2> stands_xy;
	int ret = load_stands(standfile, stands_xy);
	if( ret < 0 ) {
		return ret;
	}
	if( verbose >= 1 ) {
		cout << "  Done" << endl;
	}
	*/
	if( core >= 0 ) {
		if( dada_bind_thread_to_core(core) < 0 ) {
			cerr << "WARNING: Failed to bind to core " << core << endl;
		}
		if( verbose >= 1 ) {
			cout << "Process bound to core " << core << endl;
		}
	}
	
	dbbdi ctx(log, verbose);
	
	// HACK TESTING
	size_t nstation  = 16;
	size_t nbaseline = nstation*(nstation+1)/2;
	std::vector<float> times(nbaseline);
	for( size_t b=0; b<nbaseline; ++b ) {
		times[b] = b + 100;
	}
	float corr_dump_time = 8.533333;
	ctx.setMaxBaselineDumpTimes(nstation, &times[0], corr_dump_time);
	
	if( dumpinfofile != "" ) {
		// Write dump info to specified file
		std::ofstream dumpfile(dumpinfofile.c_str());
		if( !dumpfile ) {
			cerr << "ERROR: Failed to open " << dumpfile << endl;
			return -2;
		}
		dumpfile << "# Note: LDP == log2 of the dump period in units of the min dump time" << endl;
		dumpfile << "# Note: LDP(i'th dump) == lowest_set_bit(i)" << endl;
		dumpfile << "#LDP\ttime\tbaseline" << endl;
		size_t ndumps = ctx.getNDumpTimes();
		for( size_t dump=0; dump<ndumps; ++dump ) {
			float dumptime = ctx.getDumpTime(dump);
			const std::vector<size_t>& baselines = ctx.getDumpBaselines(dump);
			for( size_t b=0; b<baselines.size(); ++b ) {
				size_t baseline = baselines[b];
				dumpfile << dump << "\t"
				         << dumptime << "\t"
				         << baseline << endl;
			}
		}
		dumpfile.close();
		cout << "Dump info written to " << dumpinfofile << endl;
		return 0;
	}
	
	// Note: We do this down here to allow key-less -D flag
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
	
	/*
	if( verbose >= 1 ) {
		cout << "Initialising from station data" << endl;
	}
	
	if( verbose >= 1 ) {
		cout << "  Done" << endl;
	}
	*/
	ctx.connect(in_key, out_key);
	ctx.run();
	ctx.disconnect();
	
	return 0;
}
