Usage
*****

To use resen, simply enter ``resen`` at the command line::

    $ resen

This will open the resen tool::

        ___ ___ ___ ___ _  _ 
       | _ \ __/ __| __| \| |
       |   / _|\__ \ _|| .` |
       |_|_\___|___/___|_|\_|
    
    Resen 2019.1.0rc2 -- Reproducible Software Environment
    
    [resen] >>> 

Type ``help`` to see available commands::

    [resen] >>> help

This will produce a list of resen commands you will use to manage your resen buckets::

    Documented commands (type help <topic>):
    ========================================
    EOF            exit  quit           start_jupyter  stop_jupyter
    create_bucket  help  remove_bucket  status

To get more information about a specific command, enter ``help <command>``.

Resen Workflow
==============

Use Resen to create and remove buckets. Buckets are portable, system independent environments where code can be developed and run. Buckets can be shared between Windows, Linux, and macos systems and all analysis within the bucket will be run exactly the same. Resen buckets come preinstalled with a variety of common geospace software that can be used immediately in analysis.

Setup a New Bucket
------------------

1. Creating a new bucket is performed with the command::

     [resen] >>> create_bucket

   The ``create_bucket`` command queries the user for several pieces of information required to create a bucket. First it asks for the bucket name. Creating a bucket named ``amber``::

     Please enter a name for your bucket.
     Valid names may not contain spaces and must start with a letter and be less than 20 characters long.``
     >>> Enter bucket name: amber

   Next, the user is asked to specify the version of resen-core to use::

     Please choose a version of resen-core.
     Available versions: 2019.1.0rc2
     >>> Select a version: 2019.1.0.rc2

   Optionally, one may then specify a local directory to mount into the bucket at ``/home/jovyan/work``::

     Local directories can be mounted to either /home/jovyan/work or /home/jovyan/mount/ in
     a bucket. The /home/jovyan/work location is a workspace and /home/jovyan/mount/ is intended
     for mounting in data. You will have rw privileges to everything mounted in work, but can
     specify permissions as either r or rw for directories in mount. Code and data created in a
     bucket can ONLY be accessed outside the bucket or after the bucket has been deleted if it is
     saved in a mounted local directory.
     >>> Mount storage to /home/jovyan/work? (y/n): y
     >>> Enter local path: /some/local/path

   Followed by additional local directories that can be mounted under ``/home/jovyan/mount``::

     >>> Mount storage to /home/jovyan/mount? (y/n): y
     >>> Enter local path: /some/other/local/path
     >>> Enter bucket path: /home/jovyan/mount/data001
     >>> Enter permissions (r/rw): r
     >>> Mount additional storage to /home/jovyan/mount? (y/n): n

   Finally, the user is asked if they want jupyterlab to be started::

     >>> Start bucket and jupyterlab? (y/n): y

   after which resen will begin creating the bucket. Example output for a new bucket named ``amber`` with jupyterlab started is::

     ...adding core...
     ...adding mounts...
     Bucket created successfully!
     ...starting jupyterlab...
     Jupyter lab can be accessed in a browser at: http://localhost:9000/?token=61469c2ccef5dd27dbf9a8ba7c296f40e04278a89e6cf76a

2. Check the status of the bucket::

    [resen] >>> status amber
    {'bucket': {'name': 'amber'}, 'docker': {'image': '2019.1.0rc1', 'container': 'a6501d441a9f025dc7dd913bf6d531b6b452d0a3bd6d5bad0eedca791e1d92ca', 'port': [[9000, 9000, True]], 'storage': [['/some/local/path', '/home/jovyan/work', 'rw'], ['/some/other/local/path', '/home/jovyan/mount/data001', 'ro']], 'status': 'running', 'jupyter': {'token': '61469c2ccef5dd27dbf9a8ba7c296f40e04278a89e6cf76a', 'port': 9000}, 'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff', 'pull_image': 'earthcubeingeo/resen-core@sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b'}}

At this point, the bucket should have a name, an image, at least one port, and optionally one or more storage location.  Status should be ``running`` if the user decided to have jupyterlab started, otherwise the status will be ``None``.

Work with a Bucket
------------------
1. Check what buckets are available with ``status``::

    [resen] >>> status
    Bucket Name         Docker Image             Status
    amber               2019.1.0rc2              running

   If a bucket is running, it will consume system resources accordingly.

2. Stop jupyter lab from a bucket::

    [resen] >>> stop_jupyter amber

   The status of ``amber`` should now be ``exited``::

    [resen] >>> status
    Bucket Name         Docker Image             Status
    amber               2019.1.0rc2              exited

   The bucket will still exist and can be restarted at any time, even after quitting and restarting resen.

3. Start a jupyter lab in bucket ``amber`` that has been stopped::

    [resen] >>> start_jupyter amber

   The status of ``amber`` should now be ``running``::

    [resen] >>> status
    Bucket Name         Docker Image             Status
    amber               2019.1.0rc2              running


   The jupyter lab server starts in the ``/home/jovyan`` directory, which should include the persistent storage directories ``work`` and ``mount``.
   The user can alternate between the jupyter lab and the classic notebook view by changing the url in the browser from ``http://localhost:8000/lab`` to ``http://localhost:8000/tree``. Alternatively one can switch from the lab to the notebook through Menu -> Help -> Launch Classic Notebook.


Remove a Bucket
---------------
The user can delete a bucket with the following command::

    [resen] >>> remove_bucket amber

A bucket that is running needs to be stopped before removed.
WARNING: This will permanently delete the bucket. Any work that was not saved in a mounted storage directory will be lost.
