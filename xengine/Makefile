DBXGPU_LIBS += -L$(CUDA_DIR)/lib64 -lcudart -L$(XGPU_DIR)/src -lxgpu -L$(PSRDADA_DIR)/src/.libs -L$(PSRDADA_DIR)/.libs -lpsrdada
DBXGPU_INC  += -I$(CUDA_DIR)/include -I$(XGPU_DIR)/src -I$(PSRDADA_DIR)/src -I$(PSRDADA_DIR)

DBBDI_LIBS += -L$(PSRDADA_DIR)/src/.libs -L$(PSRDADA_DIR)/.libs -lpsrdada
DBBDI_INC  += -I$(PSRDADA_DIR)/src -I$(PSRDADA_DIR)

CXX_FLAGS   += -Wall -pedantic -O3
DEBUG_FLAGS += -g

CXX ?= g++

all: leda_dbxgpu hackhex

leda_dbxgpu: leda_dbxgpu.cpp dada_db2db.hpp dada_db2db.cpp
	$(CXX) -o leda_dbxgpu $(CXX_FLAGS) $(DEBUG_FLAGS) $(DBXGPU_INC) leda_dbxgpu.cpp dada_db2db.cpp $(DBXGPU_LIBS)

leda_dbbdi: leda_dbbdi.cpp dada_db2db.hpp dada_db2db.cpp
	$(CXX) -o leda_dbbdi $(CXX_FLAGS) $(DEBUG_FLAGS) $(DBBDI_INC) leda_dbbdi.cpp dada_db2db.cpp $(DBBDI_LIBS)

hackhex: hackhex.cpp
	$(CXX) -o hackhex hackhex.cpp
