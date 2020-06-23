Usage
*****

To use resen, simply enter ``resen`` at the command line::

    $ resen

This will open the resen tool::

        ___ ___ ___ ___ _  _
       | _ \ __/ __| __| \| |
       |   / _|\__ \ _|| .` |
       |_|_\___|___/___|_|\_|

    Resen 2020.1.0 -- Reproducible Software Environment

    [resen] >>>

Type ``help`` to see available commands::

    [resen] >>> help

This will produce a list of resen commands you will use to manage your resen buckets::

    Documented commands (type help <topic>):
    ========================================
    EOF     exit    help    list  remove  status
    create  export  import  quit  start   stop 

To get more information about a specific command, enter ``help <command>``.

Resen Workflow
==============

To create, import, export, and remove buckets, we use Resen. Buckets are portable, system independent environments where code can be developed and run. Buckets can be shared between Windows, Linux, and macos systems and all analysis within the bucket will be run exactly the same. Resen buckets come preinstalled with a variety of common geospace software that can be used immediately in analysis.

The interface to a resen bucket is a jupyter lab server and access to the bucket is provided through a web browser. The user home directory is ``/home/jovyan``. Any mounted storage directories are available in ``mount``.

Below are instructions on how to use Resen to work with buckets. A typical workflow will involve: creation of a bucket, performing scientific data analysis inside the bucket, exporting the bucket and sharing it with colleagues. Collaborators can then import the bucket, perform additional analysis, and then export the bucket for publication in an open access citable repository, such as `Zenodo <https://zenodo.org/>`_.

Setup a New Bucket
------------------

1. Creating a new bucket is performed with the command::

     [resen] >>> create

   The ``create`` command queries the user for several pieces of information required to create a bucket. First it asks for the bucket name. Creating a bucket named ``amber``::

     Please enter a name for your bucket.
     Valid names may not contain spaces and must start with a letter and be less than 20 characters long.``
     >>> Enter bucket name: amber

   Next, the user is asked to specify the version of resen-core to use::

     Please choose a version of resen-core.
     Available versions: 2019.1.0, 2020.1.0
     >>> Select a version: 2020.1.0

   Optionally, one may then specify a local directory to mount into the bucket at ``/home/jovyan/mount``::

     Local directories can be mounted to either /home/jovyan/work or /home/jovyan/mount/ in
     a bucket. The /home/jovyan/work location is a workspace and /home/jovyan/mount/ is intended
     for mounting in data. You will have rw privileges to everything mounted in work, but can
     specify permissions as either r or rw for directories in mount. Code and data created in a
     bucket can ONLY be accessed outside the bucket or after the bucket has been deleted if it is
     saved in a mounted local directory.
     >>> Mount storage to /home/jovyan/mount? (y/n): y
     >>> Enter local path: /some/local/path

   Finally, the user is asked if they want jupyterlab to be started::

     >>> Start bucket and jupyterlab? (y/n): y

   after which resen will begin creating the bucket. Example output for a new bucket named ``amber`` with jupyterlab started is::

     ...adding core...
     ...adding ports...
     ...adding mounts...
     Bucket created successfully!
     ...starting jupyterlab...
     Jupyter lab can be accessed in a browser at: http://localhost:9002/?token=e7a11fc1ea42a445807b4e24146b9908e1abff82bacbf6f2

2. Check the status of the bucket::

     [resen] >>> status amber

     amber
     =====
   
     Resen-core Version:  2020.1.0
     Status:  running
     Jupyter Token:  e7a11fc1ea42a445807b4e24146b9908e1abff82bacbf6f2
     Jupyter Port:  9002
     Jupyter lab URL: http://localhost:9002/?token=e7a11fc1ea42a445807b4e24146b9908e1abff82bacbf6f2
   
     Storage:
     Local                                   Bucket                                  Permissions
     /some/local/path                        /home/jovyan/mount/path                 rw
   
     Ports:
     Local          Bucket
     9002           9002

At this point, the bucket should have a name, an image, at least one port, and optionally one or more storage locations.  Status should be ``running`` if the user decided to have jupyterlab started, otherwise the status will be ``None``.

Work with a Bucket
------------------
1. Check what buckets are available with ``list``::

    [resen] >>> list
    Bucket Name         Docker Image             Status
    amber               2020.1.0                 running

   If a bucket is running, it will consume system resources accordingly.

2. Stop the bucket ``amber``::

    [resen] >>> stop amber

   The status of ``amber`` should now be ``exited``::

    [resen] >>> list
    Bucket Name         Docker Image             Status
    amber               2020.1.0                 exited

   The bucket will still exist and can be restarted at any time, even after quitting and restarting resen.

3. Start the bucket ``amber`` that was just stopped::

    [resen] >>> start amber

   The status of ``amber`` should now be ``running``::

    [resen] >>> status
    Bucket Name         Docker Image             Status
    amber               2020.1.0                 running

4. Export bucket ``amber``::

    [resen] >>> export amber

  The ``export`` command will ask a series of question.  First, provide a name for the output *.tar file::

    >>> Enter name for output tar file: /path/for/output/amber.tar

  If desired, change the default name and tag for the exported image::

    By default, the output image will be named "amber" and tagged "latest".
    >>> Would you like to change the name and tag? (y/n): y
    >>> Image name: custom_name
    >>> Image tag: custom_tag

  Specify if you want all mounted directories to be included in the exported bucket.  Answering `n` to this query will allow you to see how large each mount is and specify which you would like to include.  Consider excluding any mounts that are not nessesary for the analysis to reduce the size of the output file::

    The following local directories are mounted to the bucket (total 2212 MB):
    /home/usr/mount1
    /home/usr/mount2
    /home/usr/mount3
    >>> Would you like to include all of these in the exported bucket? (y/n): n
    >>> Include /home/usr/mount1 [154.68095 MB]? (y/n): y
    >>> Include /home/usr/mount2 [2005.28493 MB]? (y/n): y
    >>> Include /home/usr/mount3 [53.59823 MB]? (y/n): y

  Confirm that you want to continue with the export.  The values shown should be considered a "high-side" approximation and may not be the actual final size::

    This export could require up to 13337 MB of disk space to complete and will produce an output file up to 4600 MB.
    >>> Are you sure you would like to continue? (y/n): y
    Exporting bucket amber.  This will take several minutes.

5. Import a new bucket, ``amber2``, from a tar file ``amber.tar``::

    [resen] >>> import

  This command will also ask a series of questions.  First provide a name for the imported bucket::

    Please enter a name for your bucket.
    Valid names may not contain spaces and must start with a letter and be less than 20 characters long.
    >>> Enter bucket name: amber2

  Specify the *.tar file to import the bucket from::

    >>> Enter name for input tar file: /path/to/file/amber.tar

  If desired, enter a custom image name and tag.  If not provided, the name an image saved on export will be used::

    >>> Would you like to keep the default name and tag for the imported image? (y/n): n
    >>> Image name: amber2
    >>> Image tag: new_tag

  When a bucket that had mounts is imported, the mounted directories must be extracted and saved on the local machine.  Resen will do this automatically, but you have the option to specify where these files should be saved instead of the default location::

    The default directory to extract the bucket metadata and mounts to is /default/save/path/resen_amber2.
    >>> Would you like to specify and alternate directory? (y/n): y
    >>> Enter path to directory: /new_save_path

  Aside from the existing mounts, you can add new mounts to a imported bucket.  This is useful if you would like to repeat the analysis with a different dataset::

    >>> Mount additional storage to the imported bucket? (y/n): y
    >>> Enter local path: /new/local/path/new_mount
    >>> Enter bucket path: /home/jovyan/mount/new_mount
    >>> Enter permissions (r/rw): r
    >>> Mount additional storage to /home/jovyan/mount? (y/n): n

  Similar to ``create``, you have the option to start jupyter lab immediately after the bucket is imported::

    >>> Start bucket and jupyterlab? (y/n): y
    ...starting jupyterlab...
    Jupyter lab can be accessed in a browser at: http://localhost:9003/?token=70532767bab0ddc4febe2790efaaf974961e961e78e6025a

Sudo-enabled buckets
--------------------

When starting a bucket with resen, `sudo` is enabled for the jovyan user to allow special installation and configuration
where root security privileges are needed. The password for running `sudo` commands with user jovyan is: `ganimede`.

Remove a Bucket
---------------
**WARNING**: This will permanently delete the bucket. Any work that was not saved in a mounted storage directory or downloaded from the bucket will be **permanently lost**.

The user can delete a bucket with the following command::

    [resen] >>> remove amber

A bucket that is running needs to be stopped before being removed.


