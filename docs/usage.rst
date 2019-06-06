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
	EOF        add_storage    help           remove_port     start_jupyter
	add_image  create_bucket  quit           remove_storage  status       
	add_port   exit           remove_bucket  start_bucket    stop_bucket  

To get more information about a specific command, enter ``help <command>``.

Resen Workflow
==============

Use Resen to start, stop, and manage resen buckets.  Buckets are portable, system independent environments where code can be developed and run.  Buckets can be shared between systems and the code in it will run exactly the same way.  Resen buckets come preinstalled with a variety of common geospace software that can be used immediately in analysis.

Setup a New Bucket
------------------

1. Create a new bucket.  Buckets should be given a name that a string of less than 20 characters with no spaces.  To create a bucket named ``amber``::

	[resen] >>> create_bucket amber

2. Add a resen image to the bucket.  The image name must be a valid resen-core tag that is available on Docker Hub.  For a list of tags, see https://hub.docker.com/r/earthcubeingeo/resen-core/tags.  To add the ``2019.1.0rc1`` image to ``amber``::

	[resen] >>> add_image amber 2019.1.0rc1

3. Add a port for the bucket.  This is required for the bucket to run jupyter notebooks.  A port on the bucket will map to a port on the local machine.  Map the local port 8000 to the bucket port 8080::

	[resen] >>> add_port amber 8000 8080

4. Add a persistent storage directory to the bucket.  This lets the bucket access code and data on the local machine.  Files created in a Resen bucket will be available outside of the bucket or after the bucket has been deleted ONLY if they are saved in a persistent storage directory.  Multiple storage directories can be added to the bucket.  Each persistent storage directory can have either read (`r`) or read/write (`rw`) permissions, specifying whether or not resen can write to the local directory.  Add the local directories ``/home/usr/code/fossil`` and ``/home/usr/data`` to the bucket in the ``/home/jovyan/work`` directory::

	[resen] >>> add_storage amber /home/usr/code/fossil /home/jovyan/work/fossil rw
	[resen] >>> add_storage amber /home/usr/data /home/jovyan/work/data r

5. Check the status of the bucket::

	[resen] >>> status amber
	{'bucket': {'name': 'amber'}, 'docker': {'image': 'docker.io/earthcubeingeo/resen-core:2019.1.0rc1', 'container': None, 'port': [[8000, 8080, True]], 'storage': [['/home/usr/code/fossil', '/home/jovyan/work/fossil', 'rw'], ['/home/usr/data', '/home/jovyan/work/data', 'ro']], 'status': None}}

At this point, the bucket should have a name, an image, at least one port, and at least one storage location.  Status should be ``None``.

Work in a Bucket
----------------
1. Check what buckets are available with ``status``::

	[resen] >>> status
	Bucket Name         Docker Image             Status                   
	amber               docker.io/earthcubei...  None   

Newly created buckets that have not been started will have Status ``None``.

2. Start a newly created bucket or restart a bucket that has been exited::

	[resen] >>> start_bucket amber
	Pulling image: docker.io/earthcubeingeo/resen-core:2019.1.0rc1
	    This may take some time...
	Done!

The status of ``amber`` should now be ``running``::

	[resen] >>> status
	Bucket Name         Docker Image             Status                   
	amber               docker.io/earthcubei...  running                  

3. Use the bucket to start a jupyter server.  Make sure to include the local port and the bucket port that forwards to it.  Start a jupyter server in ``amber``::

	[resen] >>> start_jupyter amber 8000 8080

The jupyter server starts in the ``/home/jovyan/work`` directory, which should include the persistent storage directories ``fossil`` and ``data``. Alternatively you can start directly a jupyter lab adding ``--lab`` to the previous command::

	[resen] >>> start_jupyter amber 8000 8080 --lab
	
or, if you already started the notebook without ``--lab`` you can change the url in your browser from ``http://localhost:8000/tree`` to ``http://localhost:8000/lab``. One can go back from the lab to the notebook through Menu -> Help -> Launch Classic Notebook.

4. Stop the jupyter server by clicking the "Quit" button on the home page of the notebook. The jupyter lab "Quit" button has not been configured in this version.

5. Stop the bucket::

	[resen] >>> stop_bucket amber

The status of ``amber`` should now be ``exited``::

	[resen] >>> status
	Bucket Name         Docker Image             Status                   
	amber               docker.io/earthcubei...  exited                   

The bucket will still exist and can be restarted at any time, even after quitting and restarting resen.

Remove a Bucket
---------------
Delete a bucket::

	remove_bucket amber

WARNING: This will permanently delete the bucket.  Any work that is not saved in a persistent storage directory will be lost.
