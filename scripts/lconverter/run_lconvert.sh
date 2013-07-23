#! /usr/bin/env bash

# Usage: ./lconvert [options]
# 
# Options:
# 
#   -V, --version                 output program version
#   -h, --help                    output help information
#   -v, --verbose                 enable verbose info
#   -s, --silent                  set silent (no print to stdout)
#   -A, --autosonly               Only output autocorrelations (.LA)
#   -i, --input <arg>             input filename
#   -o, --output <arg>            output filename root
#   -n, --numchans [arg]          Number of channels to read (defaults to 600)
#   -f, --startchan [arg]         First channel (defaults to 0)
#   -t, --accperfile [arg]        Number of accumulations per file
#   -T, --acctoread [arg]         Number of accumulations from input file to read


./lconvert -i testdata/test.dada -o testdata/test_output -f 100 -n 10 -t 101 -A $1