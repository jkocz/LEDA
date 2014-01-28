
#include <iostream>
using std::cout;
using std::cerr;
using std::endl;
#include <stdexcept>
#include <cstdio>
#include <cstdlib>

#include <cstring>       // For strerror
#include <errno.h>       // For errno
#include <sys/syscall.h> // For SYS_gettid

#include "dada_dbreader.hpp"

int dada_bind_thread_to_core(int core)
{

  cpu_set_t set;
  pid_t tpid;

  CPU_ZERO(&set);
  CPU_SET(core, &set);
  tpid = syscall(SYS_gettid);

  if (sched_setaffinity(tpid, sizeof(cpu_set_t), &set) < 0) {
    fprintf(stderr, "failed to set cpu affinity: %s", strerror(errno));
    return -1;
  }

  CPU_ZERO(&set);
  if ( sched_getaffinity(tpid, sizeof(cpu_set_t), &set) < 0 ) {
    fprintf(stderr, "failed to get cpu affinity: %s", strerror(errno));
    return -1;
  }

  return 0;
}

class leda_dbpost : public dada_dbreader {
	FILE* m_outpipe;
public:
	leda_dbpost(multilog_t* log, int verbose,
	            const char* args)
	            //int argc, char* argv[])
		: dada_dbreader(log, verbose), m_outpipe(0) {
		
		// Launch output process and open a pipe to it for writing
		// Note: Assumes the python script is in the CWD
		std::string cmd = "python leda_dbpost2.py";
		cmd += " ";
		cmd += args;
		if( verbose >= 1 ) {
			cout << "Subprocess command line: " << cmd << endl;
		}
		m_outpipe = popen(cmd.c_str(), "w");
		if( !m_outpipe ) {
			throw std::runtime_error("Failed to open output pipe");
		}
	}
	virtual ~leda_dbpost() {
		// Wait for pipe to exit
		int pipe_status = pclose(m_outpipe);
		// Check exit status
		if( !WIFEXITED(pipe_status) ) {
			cout << "ERROR when closing output pipe" << endl;
		}
	}
	//virtual void     onConnect(key_t out_key) {}
	//virtual void     onDisconnect() {}
	// Return desired no. bytes per data read
	virtual uint64_t readHeader(uint64_t header_size, const char* header_in) {
		// Write header to output pipe
		// Note: This is assumed by the reader to be the first thing written
		size_t nbytes = fwrite(header_in, sizeof(char), header_size, m_outpipe);
		if( nbytes != header_size*sizeof(char) ) {
			throw std::runtime_error("Failed to write complete header to output pipe");
		}
		return this->bufsize();
	}
	// Return anything
	virtual uint64_t readData(uint64_t in_size, const char* data_in) {
		// Write data to the output pipe
		size_t nbytes = fwrite(data_in, sizeof(char), in_size, m_outpipe);
		if( nbytes != in_size*sizeof(char) ) {
			throw std::runtime_error("Failed to write complete data buffer to output pipe");
		}
		return 0;
	}
};

bool parse_arg_typed(int& x)                { return sscanf(optarg, "%i", &x) == 1; }
bool parse_arg_typed(unsigned& x)           { return sscanf(optarg, "%u", &x) == 1; }
bool parse_arg_typed(long long& x)          { return sscanf(optarg, "%lli", &x) == 1; }
bool parse_arg_typed(unsigned long long& x) { return sscanf(optarg, "%llu", &x) == 1; }
bool parse_arg_typed(float& x)              { return sscanf(optarg, "%f", &x) == 1; }
bool parse_arg_typed(std::string& x)        { x = optarg; return true; }
template<typename T>
bool parse_arg(char c, T& x) {
	if( !optarg ) {
		cerr << "ERROR: -" << c << " flag requires an argument" << endl;
		return false;
	}
	else if( !parse_arg_typed(x) ) {
		cerr << "ERROR: Could not parse -" << c << " " << optarg << endl;
		return false;
	}
	else {
		return true;
	}
}

void print_usage() {
	cout <<
		"leda_dbpost_adapter [options] -- in_key\n"
		" -a \"args for leda_dbpost2.py\" (note: must use quotes)\n"
		" See leda_dbpost2.py usage!\n"
		" -c core      Bind process to CPU core\n"
		" -v           Increase verbosity\n"
		" -q           Decrease verbosity\n"
		" -h           Print usage\n" << endl;
}

int main(int argc, char* argv[])
{
	int         verbose = 0;
	int         core    = -1;
	key_t       in_key  = 0;
	multilog_t* log     = 0;
	std::string fwd_args;
	int req_args = 1;
	
	int arg = 0;
	while( (arg = getopt(argc,argv,"a:c:hvq")) != -1 ) {
		switch( arg ) {
		case 'a': if( !parse_arg('a', fwd_args) ) return -1; break;
		case 'c': if( !parse_arg('c', core) ) return -1; break;
		case 'h': print_usage(); return 0;
		case 'v': ++verbose; break;
		case 'q': --verbose; break;
		default: cerr << "WARNING: Unexpected flag -" << arg << endl; break;
		}
	}
	int num_args = argc - optind;
	if( num_args != req_args ) {
		cerr << "ERROR: Expected exactly "
		     << req_args
		     << " required arg, got " << num_args << endl;
		print_usage();
		return -1;
	}
	unsigned int tmp;
	if( sscanf(argv[optind+0], "%x", &tmp) != 1 ) {
		cerr << "ERROR: Could not parse buffer key from "
		     << argv[optind+0] << endl;
		return -1;
	}
	in_key = tmp;
	if( verbose >= 1 ) {
		cout << "Input dada buffer key: " << std::hex << in_key << std::dec << endl;
	}
	
	log = multilog_open("dbpost_adapter", 0);
	multilog_add(log, stderr);
	
	if( core >= 0 ) {
		if( dada_bind_thread_to_core(core) < 0 ) {
			cerr << "WARNING: Failed to bind to core " << core << endl;
		}
		if( verbose >= 1 ) {
			cout << "Parent process bound to core " << core << endl;
		}
	}
	
	leda_dbpost ctx(log, verbose, fwd_args.c_str());
	ctx.connect(in_key);
	ctx.run();
	ctx.disconnect();
	
	return 0;
}

