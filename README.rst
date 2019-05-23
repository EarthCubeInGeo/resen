Resen
*****
Resen (REproducible Software ENvironment), is a tool that enables reproducible scientific data analysis, built using python and docker.  It is designed to make it easier for geospace researchers to share analysis and results, as well as build off of work others have done.  Resen was developed under the InGeO project, currently supported by the National Science Foundation's Cyberinfrastructure for Sustained Scientific Innovation (CSSI) program (Grant \#1835573).  For more information about the InGeO project, please visit the `InGeO website <https://ingeo.datatransport.org>`_.

Resen is based on the concept of portable environments, or buckets, where code can be developed and run independent of a users system.  If two buckets are set up the same way on two different systems, code should run identically in both of them.  This helps users share code and reproduce results much more easily without worrying about different environments, package installation, and file paths.

Additionally, Resen buckets have many common geospace packages preinstalled and ready to use.  In a resen bucket, users can immediately start using these packages to produce results without having to download, install, and configure them on their own system.

Quickstart
==========

Installation
------------
Resen requires both python 3 and docker to be installed.

1. Install `Python 3 <https://www.python.org/>`_
2. Install `docker <https://docs.docker.com/v17.12/install/>`_
3. Clone the `resen <https://github.com/EarthCubeInGeo/resen>`_ git repository and install with ``pip install .``

More detailed installation instructions are available `here <https://resen.readthedocs.io/en/readthedocs/installation.html>`_.

Usage
-----
Resen is a command line tool.  To start resen, simply enter ``resen`` at a command prompt::

	$ resen

For a list of available commands, use the ``help`` command::

	[resen] >>> help

Documentation
=============
Complete documentation for Resen is available at https://resen.readthedocs.io/.
