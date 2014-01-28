
#pragma once

#include <dada_hdu.h>

#include "dada_base.hpp"

class dada_dbreader : public dada_base {
	/* DADA Header plus Data Unit */
	dada_hdu_t* m_hdu_in;
	
	// output data block HDU key
	key_t m_in_key;
	
	uint64_t m_bufsize;
	
protected:
	// Callbacks
	// ---------
	virtual void     onConnect(key_t out_key) {}
	virtual void     onDisconnect() {}
	// Return desired no. bytes per data read
	virtual uint64_t readHeader(uint64_t header_size, const char* header_in) = 0;
	// Return anything
	virtual uint64_t readData(uint64_t in_size, const char* data_in) = 0;
	
	inline uint64_t bufsize() const { return m_bufsize; }
	
	dada_dbreader(multilog_t* log, int verbose);
	virtual ~dada_dbreader();
	
public:
	void connect(key_t in_key);
	void disconnect();
	
	// Allow access for, e.g., registering memory for CUDA
	dada_hdu_t* hdu_in() { return m_hdu_in; }
	
	void run();
};
