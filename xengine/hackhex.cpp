
#include <fstream>
#include <iostream>
using std::cout;
using std::endl;
#include <vector>
#include <iomanip>

//typedef unsigned long long word;
//typedef unsigned int word;
typedef unsigned short word;

int main(int argc, char* argv[])
{
	if( argc <= 1 ) {
		cout << "Usage: " << argv[0] << " /path/to/libxgpu.so" << endl;
		return -1;
	}
	std::fstream file;
	file.open(argv[1], std::ios::in | std::ios::out | std::ios::binary);
	file.seekg(0, std::ifstream::end);
	size_t size = file.tellg();
	cout << "File size = " << size/1000 << " KB" << endl;
	file.seekg(0, std::ifstream::beg);
	size /= sizeof(word);
	
	//cout << "File size = " << size/1000/1000 << " MB" << endl;
	
	std::vector<word> in(size);
	//std::vector<word> out(size);
	
	cout << "Reading file..." << endl;
	file.read((char*)&in[0], size*sizeof(word));
	
	//enum { MASK = (1ull << 16) - 1 };
	enum { MASK = 0xFFFFull };
	
	cout << "Converting 0x7a70 to 0x7a78..." << endl;
	size_t count = 0;
	for( size_t i=0; i<size; ++i ) {
		//if( (in[i] & MASK) == 0x707a ) {
		if( (in[i] & MASK) == 0x7a70 ) {
			//cout << "  Instruction changed" << endl;
			count += 1;
			in[i] = (in[i] & (~MASK)) | 0x7a78;
			//cout << std::hex << "0x" << ((in[i] & (~MASK)) | 0x7a78) << endl;
		}
	}
	
	cout << "Changed " << count << " instructions" << endl;
	
	cout << "Writing file..." << endl;
	file.seekp(0, std::ifstream::beg);
	file.write((char*)&in[0], size*sizeof(word));
	
	cout << "Done" << endl;
}
