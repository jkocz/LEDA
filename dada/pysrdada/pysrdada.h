
#ifndef PSRDADA_PY_H
#define PSRDADA_PY_H

#include <dada_hdu.h>
//#include <dada_def.h>
//#include <ascii_header.h>

enum {
	DADA_LOCK_NONE,
	DADA_LOCK_READ,
	DADA_LOCK_WRITE
};

enum {
	DADA_NO_ERROR,
	DADA_MEM_ALLOC_FAILED,
	DADA_CONNECT_FAILED,
	DADA_LOCK_FAILED,
	DADA_UNLOCK_FAILED,
	DADA_NOT_CONNECTED,
	DADA_NO_MATCHING_LOCK,
	DADA_OPEN_BLOCK_FAILED,
	DADA_READ_FAILED,
	DADA_WRITE_FAILED,
	DADA_INTERNAL_ERROR
};

typedef struct dada_handle_t* dada_handle;

int dada_create(dada_handle* obj,
                const char* logname);
int dada_destroy(dada_handle obj);
int dada_connect(dada_handle obj,
                 key_t       key);
int dada_lock_read(dada_handle obj);
int dada_lock_write(dada_handle obj);
int dada_unlock(dada_handle obj);
int dada_disconnect(dada_handle obj);
int dada_read_header(const dada_handle obj,
                     char*             header);
int dada_write_header(const dada_handle obj,
                      const char*       header);
int dada_read_buffer(const dada_handle obj,
                     char*             data);
int dada_write_buffer(const dada_handle obj,
                      const char*       data);
int dada_is_eod(const dada_handle obj);
int dada_get_lock(const dada_handle obj);
key_t dada_get_key(const dada_handle obj);
dada_hdu_t* dada_get_hdu(const dada_handle obj);
multilog_t* dada_get_log(const dada_handle obj);
uint64_t dada_get_header_size(const dada_handle obj);
uint64_t dada_get_buffer_size(const dada_handle obj);
const char* dada_get_error_string(int error);

#endif // PSRDADA_PY_H
