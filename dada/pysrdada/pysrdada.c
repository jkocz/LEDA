
#include "pysrdada.h"

#include <stdlib.h>
#include <string.h>

struct dada_handle_t {
	int         lock;
	key_t       key;
	dada_hdu_t* hdu;
	multilog_t* log;
	uint64_t    bufsize;
	uint64_t    headersize;
};

int dada_create(dada_handle* obj, const char* logname) {
	multilog_t* log = multilog_open(logname, 0);
	multilog_add(log, stderr);
	
	dada_handle newobj = (dada_handle)malloc(sizeof(struct dada_handle_t));
	if( !newobj ) {
		return DADA_MEM_ALLOC_FAILED;
	}
	newobj->lock    = DADA_LOCK_NONE;
	newobj->key     = 0;
	newobj->hdu     = 0;
	newobj->log     = log;
	newobj->bufsize = 0;
	*obj = newobj;
	
	return DADA_NO_ERROR;
}
int dada_destroy(dada_handle obj) {
	if( obj ) {
		dada_disconnect(obj);
		free(obj);
	}
	return DADA_NO_ERROR;
}
int dada_connect(dada_handle obj,
                 key_t       key) {
	obj->key = key;
	obj->hdu = dada_hdu_create(obj->log);
	dada_hdu_set_key(obj->hdu, obj->key);
	if( dada_hdu_connect(obj->hdu) < 0 ) {
		return DADA_CONNECT_FAILED;
	}
	obj->bufsize    = ipcbuf_get_bufsz((ipcbuf_t*)obj->hdu->data_block);
	obj->headersize = ipcbuf_get_bufsz((ipcbuf_t*)obj->hdu->header_block);
	return DADA_NO_ERROR;
}
int dada_lock_read(dada_handle obj) {
	if( dada_hdu_lock_read(obj->hdu) < 0 ) {
		return DADA_LOCK_FAILED;
	}
	obj->lock = DADA_LOCK_READ;
	return DADA_NO_ERROR;
}
int dada_lock_write(dada_handle obj) {
	if( dada_hdu_lock_write(obj->hdu) < 0 ) {
		return DADA_LOCK_FAILED;
	}
	obj->lock = DADA_LOCK_WRITE;
	return DADA_NO_ERROR;
}
int dada_unlock(dada_handle obj) {
	int ret;
	switch( obj->lock ) {
	case DADA_LOCK_NONE:  ret = 0; break;
	case DADA_LOCK_READ:  ret = dada_hdu_unlock_read(obj->hdu); break;
	case DADA_LOCK_WRITE: ret = dada_hdu_unlock_write(obj->hdu); break;
	default: return DADA_INTERNAL_ERROR;
	}
	if( ret < 0 ) {
		return DADA_UNLOCK_FAILED;
	}
	return DADA_NO_ERROR;
}
int dada_disconnect(dada_handle obj) {
	if( obj->hdu ) {
		int ret = dada_unlock(obj);
		if( ret != DADA_NO_ERROR ) {
			return ret;
		}
		dada_hdu_destroy(obj->hdu);
		obj->lock    = DADA_LOCK_NONE;
		obj->key     = 0;
		obj->hdu     = 0;
		obj->bufsize = 0;
	}
	return DADA_NO_ERROR;
}
int dada_read_header(const dada_handle obj,
                     char*             header) {
	if( !obj->hdu ) {
		return DADA_NOT_CONNECTED;
	}
	if( obj->lock != DADA_LOCK_READ ) {
		return DADA_NO_MATCHING_LOCK;
	}
	
	uint64_t header_size = 0;
	char*    header_in = ipcbuf_get_next_read(obj->hdu->header_block,
	                                          &header_size);
	if( !header_in ) {
		return DADA_OPEN_BLOCK_FAILED;
	}
	memcpy(header, header_in, header_size);
	if( ipcbuf_mark_cleared(obj->hdu->header_block) < 0 ) {
		return DADA_READ_FAILED;
	}
	return DADA_NO_ERROR;
}
int dada_write_header(const dada_handle obj,
                      const char*       header) {
	if( !obj->hdu ) {
		return DADA_NOT_CONNECTED;
	}
	if( obj->lock != DADA_LOCK_WRITE ) {
		return DADA_NO_MATCHING_LOCK;
	}
	
	char* header_out = ipcbuf_get_next_write(obj->hdu->header_block);
	if( !header_out ) {
		return DADA_OPEN_BLOCK_FAILED;
	}
	memcpy(header_out, header, obj->headersize);
	if( ipcbuf_mark_filled(obj->hdu->header_block, obj->headersize) < 0 ) {
		return DADA_WRITE_FAILED;
	}
	return DADA_NO_ERROR;
}
// TODO: Allow incomplete block reads and writes
int dada_read_buffer(const dada_handle obj,
                     char*             data) {
	if( !obj->hdu ) {
		return DADA_NOT_CONNECTED;
	}
	if( obj->lock != DADA_LOCK_READ ) {
		return DADA_NO_MATCHING_LOCK;
	}
	
	uint64_t bytes_to_read;
	uint64_t block_id;
	char* in_block = ipcio_open_block_read(obj->hdu->data_block,
	                                       &bytes_to_read, &block_id);
	if( !in_block ) {
		return DADA_OPEN_BLOCK_FAILED;
	}
	memcpy(data, in_block, bytes_to_read);
	ipcio_close_block_read(obj->hdu->data_block, bytes_to_read);
	return DADA_NO_ERROR;
}
int dada_write_buffer(const dada_handle obj,
                      const char*       data) {
	if( !obj->hdu ) {
		return DADA_NOT_CONNECTED;
	}
	if( obj->lock != DADA_LOCK_WRITE ) {
		return DADA_NO_MATCHING_LOCK;
	}
	
	uint64_t block_id;
	char* out_block = ipcio_open_block_write(obj->hdu->data_block,
	                                        &block_id);
	if( !out_block ) {
		return DADA_OPEN_BLOCK_FAILED;
	}
	uint64_t bytes_written = obj->bufsize;
	memcpy(out_block, data, bytes_written);
	ipcio_close_block_write(obj->hdu->data_block, bytes_written);
	return DADA_NO_ERROR;
}
int dada_is_eod(const dada_handle obj) {
	return ipcbuf_eod((ipcbuf_t*)obj->hdu->data_block);
}
int dada_get_lock(const dada_handle obj) {
	return obj->lock;
}
key_t dada_get_key(const dada_handle obj) {
	return obj->key;
}
dada_hdu_t* dada_get_hdu(const dada_handle obj) {
	return obj->hdu;
}
multilog_t* dada_get_log(const dada_handle obj) {
	return obj->log;
}
uint64_t dada_get_header_size(const dada_handle obj) {
	return obj->headersize;
}
uint64_t dada_get_buffer_size(const dada_handle obj) {
	return obj->bufsize;
}
const char* dada_get_error_string(int error) {
	switch( error ) {
	case DADA_NO_ERROR:
		return "No error";
	case DADA_MEM_ALLOC_FAILED:
		return "Memory allocation failed";
	case DADA_CONNECT_FAILED:
		return "Failed to connect to buffer";
	case DADA_LOCK_FAILED:
		return "Failed to lock buffer";
	case DADA_UNLOCK_FAILED:
		return "Failed to unlock buffer";
	case DADA_NOT_CONNECTED:
		return "Not connected to buffer";
	case DADA_NO_MATCHING_LOCK:
		return "Not locked or incorrectly locked";
	case DADA_OPEN_BLOCK_FAILED:
		return "Failed to open block";
	case DADA_READ_FAILED:
		return "Failed to read";
	case DADA_WRITE_FAILED:
		return "Failed to write";
	case DADA_INTERNAL_ERROR:
		return "Internal library error";
	default:
		return "Invalid error code";
	}
}
