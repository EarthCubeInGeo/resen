Installing on Windows
*********************

Resen requires both python 3 and docker to function. Here we provide a basic guide for installing both python 3 and docker. We have tested this procedure and know it works. Python 3 and Resen are easy to install. Docker is also fairly easy, but there are some subtle details that need to be emphasized for a smooth installation process.

Install Anaconda and Resen
==========================

**Anaconda**:
We recommend downloading and installing the Python 3 Anaconda Distribution (https://www.anaconda.com/distribution/). This simplifies the installation and usage of several common software tools needed to install and run Resen.

**Resen**:
Using the start menu search, open the "Anaconda Powershell Prompt" and navigate to a directory where you wish to host the Resen source code. Next, install Resen by first cloning the resen GitHub repo (https://github.com/EarthCubeInGeo/resen)::

    git clone https://github.com/EarthCubeInGeo/resen.git

Change into the ``resen`` directory::

    cd resen

Finally, install Resen::

    pip install .

Once complete, this will provide the command line command ``resen``. Next, we need to install Docker.



Docker
======

For Windows, there are 2 options for installing Docker, which depends on what else you use and do with your Windows system::

1. `Docker Desktop for Windows <https://docs.docker.com/docker-for-windows/install/>`_

2. `Docker Toolbox <https://docs.docker.com/toolbox/toolbox_install_windows/>`_

If you use `Oracle VM VirtualBox <https://www.virtualbox.org/>`_ to run virtual machines on your Windows system, DO NOT install Docker Desktop. You must instead install Docker Toolbox. Docker Desktop uses Hyper-V, which is not compatible with VirtualBox.

**Docker Desktop**
TODO. If you can help fill this in, please make a PR to the develop branch for resen!

**Docker Toolbox**
Docker Toolbox essentially works by running docker inside of a Linux virtual machine using VirtualBox. The VM that gets installed is name "default" and we will refer to this "default" Docker virtual machine as the "Docker VM". To install it Docker Toolbox, do the following:

1. Shutdown any VirtualBox VMs that you currently have running and take note of the VirtualBox version you have installed. Docker Desktop installs an older version of VirtualBox on your system, but this version you are currently running can be upgraded back to the version you are currently running.

2. `Follow the instructions on here to install Docker Toolbox <https://docs.docker.com/toolbox/toolbox_install_windows/>`_. Once installed, restart your computer and then run the ``Docker Quickstart Terminal`` from the start menu. ``TODO: insert screenshot``

3. Now we need to add port forwarding and check the shared folders for the Docker VM in VirtualBox. To do this, open VirtualBox and open the "Settings" for the "default" VM, like so:

``TODO: insert screenshot``

Add a new port forwarding rule by navigating to Settings->Network->Adapter 1->Advanced->Port Forwarding:

``TODO: insert screenshot``

Here, we need to add a port forwarding rule for each bucket we create in Resen. Resen requires port 9000 for one bucket and then increments by 1 for every new bucket created. This means that if you have 5 buckets, you will need to make a port forward rule for ports 9000, 9001, 9002, 9003, and 9004. Change both the Host and Guest Ports as seen in the above screenshot.

Now we can optionally add Shared Folders. By default, Docker Toolbox shares the ``C:\Users`` directory with the Docker VM at ``/c/Users``. This means that directories in ``C:\Users`` will be available to mount into a Resen bucket via the ``/c/Users`` Shared Folder in VirtualBox. If additional shared directory locations are desired add them. For example:

``TODO: insert screenshot``

makes an additional location, ``D:\ashto`` available to the Docker VM at the location ``/d/ashto`` so that any directories in ``D:\ashto`` can be mounted into a resen bucket via ``/d/ashto``. After adding or removing Shared Folders, you must restart the Docker VM. This can be done by running:

	docker-machine restart

in the "Docker Quickstart Terminal".

4. Optionally, you can now re-install the newer verions of VirtualBox that you had previously installed. Before doing this, shutdown the Docker Toolbox VM. After re-installing VirtualBox, restart your computer and then open the "Docker Quickstart Terminal" again.

**Running Resen**

Now you can run Resen! To do this, open an "Anaconda Powershell Prompt" and type "resen" and hit enter! You should see something similar to:

``TODO: insert screenshot``