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


## Building the ReSEn container

Building the ReSEn container locally requires docker to be installed and the docker service must be running.

On linux:

check status of docker service:

    sudo systemctl status docker

start the service:

    sudo systemctl start docker

Navigate to resen/docker, which is the location where the Dockerfile is and run:

    sudo docker build -t resen/testing .

This can take some time. Make note of the container id.

## Running the container

sudo docker run -p 8000:8000 resen/testing jupyterhub
