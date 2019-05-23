Installation
************

Resen is built off of both python 3 and docker, so you must have both of these installed for Resen to function.

Python 3
========

Python (https://www.python.org/) is an open source, interpreted programming language that is both powerful and easily to learn. There are many ways you can install python on your system.  For new users, we recommend downloading and installing the latest Python 3 Anaconda Distribution (https://www.anaconda.com/distribution/) for your system.  This will save you the trouble of building a python distribution from scratch.

Docker
======

Follow these instructions to download and install docker for your operating system. https://docs.docker.com/v17.12/install/

Resen
=====

Install Resen by first cloning the resen GitHub repo (https://github.com/EarthCubeInGeo/resen)::

    git clone https://github.com/EarthCubeInGeo/resen.git

Change into the ``resen`` directory::

    cd resen

In a python 3 environment, use pip to install Resen::

    pip install .
