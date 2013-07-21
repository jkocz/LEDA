
#pragma once

#include <string>

#include <dada_hdu.h>

class dada_db2db {
	/* DADA Header plus Data Unit */
	dada_hdu_t* m_hdu_in;
	dada_hdu_t* m_hdu_out;
	/* DADA Logger */
	multilog_t* m_log;
	/* Flag set in verbose mode */
	int m_verbose;
	
	// input data block HDU key
	key_t m_in_key;
	// output data block HDU key
	key_t m_out_key;
	
	uint64_t m_bufsize_in;
	uint64_t m_bufsize_out;
	
protected:
	// Callbacks
	// ---------
	virtual void     onConnect(key_t in_key, key_t out_key) {}
	virtual void     onDisconnect() {}
	// Return desired no. bytes per data read
	virtual uint64_t onHeader(uint64_t header_size,
	                          const char* header_in, char* header_out) = 0;
	// Return no. bytes written
	virtual uint64_t onData(uint64_t in_size,
	                        const char* data_in, char* data_out) = 0;
	
	// TODO: These aren't very good; either remove or re-implement
	// Utilities
	// ---------
	void logInfo(std::string msg) const {
		if( m_verbose ) {
			multilog(m_log, LOG_INFO, (msg + "\n").c_str());
		}
	}
	void logError(std::string msg) const {
		multilog(m_log, LOG_ERR, (msg + "\n").c_str());
	}
	void logWarning(std::string msg) const {
		multilog(m_log, LOG_WARNING, (msg + "\n").c_str());
	}
	
	inline uint64_t bufsize_in()  const { return m_bufsize_in; }
	inline uint64_t bufsize_out() const { return m_bufsize_out; }
	
	dada_db2db(multilog_t* log, int verbose);
	virtual ~dada_db2db();
	
public:
	void connect(key_t in_key, key_t out_key);
	void disconnect();
	
	// Allow access for, e.g., registering memory for CUDA
	dada_hdu_t* hdu_in()  { return m_hdu_in; }
	dada_hdu_t* hdu_out() { return m_hdu_out; }
	
	void run();
};
