
SRC_DIR = .
OBJ_DIR = .
LIB_DIR = .

OPTIMISE = -O3
DEBUG    = -g

SOURCES = pysrdada.c pysrdada.h
INCLUDE = -I$(PSRDADA_DIR)/src
LIB     = -L$(PSRDADA_DIR)/src/.libs -lpsrdada

LIB_NAME  := libpysrdada
SO_EXT    := .so
MAJOR     := 1
MINOR     := 0.1
SO_FILE   := $(LIB_NAME)$(SO_EXT).$(MAJOR).$(MINOR)
SO_NAME   := $(LIB_DIR)/$(SO_FILE)
VERSION_FILE := $(LIB_NAME).version

$(SO_NAME): $(SOURCES)
	gcc -c -fPIC -Wall $(OPTIMISE) $(DEBUG) $(INCLUDE) -o $(OBJ_DIR)/pysrdada.o $(SRC_DIR)/pysrdada.c
	gcc -shared -Wl,--version-script=$(VERSION_FILE),-soname,$(LIB_NAME)$(SO_EXT).$(MAJOR) -o $(SO_NAME) $(OBJ_DIR)/pysrdada.o $(LIB)
	ln -s -f $(SO_FILE) $(LIB_DIR)/$(LIB_NAME)$(SO_EXT).$(MAJOR)
	ln -s -f $(SO_FILE) $(LIB_DIR)/$(LIB_NAME)$(SO_EXT)

clean:
	rm -f $(SO_NAME) $(OBJ_DIR)/*.o
