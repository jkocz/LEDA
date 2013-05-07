
#include "dada_db2db.hpp"

#include <stdexcept>

dada_db2db::dada_db2db(multilog_t* log, int verbose)
	: m_hdu_in(0), m_hdu_out(0),
	  m_log(log), m_verbose(verbose),
	  m_in_key(0), m_out_key(0),
	  m_bufsize_in(0), m_bufsize_out(0) {}
dada_db2db::~dada_db2db() {
	this->disconnect();
}

void dada_db2db::connect(key_t in_key, key_t out_key) {
	this->disconnect();
	m_in_key  = in_key;
	m_out_key = out_key;
	if( m_verbose ) {
		multilog(m_log, LOG_INFO, "db2db: creating in hdu\n");
	}
	// open connection to the in/read DB
	m_hdu_in = dada_hdu_create(m_log);
	dada_hdu_set_key(m_hdu_in, m_in_key);
	if( dada_hdu_connect(m_hdu_in) < 0 ) {
		throw std::runtime_error("Could not connect to input buffer");
	}
	if( dada_hdu_lock_read(m_hdu_in) < 0 ) {
		throw std::runtime_error("Could not lock input buffer for reading");
	}
	if( m_verbose ) {
		multilog(m_log, LOG_INFO, "db2db: creating out hdu\n");
	}
	// open connection to the out/write DB
	m_hdu_out = dada_hdu_create(m_log);
	dada_hdu_set_key(m_hdu_out, m_out_key);
	if( dada_hdu_connect(m_hdu_out) < 0 ) { 
		throw std::runtime_error("Could not connect to output buffer");
	}
	if( dada_hdu_lock_write(m_hdu_out) < 0 ) {
		throw std::runtime_error("Could not lock output buffer for writing");
	}
	if( m_verbose ) {
		multilog(m_log, LOG_INFO, "db2db: initialisation complete\n");
	}
	
	m_bufsize_in  = ipcbuf_get_bufsz((ipcbuf_t*)m_hdu_in->data_block);
	m_bufsize_out = ipcbuf_get_bufsz((ipcbuf_t*)m_hdu_out->data_block);
	
	this->onConnect(in_key, out_key);
}
void dada_db2db::disconnect() {
	bool was_connected = m_hdu_in || m_hdu_out;
	if( m_hdu_in ) {
		if( dada_hdu_unlock_read(m_hdu_in) < 0 ) {
			multilog(m_log, LOG_ERR, "db2db: could not unlock read on hdu_in\n");
		}
		dada_hdu_destroy(m_hdu_in);
		m_hdu_in = 0;
		m_in_key = 0;
		m_bufsize_in = 0;
	}
	if( m_hdu_out ) {
		if( dada_hdu_unlock_write(m_hdu_out) < 0 ) {
			multilog(m_log, LOG_ERR, "db2db: could not unlock write on hdu_out\n");
		}
		dada_hdu_destroy(m_hdu_out);
		m_hdu_out = 0;
		m_out_key = 0;
		m_bufsize_out = 0;
	}
	if( was_connected ) {
		this->onDisconnect();
	}
}
	
void dada_db2db::run() {
	if( m_verbose ) {
		multilog(m_log, LOG_INFO, "db2db: Beginning run\n");
	}
		
	if( m_verbose ) {
		multilog(m_log, LOG_INFO, "db2db: Waiting to read input header\n");
	}
	uint64_t header_size = 0;
	char *   header_in = ipcbuf_get_next_read(m_hdu_in->header_block,
	                                          &header_size);
	if( !header_in ) {
		multilog(m_log, LOG_ERR, "could not read next header\n");
		throw std::runtime_error("Could not read next header");
	}
		
	// TODO: Can/should read nfrequency(nchan) and NPOL from header?
		
	// now write the output DADA header
	if( m_verbose ) {
		multilog(m_log, LOG_INFO, "db2db: Writing output header\n");
	}
	char* header_out = ipcbuf_get_next_write(m_hdu_out->header_block);
	if( !header_out ) {
		multilog(m_log, LOG_ERR, "db2db: could not get next header block [output]\n");
		throw std::runtime_error("db2db: could not get next header block [output]");
	}
	
	// Callback
	uint64_t bytes_per_read = this->onHeader(header_size, header_in,
	                                         header_out);
	
	if( m_verbose ) {
		multilog(m_log, LOG_INFO, "db2db: Marking headers as cleared and filled\n");
	}
	// mark the input header as cleared
	if( ipcbuf_mark_cleared (m_hdu_in->header_block) < 0 ) {
		multilog(m_log, LOG_ERR, "db2db: could not mark header block cleared [input]\n");
		throw std::runtime_error("db2db: could not mark header block cleared [input]");
	}
	
	// mark the output header buffer as filled
	if( ipcbuf_mark_filled (m_hdu_out->header_block, header_size) < 0 ) {
		multilog(m_log, LOG_ERR, "db2db: could not mark header block filled [output]\n");
		throw std::runtime_error("db2db: could not mark header block filled [output]");
	}
	
	//uint64_t bytes_per_read = ?????;
	multilog(m_log, LOG_INFO, "bytes_per_read=%llu\n", bytes_per_read);
	
	uint64_t in_block_size  = ipcbuf_get_bufsz((ipcbuf_t*)m_hdu_in->data_block);
	uint64_t out_block_size = ipcbuf_get_bufsz((ipcbuf_t*)m_hdu_out->data_block);
	uint64_t bytes_to_read;
	uint64_t block_id;
	uint64_t bytes_written_block;
	uint64_t bytes_written_total = 0;
	
	// Note: We open an output block here and only close it when it's full,
	//         so data can be written by onData( ) at any pace.
	uint64_t out_block_id;
	char* out_block = ipcio_open_block_write(m_hdu_out->data_block,
	                                         &out_block_id);
	bytes_written_block = 0;
	if( m_verbose ) {
		multilog(m_log, LOG_INFO,
		         "db2db: opened output block %llu which has space for %llu bytes\n",
		         out_block_id, out_block_size);
	}
	
	bool observation_complete = false;
	while( !observation_complete ) {
		// open a DADA block
		char* in_block = ipcio_open_block_read(m_hdu_in->data_block,
		                                       &bytes_to_read, &block_id);
		if( m_verbose ) {
			multilog(m_log, LOG_INFO,
			         "db2db: opened input block %llu which contains %llu bytes\n",
			         block_id, bytes_to_read);
		}
		
		for( uint64_t ibyte=0; ibyte < bytes_to_read; ibyte += bytes_per_read ) {
			if( m_verbose ) {
				multilog(m_log, LOG_INFO,
				         "db2db: [%llu] ibyte=%llu bytes_to_read=%llu bytes_per_read=%llu\n",
				         block_id, ibyte, bytes_to_read, bytes_per_read);
			}
			uint64_t bytes_written;
			if( ibyte + bytes_per_read > bytes_to_read ) {
				multilog(m_log, LOG_INFO,
				         "db2db: skipping non full gulp\n");
				bytes_written = 0;
			}
			else {
				
				// Callback
				bytes_written = this->onData(bytes_per_read, in_block, out_block);
				
				out_block += bytes_written;
				bytes_written_block += bytes_written;
				bytes_written_total += bytes_written;
				if( m_verbose ) {
					multilog(m_log, LOG_INFO,
					         "db2db: wrote %llu bytes, %llu block, %llu total\n",
					         bytes_written, bytes_written_block, bytes_written_total);
				}
				
				// Check for completed output block
				if( bytes_written_block == out_block_size ) {
					ipcio_close_block_write(m_hdu_out->data_block,
					                        bytes_written_block);
					out_block = ipcio_open_block_write(m_hdu_out->data_block,
					                                   &out_block_id);
					bytes_written_block = 0;
					if( m_verbose ) {
						multilog(m_log, LOG_INFO,
						         "db2db: opened output block %llu which has space for %llu bytes\n",
						         out_block_id, out_block_size);
					}
				}
				else if( bytes_written_block > out_block_size ) {
					multilog(m_log, LOG_ERR,
					         "db2db: wrote %llu bytes past end of output buffer!\n",
					         bytes_written_block - out_block_size);
					throw std::runtime_error("db2db: wrote data past end of output buffer");
				}
			}
			
			// increment the block pointer by the gulp amount (in bytes)
			in_block += bytes_per_read;
		}
		ipcio_close_block_read(m_hdu_in->data_block, bytes_to_read);
		
		//bytes_written_total += bytes_written_block;
		
		// TODO: Both of these checks evaluate true at the end of data
		if( bytes_to_read < in_block_size ) {
			observation_complete = 1;
		}
		// check for end of data in the DADA block
		if( ipcbuf_eod((ipcbuf_t*)m_hdu_in->data_block) ) {
			multilog(m_log, LOG_INFO, "end of data reached, exiting\n");
			observation_complete = 1;
		}
	}
	ipcio_close_block_write(m_hdu_out->data_block, bytes_written_block);
}
