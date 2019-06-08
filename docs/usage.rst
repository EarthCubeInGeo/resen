Usage
*****

To use resen, simply enter ``resen`` at the command line::

    $ resen

This will open the resen tool::

        ___ ___ ___ ___ _  _ 
       | _ \ __/ __| __| \| |
       |   / _|\__ \ _|| .` |
       |_|_\___|___/___|_|\_|
    
    Resen 2019.1.0rc1 -- Reproducible Software Environment
    
    [resen] >>> 

Type ``help`` to see available commands::

    [resen] >>> help

This will produce a list of resen commands you will use to manage your resen buckets::

	Documented commands (type help <topic>):
	========================================
	EOF            exit  quit           start_bucket   status     
	create_bucket  help  remove_bucket  start_jupyter  stop_bucket


To get more information about a specific command, enter ``help <command>``.

Resen Workflow
==============

Use Resen to create, start, and stop buckets. Buckets are portable, system independent environments where code can be developed and run. Buckets can be shared between Windows, Linux, and macos systems and all analysis within the bucket will be run exactly the same. Resen buckets come preinstalled with a variety of common geospace software that can be used immediately in analysis.

Setup a New Bucket
------------------

1. Creating a new bucket is performed with the command::

	[resen] >>> create_bucket bucket_name

The ``create_bucket`` command queries the user for several pieces of information required to create a bucket. Bucket names must be a string of less than 20 characters with no spaces. To create a bucket named ``amber``::

	[resen] >>> create_bucket amber

Next, the user is asked to specify the version of resen-core to use::

	Please choose a version of resen-core. Available versions: 2019.1.0rc1
	>>> Select a version: 

Optionally, one may then specify a local directory to mount into the bucket at ``/home/jovyan/work``::

    >>> Mount storage to /home/jovyan/work? (y/n): y
    >>> Enter local path:

Followed by additional local directories that can be mounted under ``/home/jovyan/mount``::

    >>> Mount additional storage to /home/jovyan/mount? (y/n):

Finally, the user is asked if they want jupyterlab to be started::

    >>> Start bucket and jupyterlab? (y/n):

after which resen will begin creating the bucket. Example output for a new bucket named ``amber`` with jupyterlab started is::

    Creating bucket with name: test
    ...adding core...
    ...adding mounts...
    Bucket created successfully!
    Jupyter lab can be accessed in a browser at: http://localhost:9000/?token=61469c2ccef5dd27dbf9a8ba7c296f40e04278a89e6cf76a

2. Check the status of the bucket::

	[resen] >>> status amber
	{'bucket': {'name': 'amber'}, 'docker': {'image': 'docker.io/earthcubeingeo/resen-core:2019.1.0rc1', 'container': None, 'port': [[8000, 8080, True]], 'storage': [['/home/usr/code/fossil', '/home/jovyan/work/fossil', 'rw'], ['/home/usr/data', '/home/jovyan/work/data', 'ro']], 'status': None}}

At this point, the bucket should have a name, an image, at least one port, and at least one storage location.  Status should be ``None``.

Work with a Bucket
------------------
1. Check what buckets are available with ``status``::

	[resen] >>> status
	Bucket Name         Docker Image             Status                   
	amber               docker.io/earthcubei...  running

If a bucket is running, it will consume system resources accordingly.

2. Stop the bucket::

	[resen] >>> stop_bucket amber

The status of ``amber`` should now be ``exited``::

	[resen] >>> status
	Bucket Name         Docker Image             Status                   
	amber               docker.io/earthcubei...  exited  

The bucket will still exist and can be restarted at any time, even after quitting and restarting resen.

3. Start a bucket ``amber`` that has been stopped::

	[resen] >>> start_bucket amber

The status of ``amber`` should now be ``running``::

	[resen] >>> status
	Bucket Name         Docker Image             Status                   
	amber               docker.io/earthcubei...  running                  

3. Use the bucket to start a jupyter server.  Make sure to include the local port and the bucket port that forwards to it.  Start a jupyter server in ``amber``::

	[resen] >>> start_jupyter amber 8000 8080

The jupyter server starts in the ``/home/jovyan/work`` directory, which should include the persistent storage directories ``fossil`` and ``data``. Alternatively you can start directly a jupyter lab adding ``--lab`` to the previous command::

	[resen] >>> start_jupyter amber 8000 8080 --lab
	
or, if you already started the notebook without ``--lab`` you can change the url in your browser from ``http://localhost:8000/tree`` to ``http://localhost:8000/lab``. One can go back from the lab to the notebook through Menu -> Help -> Launch Classic Notebook.

4. Stop jupyter lab by clicking "Quit" in the "File" menu of Jupyter lab.


Remove a Bucket
---------------
Delete a bucket::

	remove_bucket amber

WARNING: This will permanently delete the bucket. Any work that was not saved in a mounted storage directory will be lost.
