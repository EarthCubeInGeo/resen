Windows Gotchas
***************

Resen requires both python 3 and docker to function. Here we provide a basic guide for installing both python 3 and docker. We have tested this procedure and know it works. Python 3 and Resen are easy to install. Docker is also fairly easy, but there are some subtle details that need to be emphasized for a smooth installation process.

Install Anaconda and Resen
==========================

**Anaconda**:
We recommend downloading and installing the Python 3 Anaconda Distribution (https://www.anaconda.com/distribution/). This simplifies the installation and usage of several common software tools needed to install and run Resen.

**Resen**:
Using the start menu search, open the "Anaconda Powershell Prompt" and install Resen using ``pip``::

    pip install git+https://github.com/EarthCubeInGeo/resen.git@v2019.1.1

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

.. image:: images/vbox.png

Add a new port forwarding rule by navigating to Settings->Network->Adapter 1->Advanced->Port Forwarding:

.. image:: images/port_forward.png

Here, we need to add a port forwarding rule for each bucket we create in Resen. Resen requires port 9000 for one bucket and then increments by 1 for every new bucket created. This means that if you have 5 buckets, you will need to make a port forward rule for ports 9000, 9001, 9002, 9003, and 9004. Change both the Host and Guest Ports as seen in the above screenshot.

Now we can optionally add Shared Folders. By default, Docker Toolbox shares the ``C:\Users`` directory with the Docker VM at ``/c/Users``. If additional shared directory locations are desired add them. For example:

.. image:: images/shared_folder.png
.. image:: images/add_shared_folder.png

makes an additional location, ``D:\ashto`` available to the Docker VM at the location ``/d/ashto``.  After adding or removing Shared Folders, you must restart the Docker VM. This can be done by running:

	docker-machine restart

in the "Docker Quickstart Terminal".

4. Optionally, you can now re-install the newer verions of VirtualBox that you had previously installed. Before doing this, shutdown the Docker Toolbox VM. After re-installing VirtualBox, restart your computer and then open the "Docker Quickstart Terminal" again.

**Running Resen**

Now you can run Resen! To do this, open an "Anaconda Powershell Prompt" and type "resen" and hit enter. A prompt should appear that asks if you are using Docker Toolbox::

  Resen appears to be running on a Windows system.  Are you using Docker Toolbox? (y/n):

If you installed Docker Desktop for Windows, enter ``n``.  If you set up Docker Toolbox as described above enter ``y``.  If you respond ``y``, you will be asked to specify the mapping between shared folders on the host machine and the Docker VM.  This is referring to the Shared Folders set up in step 3 above.  If you did not modify the default shared folder, the correct response should be::

  Please specify the mapping between shared folders on the host machine and the Docker VM.
  Host machine path: C:\Users
  Docker VM path: /c/Users

This will be different if you have made a different location available to the Docker VM, such as ``D:\ashto`` as described above.  In this case, the correct response will be::

  Please specify the mapping between shared folders on the host machine and the Docker VM.
  Host machine path: D:\ashto
  Docker VM path: /d/ashto

Now Resen should be configured and ready to go!  You should see something similar to:

.. image:: images/resen_cmd.png
