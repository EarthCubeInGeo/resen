#!/bin/bash
#######################################################################################
#
#    A helper script for installing the NASA CDF library.
#
#
#    Currently installs the CDF library from:
#
#    http://spdf.sci.gsfc.nasa.gov/pub/software/cdf/dist/
#
#######################################################################################


wget https://spdf.sci.gsfc.nasa.gov/pub/software/cdf/dist/cdf36_4/linux/cdf36_4-dist-cdf.tar.gz
tar xvf cdf36_4-dist-cdf.tar.gz
cd cdf36_4-dist
make OS=linux ENV=gnu all
make INSTALLDIR=/usr/local install
cd ..
rm -r cdf36_4-dist cdf36_4-dist-cdf.tar.gz