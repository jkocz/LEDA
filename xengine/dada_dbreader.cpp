
#include "dada_dbreader.hpp"

#include <stdexcept>

dada_dbreader::dada_dbreader(multilog_t* log, int verbose)
	: dada_base(log, verbose),
	  m_hdu_in(0),
	  m_in_key(0),
	  m_bufsize(0) {}
dada_dbreader::~dada_dbreader() {
	this->disconnect();
}

void dada_dbreader::connect(key_t in_key) {
	this->disconnect();
	m_in_key = in_key;
	if( m_verbose ) {
		multilog(m_log, LOG_INFO, "dbreader: creating in hdu\n");
	}
	// open connection to the in/write DB
	m_hdu_in = dada_hdu_create(m_log);
	dada_hdu_set_key(m_hdu_in, m_in_key);
	if( dada_hdu_connect(m_hdu_in) < 0 ) { 
		throw std::runtime_error("Could not connect to input buffer");
	}
	if( dada_hdu_lock_read(m_hdu_in) < 0 ) {
		throw std::runtime_error("Could not lock input buffer for reading");
	}
	if( m_verbose ) {
		multilog(m_log, LOG_INFO, "dbreader: initialisation complete\n");
	}
	
	m_bufsize = ipcbuf_get_bufsz((ipcbuf_t*)m_hdu_in->data_block);
	
	this->onConnect(in_key);
}
void dada_dbreader::disconnect() {
	if( m_hdu_in ) {
		if( dada_hdu_unlock_read(m_hdu_in) < 0 ) {
			multilog(m_log, LOG_ERR, "dbreader: could not unlock read on hdu_in\n");
		}
		dada_hdu_destroy(m_hdu_in);
		m_hdu_in = 0;
		m_in_key = 0;
		m_bufsize = 0;
		
		this->onDisconnect();
	}
}

void dada_dbreader::run() {
	if( m_verbose ) {
		multilog(m_log, LOG_INFO, "dbreader: Beginning run\n");
	}
	
	if( m_verbose ) {
		multilog(m_log, LOG_INFO, "dbreader: Waiting to read input header\n");
	}
	uint64_t header_size = 0;
	char *   header_in = ipcbuf_get_next_read(m_hdu_in->header_block,
	                                          &header_size);
	if( !header_in ) {
		multilog(m_log, LOG_ERR, "dbreader: could not read next header\n");
		throw std::runtime_error("dbreader: Could not read next header");
	}
	
	// Callback
	uint64_t bytes_per_read = this->readHeader(header_size, header_in);
	
	if( m_verbose ) {
		multilog(m_log, LOG_INFO, "dbreader: Marking headers as cleared and filled\n");
	}
	// mark the input header as cleared
	if( ipcbuf_mark_cleared (m_hdu_in->header_block) < 0 ) {
		multilog(m_log, LOG_ERR, "dbreader: could not mark header block cleared [input]\n");
		throw std::runtime_error("dbreader: could not mark header block cleared [input]");
	}
	
	multilog(m_log, LOG_INFO, "dbreader: bytes_per_read=%llu\n", bytes_per_read);
	
	uint64_t block_size = ipcbuf_get_bufsz((ipcbuf_t*)m_hdu_in->data_block);
	uint64_t bytes_to_read;
	uint64_t block_id;
	
	multilog(m_log, LOG_INFO,
	         "dbreader: block_size=%llu\n", block_size);
	
	bool observation_complete = false;
	while( !observation_complete ) {
		// open a DADA block
		char* in_block = ipcio_open_block_read(m_hdu_in->data_block,
		                                       &bytes_to_read, &block_id);
		if( m_verbose ) {
			multilog(m_log, LOG_INFO,
			         "dbreader: opened block %llu which contains %llu bytes\n",
			         block_id, bytes_to_read);
		}
		
		for( uint64_t ibyte=0; ibyte < bytes_to_read; ibyte += bytes_per_read ) {
			if( m_verbose ) {
				multilog(m_log, LOG_INFO,
				         "dbreader: [%llu] ibyte=%llu bytes_to_read=%llu bytes_per_read=%llu\n",
				         block_id, ibyte, bytes_to_read, bytes_per_read);
			}
			if( ibyte + bytes_per_read > bytes_to_read ) {
				multilog(m_log, LOG_INFO,
				         "dbreader: skipping non full gulp\n");
			}
			else {
				
				// Callback
				this->readData(bytes_per_read, in_block);
				
			}
			
			// increment the block pointer by the gulp amount (in bytes)
			in_block += bytes_per_read;
		}
		ipcio_close_block_read(m_hdu_in->data_block, bytes_to_read);
		
		// TODO: Both of these checks evaluate true at the end of data
		if( bytes_to_read < block_size ) {
			observation_complete = 1;
		}
		// check for end of data in the DADA block
		if( ipcbuf_eod((ipcbuf_t*)m_hdu_in->data_block) ) {
			multilog(m_log, LOG_INFO, "end of data reached, exiting\n");
			observation_complete = 1;
		}
	}
}
