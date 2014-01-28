
#pragma once

#include <string>
#include <dada_hdu.h>

class dada_base {
public:
	/* DADA Logger */
	multilog_t* m_log;
	/* Flag set in verbose mode */
	int m_verbose;

protected:
	// Utilities
	// ---------
	inline void logInfo(std::string msg) const {
		if( m_verbose ) {
			multilog(m_log, LOG_INFO, (msg + "\n").c_str());
		}
	}
	inline void logError(std::string msg) const {
		multilog(m_log, LOG_ERR, (msg + "\n").c_str());
	}
	inline void logWarning(std::string msg) const {
		multilog(m_log, LOG_WARNING, (msg + "\n").c_str());
	}
	
	//bool verbose() const { return m_verbose; }
	
	dada_base(multilog_t* log, int verbose)
		: m_log(log), m_verbose(verbose) {}
	virtual ~dada_base() {}
};
