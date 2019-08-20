Gerneral Instructions
*********************

Resen is built off of both python 3 and docker, so you must have both of these installed for Resen to function.

Python 3
========

Python (https://www.python.org/) is an open source, interpreted programming language that is both powerful and easily to learn. There are many ways you can install python on your system.  For new users, we recommend downloading and installing the latest Python 3 Anaconda Distribution (https://www.anaconda.com/distribution/) for your system.  This will save you the trouble of building a python distribution from scratch.

Docker
======

Docker CE is the recomended version of Docker to use with Resen.  `Installation instructions <https://docs.docker.com/install/>`_ can be found in the docker documentation.  Please read installation instructions carefully! For convenience, some OS specific links are provided below:

| **MacOS**: `Install Docker Desktop for Mac <https://docs.docker.com/docker-for-mac/install/>`_
| Important! Docker Desktop is only for MacOS 10.10 Yosemite and later.  Earlier versions of MacOS should install `Docker Toolbox <https://docs.docker.com/toolbox/toolbox_install_mac/>`_.

| **Windows**: `Install Docker Desktop for Windows <https://docs.docker.com/docker-for-windows/install/>`_
| Important! If you are already using virtualbox, do NOT install Docker Desktop.  Instead, install `Docker Toolbox <https://docs.docker.com/toolbox/toolbox_install_windows/>`_.

**CentOS**: `Get Docker CE for CentOS <https://docs.docker.com/install/linux/docker-ce/centos/>`_

**Debian**: `Get Docker CE for Debian <https://docs.docker.com/install/linux/docker-ce/debian/>`_

**Fedora**: `Get Docker CE for Fedora <https://docs.docker.com/install/linux/docker-ce/fedora/>`_

**Ubuntu**: `Get Docker CE for Ubuntu <https://docs.docker.com/install/linux/docker-ce/ubuntu/>`_


Resen
=====

Install Resen by first cloning the resen GitHub repo (https://github.com/EarthCubeInGeo/resen)::

    git clone https://github.com/EarthCubeInGeo/resen.git

Change into the ``resen`` directory::

    cd resen

In a python 3 environment, use pip to install Resen::

    pip install .