
/*
  By Ben Barsdell (2013)
  
  A simple GPU incoherent sum implementation.
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
#include <dada_cuda.h>

#include <thrust/device_vector.h>
#include <thrust/iterator/transform_iterator.h>
#include <thrust/iterator/counting_iterator.h>
#include <thrust/iterator/discard_iterator.h>
#include <thrust/reduce.h>

//#include "aaplus/AA+.h" // Astronomical Algorithms C++ library (for coord conversions)

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

template <typename T>
int sgn(T val) {
    return (T(0) < val) - (val < T(0));
}

inline __host__ __device__
float2 operator+(float2 a, float2 b) {
	return make_float2(a.x+b.x, a.y+b.y);
}

struct raw2stokesIV : public thrust::unary_function<char4,float2> {
	inline __host__ __device__
	float2 operator()(char4 val) const {
		float stokes_I = 0.f;
		stokes_I += val.x*val.x;
		stokes_I += val.y*val.y;
		stokes_I += val.z*val.z;
		stokes_I += val.w*val.w;
		
		float stokes_V = 0.f;
		stokes_V -= val.y*val.z;
		stokes_V += val.x*val.w;
		
		return make_float2(stokes_I, stokes_V);
	}
};

struct raw2XXYY : public thrust::unary_function<char4,float2> {
	inline __host__ __device__
	float2 operator()(char4 val) const {
		float xx = 0.f;
		xx += val.x*val.x;
		xx += val.y*val.y;
		float yy = 0.f;
		yy += val.z*val.z;
		yy += val.w*val.w;
		
		return make_float2(xx, yy);
	}
};

template<typename T>
struct divide_by : public thrust::unary_function<T,T> {
	T divisor;
	divide_by(T d) : divisor(d) {}
	inline __host__ __device__
	T operator()(T x) const {
		return x / divisor;
	}
};

class dbbeam : public dada_db2db {
	typedef char4  intype;
	typedef float2 outtype;
	
	int    m_gpu_device;
	double m_lat, m_lon;
	int    m_mode;
	float  m_max_aperture;
	bool   m_maintain_circular_aperture;
	size_t m_ntime, m_nchan, m_nstation, m_npol;
	size_t m_sample_offset;
	float3 m_pointing0, m_pointing90;
	float  m_lowfreq, m_df, m_dt;
	
	thrust::device_vector<intype>  m_d_in;
	thrust::device_vector<outtype> m_d_out;
	
protected:
	virtual void     onConnect(key_t in_key, key_t out_key) {
		// Register buffers as pinned memory
		dada_cuda_select_device(m_gpu_device);
		logInfo("dbbeam_gpu: Registering input buffer");
		dada_cuda_dbregister(this->hdu_in());
		logInfo("dbbeam_gpu: Registering output buffer");
		dada_cuda_dbregister(this->hdu_out());
	}
	virtual void     onDisconnect() {}
	// Return desired no. bytes per data read
	virtual uint64_t onHeader(uint64_t    header_size,
	                          const char* header_in,
	                          char*       header_out) {
		// Copy the in header to the out header
		memcpy(header_out, header_in, header_size);
		
		int ret;
		
		// Note: Datestamp format is "2013-06-16-03:46:53"
		char utc_start_str[32];
		ret = ascii_header_get(header_in, "UTC_START", "%s", utc_start_str);
		if( ret < 0 ) {
			throw std::runtime_error("Missing header entry UTC_START");
		}
		//int year, month, day, hour, minute;
		//float second;
		/*
		  ret = sscanf(utc_start_str, "%i-%02i-%02i-%02i:%02i:%f",
		  &year, &month, &day, &hour, &minute, &second);
		  if( ret != 6 ) {
		  cerr << "UTC_START = " << utc_start_str << endl;
		  throw std::runtime_error("Could not parse UTC_START");
		  }
		*/
		tm time;
		if( !strptime(utc_start_str, "%Y-%m-%d-%H:%M:%S", &time) ) {
			cerr << "UTC_START = " << utc_start_str << endl;
			throw std::runtime_error("Failed to parse UTC_START");
		}
		/*
		year   = time.tm_year+1900;
		month  = time.tm_mon+1;
		day    = time.tm_mday;
		hour   = time.tm_hour;
		minute = time.tm_min;
		second = time.tm_sec;
		double utc_start_jd = get_Julian_day(year, month, day, hour, minute, second);
		*/
		char ra_str[32];
		char dec_str[32];
		int  sign, deg;
		int   hour, minute;
		float second;
		ret = ascii_header_get(header_in, "RA", "%s", ra_str);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry RA"); }
		ret = sscanf(ra_str, "%i:%i:%f", &hour, &minute, &second);
		if( ret != 3 ) {
			cerr << "RA = " << ra_str << endl;
			throw std::runtime_error("Could not parse RA");
		}
		double ra = (second + 60*(minute + 60*hour)) * 360 / (24*60*60);
		
		ret = ascii_header_get(header_in, "DEC", "%s", dec_str);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry DEC"); }
		ret = sscanf(dec_str, "%i:%i:%f", &deg, &minute, &second);
		if( ret != 3 ) {
			cerr << "DEC = " << dec_str << endl;
			throw std::runtime_error("Could not parse DEC");
		}
		sign  = sgn(deg);
		deg   = abs(deg);
		double dec = sign * (second + 60*(minute + 60*deg)) / (60*60);
		
		ret = ascii_header_get(header_in, "TSAMP", "%f", &m_dt);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry TSAMP"); }
		m_dt *= 1e-6; // TSAMP is in units of us, we want seconds
		ret = ascii_header_get(header_in, "NCHAN", "%lu", &m_nchan);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry NCHAN"); }
		ret = ascii_header_get(header_in, "NSTATION", "%lu", &m_nstation);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry NSTATION"); }
		ret = ascii_header_get(header_in, "NPOL", "%lu", &m_npol);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry NPOL"); }
		ret = ascii_header_get(header_in, "LOWFREQ", "%f", &m_lowfreq);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry LOWFREQ"); }
		ret = ascii_header_get(header_in, "CHAN_WIDTH", "%f", &m_df);
		if( ret < 0 ) { throw std::runtime_error("Missing/invalid header entry CHAN_WIDTH"); }
		
		m_ntime = this->bufsize_out() / (m_nchan*m_npol*sizeof(outtype));
		
		cout << "UTC      = " << utc_start_str << endl;
		//cout << "UTC JD   = " << utc_start_jd << endl;
		cout << "dt       = " << m_dt << endl;
		cout << "ntime    = " << m_ntime << endl;
		cout << "nchan    = " << m_nchan << endl;
		cout << "nstation = " << m_nstation << endl;
		cout << "npol     = " << m_npol << endl;
		cout << "lowfreq  = " << m_lowfreq << endl;
		cout << "df       = " << m_df << endl;
		cout << "ra       = " << ra << endl;
		cout << "dec      = " << dec << endl;
		
		// Update (some) parameter(s) in the header
		uint64_t outsize      = this->bufsize_out();//m_ntime*m_nchan*m_npol*sizeof(outtype);
		uint64_t max_filesize = 2ull*1024*1024*1024;
		uint64_t bytes_per_second = (max_filesize-header_size) / (outsize * 10) * outsize;
		if( ascii_header_set(header_out, "NBIT", "%d", 32) < 0 ) {
			logInfo("dbbeam: Failed to set NBIT 32 in header_out");
		}
		if( ascii_header_set(header_out, "BYTES_PER_SECOND", "%i", bytes_per_second) < 0 ) {
			logInfo("dbbeam: Failed to set BYTES_PER_SECOND in header_out");
		}
		if( ascii_header_set(header_out, "DATA_ORDER", "%s", "time_chan_pol_cpx_f32") < 0 ) {
			logInfo("dbbeam: Failed to set DATA_ORDER in header_out");
		}
		if( ascii_header_set(header_out, "SOURCE", "%s", "TARGET") < 0 ) {
			logInfo("dbbeam: Failed to set SOURCE in header_out");
		}
		if( ascii_header_set(header_out, "MODE", "%s", "SINGLE_BEAM") < 0 ) {
			logInfo("dbbeam: Failed to set MODE in header_out");
		}
		
		m_d_in.reserve(m_ntime*m_nchan*m_nstation);
		m_d_out.resize(m_ntime*m_nchan);
		
		size_t bytes_per_read = m_ntime*m_nchan*m_nstation*sizeof(intype);
		cout << "bytes_per_read = " << bytes_per_read << endl;
		return bytes_per_read;
	}
	
	uint64_t beamform_incoherent(const intype*  __restrict__ in,
	                             outtype* __restrict__ out) {
		size_t count = m_ntime*m_nchan*m_nstation;
		m_d_in.assign(in, in + count);
		
		using thrust::make_transform_iterator;
		using thrust::make_counting_iterator;
		using thrust::make_discard_iterator;
		
		thrust::reduce_by_key(make_transform_iterator(make_counting_iterator<uint>(0),
		                                              divide_by<uint>(m_nstation)),
		                      make_transform_iterator(make_counting_iterator<uint>(0),
		                                              divide_by<uint>(m_nstation))+count,
		                      make_transform_iterator(m_d_in.begin(),
		                                              //raw2stokesIV()),
		                                              raw2XXYY()),
		                      make_discard_iterator(),
		                      m_d_out.begin());
		
		thrust::copy(m_d_out.begin(), m_d_out.end(),
		             out);
		
		// TODO: This is only half as much data as in the coherent implementation
		size_t bytes_written = m_ntime*m_nchan*sizeof(outtype);
		return bytes_written;
	}
	
	// Return no. bytes written
	virtual uint64_t onData(uint64_t    in_size,
	                        const char* data_in,
	                        char*       data_out) {
		const intype* __restrict__ in  = (const intype*)data_in;
		outtype*      __restrict__ out =      (outtype*)data_out;
		
		switch( m_mode ) {
		case BF_MODE_INCOHERENT: return beamform_incoherent(in, out);
		//case BF_MODE_COHERENT:   return beamform_coherent(in, out);
		default: throw std::runtime_error("Invalid beamforming mode");
		}
	}
	
public:
	enum { BF_MODE_INCOHERENT, BF_MODE_COHERENT };
	
	dbbeam(multilog_t* log, int verbose, int gpu_device,
	       double lat, double lon,
	       int mode=BF_MODE_COHERENT,
	       float max_aperture=1e99, bool maintain_circular_aperture=false)
		: dada_db2db(log, verbose),
		  m_gpu_device(gpu_device),
		  m_lat(lat), m_lon(lon),
		  m_mode(mode),
		  m_max_aperture(max_aperture),
		  m_maintain_circular_aperture(maintain_circular_aperture) {
		
		// Give the CPU a rest while the GPU kernel is running
		cudaSetDeviceFlags(cudaDeviceScheduleYield);
		
		/*
		cudaError_t error = cudaSetDevice(gpu_device);
		if( error != cudaSuccess ) {
			throw std::runtime_error(cudaGetErrorString(error));
		}
		*/
	}
	virtual ~dbbeam() {}
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
/*
int load_stands(std::string          filename,
                std::vector<float3>& stands_xyz,
                std::vector<float>&  delays_low,
                std::vector<float>&  delays_high) {
	
	// *** TODO: IMPORTANT: Must convert into LEDA correlator order
	
	std::ifstream standstream(filename.c_str());
	if( !standstream ) {
		cerr << "ERROR: Failed to open stands file " << filename << endl;
		return -1;
	}
	while( standstream.good() ) {
		std::string line;
		std::getline(standstream, line);
		if( line.length() == 0 || line[0] == '#' ) {
			continue;
		}
		std::stringstream ss;
		int idx;
		float x, y, z, da_low, da_high, db_low, db_high;
		ss >> idx >> x >> y >> z >> da_low >> da_high >> db_low >> db_high;
		// TODO: This assumes the stands are perfectly ordered in the file
		//         Using std::map is probably the best way to do it properly
		stands_xyz.push_back(float3(x,y,z));
		delays_low.push_back(da_low);
		delays_low.push_back(db_low);
		delays_high.push_back(da_high);
		delays_high.push_back(db_high);
	}
	return 0;
}
*/
void print_usage() {
	cout << 
		"dbbeam [options] -- lat lon in_key out_key\n"
		" lat/lon      Observatory latitude and longitude as decimals\n"
		" -d gpu_idx   Index of GPU to use\n"
		" -s standfile Stand data file to use [stands.txt]\n"
		" -i           Incoherent sum only\n"
		" -a aperture  Max aperture (dist. from centre of array) [1e99]\n"
		" -b           Maintain circular aperture (at cost of area)\n"
		" -c core      Bind process to CPU core\n"
		" -v           Increase verbosity\n"
		" -q           Decrease verbosity\n"
		" -h           Print usage\n" << endl;
}

int main(int argc, char* argv[])
{
	// TODO: Consider reading this (also low/highfreq) from an env var
	int         gpu_idx      = 0;
	std::string standfile    = "stands.txt";
	bool        incoherent   = false;
	float       max_aperture = 1e99;
	int         circular     = 0;
	int         core         = -1;
	int         verbose      = 0;
	float       lat          = 0;
	float       lon          = 0;
	key_t       in_key       = 0;
	key_t       out_key      = 0;
	multilog_t* log          = 0;
	
	int arg = 0;
	while( (arg = getopt(argc,argv,"d:s:ia:bc:hvq")) != -1 ) {
		switch( arg ) {
		case 'd': if( !parse_arg('d', gpu_idx) ) return -1; break;
		case 's': if( !parse_arg('s', standfile) ) return -1; break;
		case 'i': incoherent = true; break;
		case 'a': if( !parse_arg('a', max_aperture) ) return -1; break;
		case 'b': ++circular; break;
		case 'c': if( !parse_arg('c', core) ) return -1; break;
		case 'h': print_usage(); return 0;
		case 'v': ++verbose; break;
		case 'q': --verbose; break;
		default: cerr << "WARNING: Unexpected flag -" << arg << endl; break;
		}
	}
	int num_args = argc - optind;
	if( num_args != 4 ) {
		cerr << "ERROR: Expected exactly 4 required args, got " << num_args << endl;
		print_usage();
		return -1;
	}
	if( sscanf(argv[optind+0], "%f", &lat) != 1 ) {
		cerr << "ERROR: Could not parse latitude from "
		     << argv[optind+0] << endl;
		return -1;
	}
	if( sscanf(argv[optind+1], "%f", &lon) != 1 ) {
		cerr << "ERROR: Could not parse longitude from "
		     << argv[optind+1] << endl;
		return -1;
	}
	unsigned int tmp;
	if( sscanf(argv[optind+2], "%x", &tmp) != 1 ) {
		cerr << "ERROR: Could not parse buffer key from "
		     << argv[optind+2] << endl;
		return -1;
	}
	in_key = tmp;
	if( sscanf(argv[optind+3], "%x", &tmp) != 1 ) {
		cerr << "ERROR: Could not parse buffer key from "
		     << argv[optind+3] << endl;
		return -1;
	}
	out_key = tmp;
	
	if( verbose >= 1 ) {
		cout << "GPU idx    = " << gpu_idx << endl;
		cout << "Latitude   = " << lat << endl;
		cout << "Longitude  = " << lon << endl;
		cout << "In key     = " << std::hex << in_key << std::dec << endl;
		cout << "Out key    = " << std::hex << out_key << std::dec << endl;
		cout << "Incoherent = " << (incoherent ? "yes" : "no") << endl;
	}
	
	log = multilog_open("dbbeam", 0);
	multilog_add(log, stderr);
	
	if( core >= 0 ) {
		if( dada_bind_thread_to_core(core) < 0 ) {
			cerr << "WARNING: Failed to bind to core " << core << endl;
		}
		if( verbose >= 1 ) {
			cout << "Process bound to core " << core << endl;
		}
	}
	
	int mode;
	if( incoherent ) {
		mode = dbbeam::BF_MODE_INCOHERENT;
	}
	else {
		mode = dbbeam::BF_MODE_COHERENT;
	}
	
	dbbeam ctx(log, verbose, gpu_idx, lat, lon, mode, max_aperture, circular);
	ctx.connect(in_key, out_key);
	ctx.run();
	ctx.disconnect();
	
	return 0;
}
