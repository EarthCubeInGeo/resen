Resen
*****
Resen (REproducible Software ENvironment), is a tool that enables reproducible scientific data analysis, built using python and docker.  It is designed to make it easier for geospace researchers to share analysis and results, as well as build off of work others have done.  Resen was developed under the InGeO project, currently supported by the National Science Foundation's Cyberinfrastructure for Sustained Scientific Innovation (CSSI) program (Grant \#1835573).  For more information about the InGeO project, please visit the `InGeO website <https://ingeo.datatransport.org>`_.

Quickstart
==========

Installation
------------
Resen requires both python 3 and docker to be installed.

1. Install `Python 3 <https://www.python.org/>`_
2. Install `docker <https://docs.docker.com/v17.12/install/>`_
3. Clone the `resen <https://github.com/EarthCubeInGeo/resen>`_ git repository and install with ``pip install .``

More detailed installation instructions are available in the `Resen documentation <https://resen.readthedocs.io/en/readthedocs/installation.html>`_.

Usage
-----
Resen is a command line tool.  To start resen, simply enter ``resen`` at a command prompt::

	$ resen

For a list of available commands, use the ``help`` command::

	[resen] >>> help

Documentation
=============
Complete documentation for Resen is available at https://resen.readthedocs.io/.
