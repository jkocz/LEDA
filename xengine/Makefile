
PSRDADA_DIR  ?= $(HOME)/psrdada
CUDA_DIR     ?= /usr/local/cuda
XGPU_DIR     ?= .
PSRDADA_LIBS += -L$(PSRDADA_DIR)/src/.libs -L$(PSRDADA_DIR)/.libs -lpsrdada
PSRDADA_INC  += -I$(PSRDADA_DIR)/src -I$(PSRDADA_DIR)
CUDA_LIBS    += -L$(CUDA_DIR)/lib64 -lcudart
CUDA_INC     += -I$(CUDA_DIR)/include

DBXGPU_LIBS += $(CUDA_LIBS) -L$(XGPU_DIR)/src -lxgpu $(PSRDADA_LIBS)
DBXGPU_INC  += $(CUDA_INC) -I$(XGPU_DIR)/src $(PSRDADA_INC)

DBTP_LIBS += $(PSRDADA_LIBS)
DBTP_INC  += $(PSRDADA_INC)

DBPOST_ADAPTER_LIBS += $(PSRDADA_LIBS)
DBPOST_ADAPTER_INC  += $(PSRDADA_INC)

DBBDI_LIBS += $(PSRDADA_LIBS)
DBBDI_INC  += $(PSRDADA_INC)

DBBEAM_LIBS += $(PSRDADA_LIBS) -Laaplus/lib -laaplus
DBBEAM_INC  += $(PSRDADA_INC)

DBBASEBAND_INC += $(PSRDADA_INC)

DBUPDB512NEW_LIBS += -L$(PSRDADA_DIR)/src/.libs -L$(PSRDADA_DIR)/.libs -lpsrdada -fopenmp -lgomp
DBUPDB512NEW_INC  += -I$(PSRDADA_DIR)/src -I$(PSRDADA_DIR)

CXX_FLAGS   += -Wall -pedantic -O3 -Wno-long-long
NVCC_FLAGS  += -Xcompiler "-Wall -Wno-long-long" -O3 -arch=sm_35
DEBUG_FLAGS += -g

CXX  ?= g++
NVCC ?= nvcc

all: leda_dbxgpu hackhex leda_dbbdi leda_dbbeam leda_dbbeam_gpu leda_dbbaseband

leda_dbxgpu: leda_dbxgpu.cpp dada_db2db.hpp dada_db2db.cpp
	$(CXX) -o leda_dbxgpu $(CXX_FLAGS) $(DEBUG_FLAGS) $(DBXGPU_INC) leda_dbxgpu.cpp dada_db2db.cpp $(DBXGPU_LIBS)

leda_dbbdi: leda_dbbdi.cpp dada_db2db.hpp dada_db2db.cpp
	$(CXX) -o leda_dbbdi $(CXX_FLAGS) $(DEBUG_FLAGS) $(DBBDI_INC) leda_dbbdi.cpp dada_db2db.cpp $(DBBDI_LIBS)

aaplus/lib/libaaplus.so:
	cd aaplus; cmake .; make; cd ..

leda_dbbeam: leda_dbbeam.cpp dada_db2db.hpp dada_db2db.cpp aaplus/lib/libaaplus.so
	$(CXX) -o leda_dbbeam $(CXX_FLAGS) -ffast-math $(DEBUG_FLAGS) $(DBBEAM_INC) leda_dbbeam.cpp dada_db2db.cpp $(DBBEAM_LIBS)
leda_dbbeam.asm: leda_dbbeam.cpp dada_db2db.hpp dada_db2db.cpp aaplus/lib/libaaplus.so
	$(CXX) -o leda_dbbeam.asm $(CXX_FLAGS) -ffast-math -fverbose-asm -S $(DEBUG_FLAGS) $(DBBEAM_INC) leda_dbbeam.cpp $(DBBEAM_LIBS)

leda_dbbeam_gpu: leda_dbbeam_gpu.cu dada_db2db.hpp dada_db2db.cpp
	$(NVCC) -o leda_dbbeam_gpu $(NVCC_FLAGS) $(DEBUG_FLAGS) $(DBBEAM_INC) leda_dbbeam_gpu.cu dada_db2db.cpp $(PSRDADA_LIBS)

leda_dbbaseband: leda_dbbaseband.cpp dada_db2db.hpp dada_db2db.cpp
	$(CXX) -o leda_dbbaseband $(CXX_FLAGS) $(DEBUG_FLAGS) $(DBBASEBAND_INC) leda_dbbaseband.cpp dada_db2db.cpp $(PSRDADA_LIBS)

hackhex: hackhex.cpp
	$(CXX) -o hackhex hackhex.cpp

leda_dbpost_adapter: leda_dbpost_adapter.cpp dada_db2db.hpp dada_db2db.cpp
	$(CXX) -o leda_dbpost_adapter $(CXX_FLAGS) $(DEBUG_FLAGS) $(DBPOST_ADAPTER_INC) leda_dbpost_adapter.cpp dada_dbreader.cpp $(DBPOST_ADAPTER_LIBS)

leda_dbtp: leda_dbtp.cpp dada_db2db.hpp dada_db2db.cpp
	$(CXX) -o leda_dbtp $(CXX_FLAGS) $(DEBUG_FLAGS) $(DBTP_INC) leda_dbtp.cpp dada_db2db.cpp $(DBTP_LIBS)

leda_dbupdb_512_new: leda_dbupdb_512_new.cpp dada_db2db.hpp dada_db2db.cpp
	$(CXX) -o leda_dbupdb_512_new $(CXX_FLAGS) $(DEBUG_FLAGS) $(DBUPDB512NEW_INC) leda_dbupdb_512_new.cpp dada_db2db.cpp $(DBUPDB512NEW_LIBS)
