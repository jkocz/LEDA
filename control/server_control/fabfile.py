from fabric.api import *
from leda_config import server_config
#from fabric.contrib.console import confirm

# HOST SSH SETUP CONFIG
env.hosts = server_config.server_list
env.user  = server_config.server_user

def runcmd(cmd):
    """ Run a simple command on the server cluster """
    run(cmd)

def purge_data1():
    """ Purge data from data1 """
    with warn_only():
        run('rm -v /data1/one/*.dada')
        run('rm -v /data1/one/*.h5')
        run('rm -v /data1/two/*.dada')
        run('rm -v /data1/two/*.h5')

def convert_dada():
    """ Convert dada files to HDF5 """
    run('dada2hdf/dada2hdf_dir.py -v 2 /data1/one/')
    run('dada2hdf/dada2hdf_dir.py -v 2 /data1/two/')

def dada2hdf_install():
    put('install/dada2hdf.tar.gz', '/home/leda/install')
    run('rm -rf /home/leda/dada2hdf')
    run('cd ~/install && tar -xf dada2hdf.tar.gz')
    run('mv ~/install/dada2hdf ~/')

def fits2hdf_install():
    put('install/fits2hdf.tar.gz', '/home/leda/install')
    run('cd ~/install && tar -xf fits2hdf.tar.gz')
    sudo('cd ~/install/fits2hdf && python setup.py install')

def apt_install(package_name):
    """" Install a package via apt-get """
    sudo('apt-get install %s -y' % package_name)

def pip_install(package_name):
    """ Install a PIP package """
    sudo('pip install %s' % package_name)

def setup_python_env():
    """ Setup the python environment """
    sudo('apt-get remove python-setuptools -y')
    run('wget https://bootstrap.pypa.io/get-pip.py')
    sudo('python get-pip.py')

def setup_hdf5():
    """" Install HDF5 on servers """

    # Copy files over
    run('mkdir -p /home/leda/install')
    put('install/szip-2.1.tar.gz', '/home/leda/install')
    put('install/hdf5-1.8.14.tar.gz', '/home/leda/install')
    put('install/bitshuffle.tar.gz', '/home/leda/install')
    put('install/h5py-2.4.0b1.tar.gz', '/home/leda/install')

    sudo('rm -rf /home/leda/install/h5py-2.4.0b1')
    sudo('rm -rf /home/leda/install/bitshuffle')

    run('cd /home/leda/install && tar -xf szip-2.1.tar.gz')
    run('cd /home/leda/install && tar -xf hdf5-1.8.14.tar.gz')
    run('cd /home/leda/install && tar -xf bitshuffle.tar.gz')
    run('cd /home/leda/install && tar -xf h5py-2.4.0b1.tar.gz')

    # Install szip
    run('cd /home/leda/install/szip-2.1 && ./configure --prefix=/usr/local \
        && make clean && make')
    sudo('cd /home/leda/install/szip-2.1 && make install')

    # Install HDF5
    sudo('apt-get remove libhdf5-serial-dev libhdf5-serial-1.8.4 -y')
    run('cd /home/leda/install/hdf5-1.8.14 && ./configure --enable-fortran \
         --enable-cxx --with-szlib=/usr/local --prefix=/usr/local \
        && make clean && make')
    sudo('cd /home/leda/install/hdf5-1.8.14 && make install')

    # Reinstall h5py
    #sudo('apt-get remove python-h5py -y')
    #sudo('pip uninstall h5py -y')
    sudo('cd /home/leda/install/h5py-2.4.0b1 \
         && python setup.py configure -r \
         --hdf5=/usr/local --hdf5-version=1.8.14')
    sudo('cd /home/leda/install/h5py-2.4.0b1 && python setup.py install')

    # Install bitshuffle
    with warn_only():
        sudo('cd /home/leda/install/bitshuffle \
             && python setup.py install --h5plugin')
