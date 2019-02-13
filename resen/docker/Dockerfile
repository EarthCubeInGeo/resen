FROM jupyter/scipy-notebook

MAINTAINER "Todd Valentic" <todd.valentic@sri.com>

# Create cache directories 

USER $NB_USER 

ENV BUILD $HOME/build
ENV MPLBACKEND Agg

RUN mkdir -p $HOME/cache/omni && \
    mkdir -p $HOME/cache/ssies && \
    mkdir -p $HOME/examples && \
    mkdir -p $BUILD 

WORKDIR /home/$NB_USER/build 

USER root

# Install development packages 

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    mpich \
    gfortran \
    libhdf5-serial-dev \
    libfreetype6-dev \
    libpng-dev \
    libffi-dev \
    libssl-dev \
    libnetcdf-dev \
    ncurses-dev \
    g++

# Install NASA CDF
# old: http://spdf.sci.gsfc.nasa.gov/pub/software/cdf/dist/cdf36_3_1/linux/cdf36_3_1-dist-cdf.tar.gz
RUN /bin/bash -c 'wget https://spdf.sci.gsfc.nasa.gov/pub/software/cdf/dist/cdf36_4/linux/cdf36_4-dist-cdf.tar.gz && \
    tar xvf cdf36_4-dist-cdf.tar.gz && \
    cd cdf36_4-dist && \
    make OS=linux ENV=gnu all && \
    make INSTALLDIR=/usr/local install && \
    cd .. && \
    rm -r cdf36_4-dist cdf36_4-dist-cdf.tar.gz'

RUN rm /home/jovyan/.wget-hsts

COPY resources/cdf.sh /etc/profile.d
COPY resources/geospacepy_config.py /tmp
COPY resources/start-singleuser-ingeo.sh /usr/local/bin
COPY resources/nbstripout /usr/local/bin

RUN chown $NB_USER:$NBUSER /tmp/geospacepy_config.py 

USER $NB_USER

RUN conda create --quiet --yes -n python2 \
    'paramiko=1.17.2' \
    'pymongo=3.2.2' \
    'mechanize=0.2.5' \
    'netcdf4=1.2.7' \
    'cryptography=1.7.1' \
    'pytest=3.0.5' \
    'nbformat=4.4.0' \
    'basemap=1.2.0' && \
    conda remove --quiet --yes -n python2 --force qt pyqt && \
    conda clean -tipsy

# Install davitpy and spacepy

RUN /bin/bash -c 'git clone https://github.com/vtsuperdarn/davitpy.git && \
    cd davitpy && \
    git pull origin 0.8-master && \
    source /opt/conda/bin/activate python2 && \
    python setup.py install'

# Install spacepy

RUN /bin/bash -c 'source /opt/conda/bin/activate python2 && \
    source /etc/profile.d/cdf.sh && \
    pip install spacepy'
    # && \
    #python -c "import spacepy.toolbox; spacepy.toolbox.update()"'

# Install amiepy
#https://bitbucket.org/amienext/

RUN /bin/bash -c 'source activate python2 && \
    git clone https://bitbucket.org/amienext/geospacepy-lite.git && \
    cd geospacepy-lite && \
    mv /tmp/geospacepy_config.py geospacepy && \
    python setup.py install'
 
RUN /bin/bash -c 'source activate python2 && \
    git clone https://bitbucket.org/amienext/ovationpyme.git && \
    cd ovationpyme && \
    python setup.py install'
  
# RUN /bin/bash -c 'source activate python2 && \
#     git clone https://github.com/lkilcommons/apex-python.git && \
#     cd apex-python && \
#     python setup.py install'
      
RUN /bin/bash -c 'source activate python2 && \
    git clone https://github.com/lkilcommons/igrfpy.git && \
    cd igrfpy && \
    python setup.py install'
    
RUN /bin/bash -c 'source activate python2 && \
    git clone https://bitbucket.org/amienext/just_sam.git && \
    cd just_sam && \
    python setup.py install'

# RUN /bin/bash -c 'source activate python2 && \
#    git clone https://bitbucket.org/lkilcommons/amiepy.git && \
#    cd amiepy && \
#    sed /package_dir/s/AmiePy/AmiePy/ < setup.py > setup.py.new && \
#    mv setup.py.new setup.py && \
#    sed -e "/package_data/s.\[.\[\"tables/test_amie_obs/*\",." < setup.py > setup.py.new && \
#    mv setup.py.new setup.py && \
#    python setup.py install && \
#    nbstripout AmiePyDemo.ipynb && \
#    sed -e "s/from AmiePy/from amiepy/g" < AmiePyDemo.ipynb > tmp && \
#    mv tmp AmiePyDemo.ipynb && \
#    sed -e "s|/home/liamk/Desktop/||g" < AmiePyDemo.ipynb > tmp && \
#    mv tmp AmiePyDemo.ipynb && \
#    cp AmiePyDemo.ipynb $HOME/examples'

#
# Cleanup 

RUN rm -r $BUILD

WORKDIR /home/$NB_USER/work

#################
# asreimer: stuff to get gdrivefs working
# need to add the "Mounting Google Drive" notebook?
#
# USER root
#
# RUN apt-get install libfuse2 fuse
#
# USER $NB_USER
#
#COPY resources/MountingGoogleDrive.ipynb /home/$NB_USER/examples
#COPY resources/ExternalStorage.tar.gz /home/$NB_USER/work
#RUN tar -zxf ExternalStorage.tar.gz
#
#RUN /bin/bash -c 'source activate python2 && \
#    pip install oauth2client google-api-python-client && \
#    git clone https://github.com/dsoprea/GDriveFS && \
#    cd GDriveFS && \
#    git reset --hard 184dbfa6e94b210d47f4ef867134f02dde33fbbe && \
#    pip install . && \
#    cd .. && \
#    rm -rf GDriveFS'
#
#############
# ExternalStorage python package and example notebook
#
#RUN /bin/bash -c 'source activate python2 && \
#    pip install ./ExternalStorage --no-deps'
#
#RUN /bin/bash -c 'source activate python2 && pip install -U six'
#
#RUN rm -r /home/$NB_USER/work/ExternalStorage /home/$NB_USER/work/ExternalStorage.tar.gz

#############
# DataFetcher python package and example notebook

COPY resources/FetchingDataFromManifest.ipynb /home/$NB_USER/examples
COPY resources/test_manifest.json /home/$NB_USER/examples
COPY resources/FetchData.tar.gz /home/$NB_USER/work
RUN tar -zxf FetchData.tar.gz

RUN /bin/bash -c 'source activate python2 && \
    pip install ./FetchData --no-deps'

RUN /bin/bash -c 'source activate python2 && \
    pip install pandas'
RUN /bin/bash -c 'source activate python2 && \
    pip install -U numpy'

RUN rm -r /home/$NB_USER/work/FetchData /home/$NB_USER/work/FetchData.tar.gz

#############
# Russel's data gridder
#
#USER root
#RUN apt-get install ffmpeg
#
#USER $NB_USER
#
#RUN /bin/bash -c 'source activate python2 && \
#    pip install scikit-image h5py pyfits'

#COPY russel_gridding/data_gridding.tar.gz /home/$NB_USER/work
#COPY russel_gridding/geomag.tar.gz /home/$NB_USER/work
#RUN tar -zxf data_gridding.tar.gz
#RUN tar -zxf geomag.tar.gz
#RUN mv data_gridding /home/$NB_USER/examples
#
#RUN /bin/bash -c 'source activate python2 && \
#    pip install ./geomag --no-deps'
#
#RUN rm -r /home/$NB_USER/work/data_gridding.tar.gz /home/$NB_USER/work/geomag.tar.gz /home/$NB_USER/work/geomag

############
# Sciunit installation

USER $NB_USER 

RUN /bin/bash -c 'source activate python2 && \
    pip install -U sciunit2'

RUN /bin/bash -c 'source activate python2 && \
    conda install -y -c anaconda bsddb'


############
# Install some other python packages
# cartopy: https://scitools.org.uk/cartopy/docs/latest/installing.html#installing

RUN /bin/bash -c 'source activate python2 && \
    conda install cartopy=0.17.0'

RUN /bin/bash -c 'source activate python2 && \
    pip install apexpy==1.0.3'

# Import spacepy once so that we get the .spacepy directory created
RUN /bin/bash -c 'source activate python2 && \
    python -c "import spacepy"'

# Needed for password-less login on jupyterhub when running locally.
RUN pip install jupyterhub-dummyauthenticator

# to run the jupyter lab
RUN pip install jupyterlab
RUN conda install -c conda-forge ipympl --yes
RUN conda install -c conda-forge widgetsnbextension --yes
RUN conda install nodejs --yes
RUN jupyter labextension install @jupyter-widgets/jupyterlab-manager
RUN jupyter labextension install jupyter-matplotlib

