Resen
*****
Resen (REproducible Software ENvironment), is a tool that enables reproducible scientific data analysis, built using python and docker.  It is designed to make it easier for geospace researchers to share analysis and results, as well as build off of work others have done.  Resen was developed under the InGeO project, currently supported by the National Science Foundation's Cyberinfrastructure for Sustained Scientific Innovation (CSSI) program (Grant \#1835573).  For more information about the InGeO project, please visit the `InGeO website <https://ingeo.datatransport.org>`_.

.. image:: images/resen_concept.png

Resen is based on the concept of portable environments, or buckets, where code can be developed and run independent of a users system.  When you start a resen bucket, it has a variety of common geospace software packages preinstalled and ready for use.  This means you have easy access to common models and datasets, and can start using them in your analysis immediately.  You can also set up your bucket to access your own datasets, locally stored on your machine.

After you have completed your analysis, you can share an entire bucket with other researchers.  Within the bucket, your analysis code will always run exactly the same way, regardless of what system the bucket is on.  This means that other researchers should be able to reproduce your work and start building off of it immediately, instead of spending time configuring their system, installing new packages, and setting up file paths so their environment is compatible with your code.


Quickstart
==========

Installation
------------
Resen requires both python 3 and docker to be installed.

1. Install `Python 3 <https://www.python.org/>`_
2. Install `docker <https://docs.docker.com/install/>`_
3. Install Resen with pip ``pip install resen``

Please refer to the `installation documentation <https://resen.readthedocs.io/en/latest/installation/index.html>`_ for more detailed instructions.

Usage
-----
Resen is a command line tool.  To start resen, simply enter ``resen`` at a command prompt::

	$ resen

For a list of available commands, use the ``help`` command::

	[resen] >>> help

`Resen Workflow Example <https://resen.readthedocs.io/en/latest/usage.html#resen-workflow>`_

Documentation
=============
Complete documentation for Resen is available at https://resen.readthedocs.io/.
