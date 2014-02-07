
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

#include <omp.h>

#include <dada_def.h>
#include <ascii_header.h>

#include "dada_db2db.hpp"

#include "stopwatch.hpp"

 /*
struct __attribute__((aligned(8))) uchar8 {
	unsigned char s0, s1, s2, s3, s4, s5, s6, s7;
};
struct __attribute__((aligned(8))) ushort4 {
	unsigned short x, y, z, w;
};
 */

class dbupdb512 : public dada_db2db {
	// Note: These are specific to the LEDA 512 deployment at OVRO
	enum {
		PROMOTE_FACTOR = 2,
		NCHAN          = 109,
		NTIME_PER_PKT  = 2,
		NGROUP_PER_PKT = 4,
		NROACH         = 16,
		GULP_SIZE = NCHAN*NTIME_PER_PKT*NGROUP_PER_PKT*NROACH
	};
	
	size_t m_buf_idx;
	size_t m_bufs_per_state;
	size_t m_state_idx;
	size_t m_nstates;
	
	int   m_ntime;
	float m_chan_width_mhz;
	
	// Total power attributes
	typedef float tptype;
	std::vector<size_t> m_tp_inputs;
	std::vector<tptype> m_tp_accums;
	std::ofstream       m_tp_outstream;
	std::string         m_tp_outpath;
	float               m_tp_edge_time_s;
	int                 m_tp_sky_state;
	
protected:
	virtual void     onConnect(key_t in_key, key_t out_key) {}
	virtual void     onDisconnect() {}
	// Return desired no. bytes per data read
	virtual uint64_t onHeader(uint64_t    header_size,
	                          const char* header_in,
	                          char*       header_out) {
		// Copy the in header to the out header
		memcpy(header_out, header_in, header_size);
		
		if( ascii_header_get(header_in, "XENGINE_NTIME", "%i", &m_ntime) < 0 ) {
			throw std::runtime_error("Missing header entry XENGINE_NTIME");
		}
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
		int nchan;
		if( ascii_header_get(header_in, "NCHAN", "%i", &nchan) < 0 ) {
			throw std::runtime_error("Missing header entry NCHAN");
		}
		if( nchan != NCHAN ) {
			throw std::runtime_error("NCHAN in header does not match compiled code");
		}
		
		// Create header for total power data
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
		// TODO: This assumes TP averages are 1s
		int tp_navg = (size_t)(1. * m_chan_width_mhz*1e6 + 0.5);
		if( ascii_header_set(&tp_header[0], "NAVG", "%d", tp_navg) < 0 ) {
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
		size_t tpsize = NCHAN * tp_ninputs * m_nstates;
		m_tp_accums.resize(tpsize, 0);
		std::fill(m_tp_accums.begin(), m_tp_accums.end(), 0);
		
		//size_t bytes_per_read = ntime * nchan * nstation * npol * sizeof(unsigned char);
		size_t bytes_per_read = this->bufsize_in();
		return bytes_per_read;
	}
	// Return no. bytes written
	virtual uint64_t onData(uint64_t    in_size,
	                        const char* __restrict__ data_in,
	                        char*       __restrict__ data_out) {
		Stopwatch timer;
		timer.start();
		
		// Lookup table to convert 4+4 bit complex values into 8+8 bit
		// Note: Puts the components into the high 4 bits of each byte
		//         to avoid issues with signed values.
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
		
		// Lookup table to compute total power of 4+4 bit complex samples
		// (I.e., lo4^2 + hi4^2)
		static const unsigned char total_power44[256] = {
			0,  1,  4,  9, 16, 25, 36, 49, 64, 49, 36, 25, 16,  9,  4,  1,
			1,  2,  5, 10, 17, 26, 37, 50, 65, 50, 37, 26, 17, 10,  5,  2,
			4,  5,  8, 13, 20, 29, 40, 53, 68, 53, 40, 29, 20, 13,  8,  5,
			9, 10, 13, 18, 25, 34, 45, 58, 73, 58, 45, 34, 25, 18, 13, 10,
			16, 17, 20, 25, 32, 41, 52, 65, 80, 65, 52, 41, 32, 25, 20, 17,
			25, 26, 29, 34, 41, 50, 61, 74, 89, 74, 61, 50, 41, 34, 29, 26,
			36, 37, 40, 45, 52, 61, 72, 85,100, 85, 72, 61, 52, 45, 40, 37,
			49, 50, 53, 58, 65, 74, 85, 98,113, 98, 85, 74, 65, 58, 53, 50,
			64, 65, 68, 73, 80, 89,100,113,128,113,100, 89, 80, 73, 68, 65,
			49, 50, 53, 58, 65, 74, 85, 98,113, 98, 85, 74, 65, 58, 53, 50,
			36, 37, 40, 45, 52, 61, 72, 85,100, 85, 72, 61, 52, 45, 40, 37,
			25, 26, 29, 34, 41, 50, 61, 74, 89, 74, 61, 50, 41, 34, 29, 26,
			16, 17, 20, 25, 32, 41, 52, 65, 80, 65, 52, 41, 32, 25, 20, 17,
			9, 10, 13, 18, 25, 34, 45, 58, 73, 58, 45, 34, 25, 18, 13, 10,
			4,  5,  8, 13, 20, 29, 40, 53, 68, 53, 40, 29, 20, 13,  8,  5,
			1,  2,  5, 10, 17, 26, 37, 50, 65, 50, 37, 26, 17, 10,  5,  2
		};
		/*
		  Input:  [N sequence numbers][16 roaches][4 input groups][2 time samples][109 chans][4 stations][2 pols][2 dims][4 bits]
		  Output: [2*N time samples][109 chans][256 stations][2 pols][2 dims][8 bits]
		
		  This is the approach used here:
		  [16 roaches 4 input groups][2 time samples 109 chans][4 stations 2 pols 2 dims 4 bits]
		  Transpose dims 0<->1, where each input element is 64 bits
		  [2 time samples 109 chans][16 roaches 4 input groups][4 stations 2 pols 2 dims 4 bits]
		*/
		
		typedef unsigned char uchar;
#define UNPACK_64_BITS {	  \
			const  uchar* p_in  = (uchar*)&in[0]; \
			/* */ ushort* p_out = (ushort*)&out[0]; \
			p_out[0] = four2eight[p_in[0]]; /* a0p0 */ \
			p_out[1] = four2eight[p_in[1]]; /* a0p1 */ \
			p_out[2] = four2eight[p_in[2]]; /* a1p0 */ \
			p_out[3] = four2eight[p_in[3]]; /* a1p1 */ \
			p_out[4] = four2eight[p_in[4]]; /* a2p0 */ \
			p_out[5] = four2eight[p_in[5]]; /* a2p1 */ \
			p_out[6] = four2eight[p_in[6]]; /* a3p0 */ \
			p_out[7] = four2eight[p_in[7]]; /* a3p1 */ \
			in  += NCHAN*NTIME_PER_PKT; \
			out += PROMOTE_FACTOR; \
		}
		/* // Note: This is 2x slower than the above! Moral: don't be fancy!
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
		*/
		//}
		size_t nwords = in_size / sizeof(uint64_t);
		size_t ngulps = nwords / GULP_SIZE;
		
		size_t tp_ninputs   = m_tp_inputs.size();
		int    switch_state = m_state_idx % m_nstates;
		int    buf_position = m_buf_idx % m_bufs_per_state;
		int    nedge        = m_chan_width_mhz*1e6*m_tp_edge_time_s/2;
		size_t edge_begin, edge_end;
		if( buf_position == 0 ) {
			edge_begin = 0;
			edge_end   = edge_begin + nedge;
		}
		else if( buf_position == (m_bufs_per_state-1) ) {
			edge_begin = m_ntime - nedge;
			edge_end   = edge_begin + nedge;
		}
		else {
			edge_begin = 0;
			edge_end   = 0;
		}
		// TODO: Remove when done testing
		cout << "nedge: " << nedge << endl;
		
		for( size_t g=0; g<ngulps; ++g ) {
			for( size_t tp=0; tp<NTIME_PER_PKT; ++tp ) {
				// This is the actual time sample index (within the buffer)
				size_t t = g*NTIME_PER_PKT + tp;
#pragma omp parallel for
				for( size_t c=0; c<NCHAN; ++c ) {
					size_t tc = tp*NCHAN + c;
					
					const uint64_t* __restrict__ in  = ((uint64_t*)data_in) + g*GULP_SIZE + tc;
					/* */ uint64_t* __restrict__ out = ( ((uint64_t*)data_out) +
					                                     g*GULP_SIZE*PROMOTE_FACTOR +
					                                     tc*(NGROUP_PER_PKT*NROACH*PROMOTE_FACTOR) );
					
					// Integrate and blank samples from total power inputs
					for( size_t tpi=0; tpi<tp_ninputs; ++tpi ) {
						int inp = m_tp_inputs[tpi];
						int iword = inp/8;
						int ibyte = inp%8;
						size_t tp_src_idx = iword * NCHAN*NTIME_PER_PKT;
						// Note: Const cast to allow in-place blanking prior to
						//         unpacking.
						uchar* p_in = (uchar*)&in[tp_src_idx];
						
						bool on_edge = (edge_begin <= t && t < edge_end);
						if( !on_edge ) {
							size_t tp_dst_idx = tpi + tp_ninputs*(c + NCHAN*switch_state);
							uchar samp = p_in[ibyte];
							m_tp_accums[tp_dst_idx] += total_power44[samp];
						}
						if( on_edge ||
						    switch_state != m_tp_sky_state ) {
							p_in[ibyte] = 0;
						}
					}
					
					// Note: It seems that gcc kind of sucks here; the loop is
					//         much slower than the manually-unrolled version.
					//for( size_t rg=0; rg<NGROUP_PER_PKT*NROACH; ++rg ) {
					//UNPACK_64_BITS;
					
					// (a0p0, ...), (a4p0, ...), (a8p0, ...), (a12p0, ...)
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS; UNPACK_64_BITS;
					//   (..., a243p1), (..., a247p1), (..., a251p1), (..., a255p1)
					//}
				}
			}
		}
		
		// Now dump the TP integrations to disk if this is the end of a cycle
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
		cout << "Processing time = " << timer.getTime() << " s" << endl;
		size_t ninput    = NROACH*NGROUP_PER_PKT*4*2;
		size_t nsamps    = in_size / sizeof(unsigned char);
		float  bandwidth = nsamps/ninput/timer.getTime();
		cout << "                = " << bandwidth/1e6 << " MHz" << endl;
		
		++m_buf_idx;
		buf_position = m_buf_idx % m_bufs_per_state;
		if( buf_position == 0 ) {
			++m_state_idx;
		}
		
		size_t bytes_written = in_size*2;
		return bytes_written;
	}
public:
	dbupdb512(multilog_t* log, int verbose, int nthreads)
		: dada_db2db(log, verbose),
		  m_bufs_per_state(3), // TODO: Set dynamically?
		  m_nstates(3),        // TODO: Set dynamically?
		  m_tp_edge_time_s(0) {
		cout << "Telling OpenMP to use " << nthreads << " threads" << endl;
		omp_set_num_threads(nthreads);
#pragma omp parallel
		{
			int tid = omp_get_thread_num();
			if( tid == 0 ) {
				int nthreads = omp_get_num_threads();
				cout << "  Threads actually used: " << nthreads << endl;
			}
		}
		
	}
	virtual ~dbupdb512() {}
	
	void setTotalPowerInputs(const int* tp_inputs, size_t tp_ninputs,
	                         float tp_switch_edge_time_secs,
	                         const char* tp_outpath) {
		m_tp_inputs.assign(tp_inputs, tp_inputs + tp_ninputs);
		m_tp_edge_time_s = tp_switch_edge_time_secs;
		m_tp_outpath = tp_outpath;
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

void print_usage() {
	cout << 
		"leda_dbupdb_512_new [options] in_key out_key\n"
		" -c core      Bind process to consecutive CPU cores starting from this\n"
		" -n nthreads  Use nthreads threads [1]\n"
		" -b factor    Bit-promotion factor [2]\n"
		" -p path      Path for total power output (default: no TP output)\n"
		" -e ms        Time to blank around state change edges (default 1.5 ms)\n"
		" -v           Increase verbosity\n"
		" -q           Decrease verbosity\n"
		" -h           Print usage\n" << endl;
}

int main(int argc, char* argv[])
{
	int         core            = -1;
	int         nthreads        = 1;
	int         bit_promotion   = 2;
	int         verbose         = 0;
	key_t       in_key          = 0;
	key_t       out_key         = 0;
	std::string tp_outpath      = "";
	float       tp_edge_time_ms = 1.5;
	multilog_t* log             = 0;
	
	int arg = 0;
	while( (arg = getopt(argc,argv,"c:n:b:p:e:hvq")) != -1 ) {
		switch( arg ) {
		case 'c': if( !parse_arg('c', core) ) return -1; break;
		case 'n': if( !parse_arg('n', nthreads) ) return -1; break;
		case 'b': if( !parse_arg('b', bit_promotion) ) return -1; break;
		case 'p': if( !parse_arg('p', tp_outpath) ) return -1; break;
		case 'e': if( !parse_arg('e', tp_edge_time_ms) ) return -1; break;
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
	
	// Note: This assumes OpenMP hasn't already created its threads. Not sure
	//         if there's any way to actually know. It does seem to work though.
	if( core >= 0 ) {
		// Generate sequential core mask for range [core:core+nthreads)
		uint64_t mask = 0;
		for( int c=core; c<core+nthreads; ++c ) {
			mask |= 1<<c;
		}
		// Set affinity mask
		pid_t tpid = syscall(SYS_gettid);
		if (sched_setaffinity(tpid, sizeof(mask), (cpu_set_t*)&mask) < 0) {
			cerr << "Failed to set CPU affinity: %s" << strerror(errno) << endl;
			return -1;
		}
		if( verbose >= 1 ) {
			cout << "Process bound to core(s) " << core << " (...)" << endl;
		}
	}
	
	dbupdb512 ctx(log, verbose, nthreads);
	
	std::string      tp_inputs_filename = "total_power_inputs.txt";
	std::ifstream    tp_inputs_file(tp_inputs_filename.c_str());
	if( !tp_inputs_file ) {
		fprintf(stderr,
		        "dbupdb512_new: failed to open %s\n",tp_inputs_filename.c_str());
		return -1;
	}
	std::vector<int> tp_inputs;
	tp_inputs.assign(std::istream_iterator<int>(tp_inputs_file),
	                 std::istream_iterator<int>());
	// Note: Convert from 1-based to 0-based
	for( size_t i=0; i<tp_inputs.size(); ++i ) {
		tp_inputs[i] -= 1;
	}
	if( verbose ) {
		fprintf(stderr, "dbupdb512_new: read %lu total power inputs from %s\n",
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
