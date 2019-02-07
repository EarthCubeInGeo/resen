# Building and Running the Reproducible Software Environment (ReSEn) Container

The Reproducible Software Environment (ReSEn) is a toolkit of preinstalled data analysis tools that enables reproducibility of scientific analysis in two ways:
1) Facilitating usage of a variety of commonly used community analysis tools, and
2) Providing tools to create a static, standardized, and citable analysis environment at publication time.

ReSEn leverages existing stardized software units, known as "containers", implemented via Docker. ReSEn provides access to pre-built docker containers that facilitate data analysis. ReSEn also provides tools for building a static container of a completed analysis, which can then be uploaded to Zenodo and cited in a publication.


## ReSEn Containers
The ReSEn containers are currently under development.

Python software is provided using Anaconda.

## ReSEn Publication Tools
The ReSEn publication tools are currently under development.


# Running ReSEn Locally

This requires docker to be installed.

## Install Docker

Docker maintains excellent instruction for installing on Linux, MacOS, and Windows. Please follow the installation instructions here: https://docs.docker.com/install/

# Development Notes and Instructions

This requires docker to be installed. The base docker image that we build ours on top of is jupyter/scipy-notebook which is built on top of an Ubuntu 18.04 container. Specifically:

Ubuntu 18.04 (bionic) from 2018-05-26
https://github.com/docker-library/official-images/commit/aac6a45b9eb2bffb8102353c350d341a410fb169
See: https://github.com/jupyter/docker-stacks/blob/master/base-notebook/Dockerfile

It might be advantageous to spool up an Ubuntu 18.04 VM to do some testing while installing packages and working with conda. Alternatively, one can use the docker image itself for doing this testing.

## Conda Development Environment

Install the miniconda environment: https://docs.conda.io/projects/continuumio-conda/en/latest/user-guide/install/macos.html

In linux:

    wget https://repo.continuum.io/miniconda/Miniconda3-3.7.0-Linux-x86_64.sh -O ~/miniconda.sh
    bash ~/miniconda.sh -b -p $HOME/miniconda
    export PATH="$HOME/miniconda/bin:$PATH"


## Building the ReSEn container

Building the ReSEn container locally requires docker to be installed and the docker service must be running.

On linux:

check status of docker service:

    sudo systemctl status docker

start the service:

    sudo systemctl start docker

Navigate to resen/docker, which is the location where the Dockerfile is and run:

    sudo docker build -t resen/testing .

This will build an image. This can take some time.

## Running the image in a container

    sudo docker run -p 8000:8000 --name testing resen/testing bash

This creates an instance of the "resen/testing" docker image in a container called "testing". It forwards port 8000 inside the container to port 8000 outside of the container. Finally, it runs the command "bash" inside the container. For starting jupyterhub, see below.

To stop this container you can use:

    sudo docker stop testing

and then to get rid of it:

    sudo docker rm testing

noting that this doesn't delete the resen/testing image, but only the container "testing", which you can easily create again. You can look at all running docker containers with:

    sudo docker ps

You can execute a root bash shell in the instance of "resen/testing" that is running with the name "testing" like so:

    sudo docker exec --user root -it testing /bin/bash

which allows you to set a password for the user "jovyan", allowing you to log in to jupyterhub:

    passwd jovyan

Finally, in a browser, navigate to localhost:8000 and log in with jovyan and the password you just set.

If you want to mount in your own notebooks/scripts for testing, then we can run the following (the :Z is needed for systems with SELinux):

    sudo docker run -p 8000:8000 -v "$(pwd)"/testing:/home/jovyan/testing:ro,Z --name testing resen/testing jupyterhub -f /home/jovyan/testing/config/testing_jupyterhub_config.py

If you want to just run a notebook server, you can do so with:

     sudo docker run -p 8000:8000 resen/testing start-notebook.sh --port 8000

and note the token that is printed to the terminal, since you need this to log in. If you want to mount in persistent storage, you can do soe with the `-v` switch like above.

### Helpful Resources

* 
* JupyterHub Authentication: https://github.com/jupyterhub/jupyterhub/blob/master/docs/source/getting-started/authenticators-users-basics.md
    * Dummy Authenticator: https://github.com/jupyterhub/dummyauthenticator
