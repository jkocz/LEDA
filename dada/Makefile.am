


lib_LTLIBRARIES = libleda.la

leda_hdr = leda_udp.h leda_def.h

libleda_la_SOURCES = $(leda_hdr) leda_udp.c

bin_PROGRAMS = leda_udpdb leda_udptest leda_udptest_paper leda_udpdb_thread leda_dbupdb_lookup leda_udpNdb_thread leda_udpNdb_paper leda_dbupdb_paper

LDADD = libleda.la $(top_builddir)/src/libpsrdada.la
INCLUDES = -I$(top_srcdir)/src

if HAVE_IPP

bin_PROGRAMS += leda_dbupdb_ipp
AM_CFLAGS = $(IPP_CFLAGS)
LDADD += $(IPP_LIBS)

endif


#############################################################################
#
# Depends on 3rd Party Timers
#
#############################################################################

if COMPILE_THIRD

bin_PROGRAMS += leda_udpgen

leda_udpgen_CFLAGS = -D$(ARCH)
INCLUDES += -I$(top_srcdir)/3rdparty
LDADD += $(top_builddir)/3rdparty/libtimers.la

endif

