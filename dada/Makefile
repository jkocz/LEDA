DBUPDB512NEW_LIBS += -L$(PSRDADA_DIR)/src/.libs -L$(PSRDADA_DIR)/.libs -lpsrdada
DBUPDB512NEW_INC  += -I$(PSRDADA_DIR)/src #-I$(PSRDADA_DIR)

CXX_FLAGS   += -Wall -pedantic -O3
DEBUG_FLAGS += -g

CXX ?= g++

all: leda_dbupdb_512_new

leda_dbupdb_512_new: leda_dbupdb_512_new.cpp dada_db2db.hpp dada_db2db.cpp
	$(CXX) -o leda_dbupdb_512_new $(CXX_FLAGS) $(DEBUG_FLAGS) $(DBUPDB512NEW_INC) leda_dbupdb_512_new.cpp dada_db2db.cpp $(DBUPDB512NEW_LIBS)
