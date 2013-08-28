
/*
  By Ben Barsdell (2013)
  
  A simple one-beam CPU beamformer.
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

#include "aaplus/AA+.h" // Astronomical Algorithms C++ library (for coord conversions)

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

struct char2 {
	char x, y;
};

struct float2 {
	float x, y;
	float2() : x(), y() {}
	float2(float x_, float y_) : x(x_), y(y_) {}
};
struct float3 {
	float x, y, z;
	float3() : x(), y(), z() {}
	float3(float x_, float y_, float z_) : x(x_), y(y_), z(z_) {}
};
/*
struct float4 {
	float x, y, z, w;
	float4() : x(), y(), z(), w() {}
	float4(float x_, float y_, float z_, float w_) : x(x_), y(y_), z(z_), w(w_) {}
};
*/
inline float dot(float3 a, float3 b) {
	return a.x*b.x + a.y*b.y + a.z*b.z;
}

double get_Julian_day(long year, long month, double day,
                      double hour, double minute, double second) {
	return CAADate(year, month, day, hour, minute, second, true).Julian();
}
float3 get_pointing(double ra, double dec, double lat, double lon, double jd) {
	// Convert ra/dec --> alt/az
	// If only this library used namespaces instead of classes :/
	//using CAASidereal::ApparentGreenwichSiderealTime;
	//using CAACoordinateTransformation::DegreesToHours;
	//using CAACoordinateTransformation::Equatorial2Horizontal;
	//using CAACoordinateTransformation::DegreesToRadians;
	double  GST   = CAASidereal::ApparentGreenwichSiderealTime(jd);
	double  lon_h = CAACoordinateTransformation::DegreesToHours(lon);
	double  LHA   = GST - lon_h - ra;
	CAA2DCoordinate horiz = CAACoordinateTransformation::Equatorial2Horizontal(LHA, dec, lat);
	double  az    = horiz.X;
	double  alt   = horiz.Y;
	
	// Convert to Cartesian direction vector
	float3 pointing;
	double az_rad  = CAACoordinateTransformation::DegreesToRadians(az);
	double alt_rad = CAACoordinateTransformation::DegreesToRadians(alt);
	pointing.x = cos(alt_rad) * sin(az_rad);
	pointing.y = cos(alt_rad) * cos(az_rad);
	pointing.z = sin(alt_rad);
	
	return pointing;
}

class dbbeam : public dada_db2db {
	typedef char2  intype;
	typedef float2 outtype;
	
	double m_lat, m_lon;
	int    m_mode;
	float  m_max_aperture;
	bool   m_maintain_circular_aperture;
	size_t m_ntime, m_nchan, m_nstation, m_npol;
	size_t m_sample_offset;
	float3 m_pointing0, m_pointing90;
	float  m_lowfreq, m_df, m_dt;
	
	std::vector<float3> m_stations_xyz;
	float m_delay_lowfreq, m_delay_highfreq;
	std::vector<float>  m_station_delays_low;
	std::vector<float>  m_station_delays_high;
	
	std::vector<outtype> m_data_out;
	std::ostream*        m_outstream;
	
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
		
		// Note: Datestamp format is "2013-06-16-03:46:53"
		char utc_start_str[32];
		ret = ascii_header_get(header_in, "UTC_START", "%s", utc_start_str);
		if( ret < 0 ) {
			throw std::runtime_error("Missing header entry UTC_START");
		}
		int year, month, day, hour, minute;
		float second;
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
		year   = time.tm_year+1900;
		month  = time.tm_mon+1;
		day    = time.tm_mday;
		hour   = time.tm_hour;
		minute = time.tm_min;
		second = time.tm_sec;
		double utc_start_jd = get_Julian_day(year, month, day, hour, minute, second);
		
		char ra_str[32];
		char dec_str[32];
		int sign, deg;
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
		cout << "UTC JD   = " << utc_start_jd << endl;
		cout << "dt       = " << m_dt << endl;
		cout << "ntime    = " << m_ntime << endl;
		cout << "nchan    = " << m_nchan << endl;
		cout << "nstation = " << m_nstation << endl;
		cout << "npol     = " << m_npol << endl;
		cout << "lowfreq  = " << m_lowfreq << endl;
		cout << "df       = " << m_df << endl;
		cout << "ra       = " << ra << endl;
		cout << "dec      = " << dec << endl;
		
		// Compute local direction vectors at start and 1/4 turn later
		m_sample_offset = 0;
		m_pointing0  = get_pointing(ra, dec,
		                            m_lat, m_lon,
		                            utc_start_jd);
		double quarter_turn = 0.25 * 86164.098903691 / 86400;
		m_pointing90 = get_pointing(ra, dec,
		                            m_lat, m_lon,
		                            utc_start_jd + quarter_turn);
		
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
		
		size_t bytes_per_read = m_ntime*m_nchan*m_nstation*m_npol*sizeof(intype);
		cout << "bytes_per_read = " << bytes_per_read << endl;
		return bytes_per_read;
	}
	
	uint64_t beamform_incoherent(const intype* in, outtype* out) {
		enum { NPOL = 2 };
		for( size_t t=0; t<m_ntime; ++t ) {
			for( size_t c=0; c<m_nchan; ++c ) {
				float stokes_I = 0.f;
				float stokes_V = 0.f;
				for( size_t sb=0; sb<m_nstation; sb+=16 ) {
					for( size_t si=0; si<16; ++si ) { // Unroll by 16x
						size_t s = sb + si;
						intype sample_int;
						size_t idx = NPOL*(s + m_nstation*(c + m_nchan*t));
						
						sample_int = in[idx+0];
						float2 pola(sample_int.x, sample_int.y);
						sample_int = in[idx+1];
						float2 polb(sample_int.x, sample_int.y);
						
						stokes_I += pola.x*pola.x;
						stokes_I += pola.y*pola.y;
						stokes_I += polb.x*polb.x;
						stokes_I += polb.y*polb.y;
						
						stokes_V -= pola.y*polb.x;
						stokes_V += pola.x*polb.y;
					}
				}
				size_t out_idx = c + m_nchan*t;
				// Normalise
				stokes_I *= 1.f / m_nstation;
				stokes_V *= 2.f / m_nstation;
				out[out_idx] = float2(stokes_I, stokes_V);
			}
		}
		// TODO: This is only half as much data as in the coherent implementation
		size_t bytes_written = m_ntime*m_nchan*sizeof(outtype);
		return bytes_written;
	}
	
	uint64_t beamform_coherent(const intype* in, outtype* out) {
		float max_dist     = m_max_aperture/2;
		float max_dist_sqr = max_dist*max_dist;
		
		// Earth's rotation rate relative to fixed stars
		const float radians_per_sec = 2*3.1415926535897932 / 86164.098903691;
		
		for( size_t t=0; t<m_ntime; ++t ) {
			float time_offset = (m_sample_offset + t) * m_dt;
			
			// Interpolate pointing through time across the sky
			float  theta = time_offset * radians_per_sec;
			float  cos_theta = cos(theta);
			float  sin_theta = sin(theta);
			float3 p;
			p.x = m_pointing0.x*cos_theta + m_pointing90.x*sin_theta;
			p.y = m_pointing0.y*cos_theta + m_pointing90.y*sin_theta;
			p.z = m_pointing0.z*cos_theta + m_pointing90.z*sin_theta;
			
			for( size_t c=0; c<m_nchan; ++c ) {
				float freq_mhz = m_lowfreq + c*m_df;
				float ff = (freq_mhz-m_delay_lowfreq)/(m_delay_highfreq-m_delay_lowfreq);
				
				float2 pol_sums[2]    = {float2(0,0), float2(0,0)};
				float  pol_weights[2] = {0, 0};
				
				//// HACK TESTING reduced nstations for increased speed
				for( size_t s=0; s</*4*/m_nstation; ++s ) {
					float3 xyz        = m_stations_xyz[s];
					float  path_diff  = dot(xyz, p);
					// Note: Assumes free-space propagation
					float  path_turns = path_diff / 299792458 * freq_mhz*1e6f;
					
					float3 aperture_xyz;
					if( m_maintain_circular_aperture ) {
						float3 projected_xyz;
						projected_xyz.x = xyz.x - p.x*path_diff;
						projected_xyz.y = xyz.y - p.y*path_diff;
						projected_xyz.z = xyz.z - p.z*path_diff;
						aperture_xyz = projected_xyz;
					}
					else {
						aperture_xyz = xyz;
					}
					// Note: Assumes array coords are centered on the origin
					float dist_sqr = dot(aperture_xyz, aperture_xyz);
					// Note: We simply crop stations that are outside the aperture
					float aperture_weight = dist_sqr <= max_dist_sqr;
					
					for( size_t p=0; p<m_npol; ++p ) {
						float  delay_low   = m_station_delays_low[s*m_npol+p];
						float  delay_high  = m_station_delays_high[s*m_npol+p];
						float  delay_ns    = (1-ff) * delay_low + ff * delay_high;
						float  delay_turns = delay_ns*1e-9f * freq_mhz*1e6f;
						
						float  turns = delay_turns + path_turns;
						float  radians = -2 * 3.1415926535897932f * turns;
						float2 weight(cosf(radians), sinf(radians));
						weight.x *= aperture_weight;
						weight.y *= aperture_weight;
						
						size_t idx = p + m_npol*(s + m_nstation*(c + m_nchan*t));
						intype sample_int = in[idx];
						float2 sample(sample_int.x, sample_int.y);
						// Complex multiply and accumulate
						pol_sums[p].x += weight.x * sample.x;
						pol_sums[p].x -= weight.y * sample.y;
						pol_sums[p].y += weight.y * sample.x;
						pol_sums[p].y += weight.x * sample.y;
						
						pol_weights[p] += aperture_weight;
					}
				}
				for( size_t p=0; p<m_npol; ++p ) {
					size_t out_idx = p + m_npol*(c + m_nchan*t);
					pol_sums[p].x /= pol_weights[p];
					pol_sums[p].y /= pol_weights[p];
					out[out_idx] = pol_sums[p];
				}
			}
		}
		
		m_sample_offset += m_ntime;
		
		size_t bytes_written = m_ntime*m_nchan*m_npol*sizeof(outtype);
		return bytes_written;
	}
	
	// Return no. bytes written
	virtual uint64_t onData(uint64_t    in_size,
	                        const char* data_in,
	                        char*       data_out) {
		const intype* in  = (const intype*)data_in;
		outtype*      out =      (outtype*)data_out;
		
		switch( m_mode ) {
		case BF_MODE_INCOHERENT: return beamform_incoherent(in, out);
		case BF_MODE_COHERENT:   return beamform_coherent(in, out);
		default: throw std::runtime_error("Invalid beamforming mode");
		}
	}
	
public:
	enum { BF_MODE_INCOHERENT, BF_MODE_COHERENT };
	
	dbbeam(multilog_t* log, int verbose,
	       double lat, double lon,
	       int mode=BF_MODE_COHERENT,
	       float max_aperture=1e99, bool maintain_circular_aperture=false)
		: dada_db2db(log, verbose),
		  m_lat(lat), m_lon(lon),
		  m_mode(mode),
		  m_max_aperture(max_aperture),
		  m_maintain_circular_aperture(maintain_circular_aperture) {}
	virtual ~dbbeam() {}
	
	// Note: Expects pols interleaved in delay arrays
	// TODO: Allow per-pol amplitude weights
	void set_stations(size_t        nstation,
	                  size_t        npol,
	                  const float3* xyz_m,
	                  float         lowfreq,
	                  const float*  delays_low_ns,
	                  float         highfreq,
	                  const float*  delays_high_ns) {
		size_t ninput = nstation * npol;
		m_stations_xyz.assign(xyz_m, xyz_m + ninput);
		m_delay_lowfreq = lowfreq;
		m_station_delays_low.assign(delays_low_ns, delays_low_ns + ninput);
		m_delay_highfreq = highfreq;
		m_station_delays_high.assign(delays_high_ns, delays_high_ns + ninput);
	}
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

void print_usage() {
	cout << 
		"dbbeam [options] -- lat lon in_key out_key\n"
		" lat/lon      Observatory latitude and longitude as decimals\n"
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
	while( (arg = getopt(argc,argv,"s:ia:bc:hvq")) != -1 ) {
		switch( arg ) {
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
		cout << "Latitude   = " << lat << endl;
		cout << "Longitude  = " << lon << endl;
		cout << "In key     = " << std::hex << in_key << std::dec << endl;
		cout << "Out key    = " << std::hex << out_key << std::dec << endl;
		cout << "Incoherent = " << (incoherent ? "yes" : "no") << endl;
	}
	
	log = multilog_open("dbbeam", 0);
	multilog_add(log, stderr);
	
	if( verbose >= 1 ) {
		cout << "Loading station data from " << standfile << endl;
	}
	std::vector<float3> stands_xyz;
	float               lowfreq;
	std::vector<float>  delays_low;
	float               highfreq;
	std::vector<float>  delays_high;
	// TODO: This assumes 2 pols and units of metres and ns
	int ret = load_stands(standfile, stands_xyz, delays_low, delays_high);
	if( ret < 0 ) {
		return ret;
	}
	// TODO: These should be read from somewhere
	lowfreq  = 10;
	highfreq = 80;
	if( verbose >= 1 ) {
		cout << "  Done" << endl;
	}
	
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
	
	dbbeam ctx(log, verbose, lat, lon, mode, max_aperture, circular);
	if( verbose >= 1 ) {
		cout << "Initialising from station data" << endl;
	}
	ctx.set_stations(stands_xyz.size(), 2,
	                 &stands_xyz[0],
	                 lowfreq,
	                 &delays_low[0],
	                 highfreq,
	                 &delays_high[0]);
	if( verbose >= 1 ) {
		cout << "  Done" << endl;
	}
	ctx.connect(in_key, out_key);
	ctx.run();
	ctx.disconnect();
	
	return 0;
}
