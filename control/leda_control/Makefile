
LIBS        = 
CXX_FLAGS   = -Wall -pedantic -O3
DEBUG_FLAGS = -g
INCLUDE     = -I$(CUDA_DIR)/include
GXX         = g++

leda_visconverter: leda_visconverter.cpp xgpu_convert.cpp
	$(GXX) -o leda_visconverter $(CXX_FLAGS) $(LIBS) $(DEBUG_FLAGS) $(INCLUDE) leda_visconverter.cpp xgpu_convert.cpp
