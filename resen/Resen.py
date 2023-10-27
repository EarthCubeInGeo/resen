#!/usr/bin/env python
####################################################################
#
#  Title: resen
#
#  Author: resen developer team
#  Description: The resen tool for working with resen-core locally
#               which allows for listing available core docker
#               images, creating resen buckets, starting buckets,
#               curing (freezing) buckets, and uploading frozen
#
####################################################################


# TODO
# 1) list available resen-core version from dockerhub
# 2) check for python 3, else throw error
# 3) when starting a bucket again, need to recreate the container if ports and/or storage locations changed. Can do so with: https://stackoverflow.com/a/33956387
#    until this happens, we cannot modify storage nor ports after a bucket has been started
# 4) check that a local port being added isn't already used by another bucket.
# 5) check that a local storage location being added isn't already used by another bucket.
#     - add a location for home directory persistent storage
#     - how many cpu/ram resources are allowed to be used?
#     - json file contains all config info about buckets
#         - used to share and freeze buckets
#         - track information about buckets (1st time using, which are running?)

# The fuctions remove_storage and remove_port will probably be used MINMALLY.
# Is it worth keeping them?


# TODO: do we need these in-line comments to explain what all the imports are for?
import os
import json  # used to store bucket manifests locally and for export
import time  # used for waiting (time.sleep())
import socket  # find available port
import shutil
import random  # used to generate tokens for jupyter server
import tarfile
import tempfile  # use this to get unique name for docker container
import webbrowser  # use this to open web browser
from pathlib import Path  # used to check whitelist paths
from subprocess import Popen, PIPE  # used for selinux detection
import platform  # NEEDED FOR WINDOWS QUICK FIX
import glob
import requests


from .DockerHelper import DockerHelper


def is_within_directory(directory, target):
    """Check whether directory path is within target path.

    Parameters
    ----------
    directory : pathlike
        Pathlike object which may be the prefix path for `target`.
    target : pathlike
        Pathlike object which may contain `directory` as a prefix.

    Returns
    -------
    bool
        Returns True if `directory` is the prefix path for `target`.
    """
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)

    prefix = os.path.commonprefix([abs_directory, abs_target])

    return prefix == abs_directory


def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
    """Helper function to safely extract a TarFile, i.e., to avoid Path Traversal.

    Parameters
    ----------
    tar : TarFile
        TarFile to be extracted.
    path : pathlike
        Path to extraction location for `tar`.
    members : list of TarInfo objects, default=None
        See TarFile.getmembers and TarFile.extractall for more details.
    numeric_owner : bool, default=False
        See TarFile.extractall for more details.

    Returns
    -------
    None

    Raises
    ------
    Exception
        If path in `tar`

    See Also
    --------
    TarFile.getmembers
    TarFile.extractall
    """
    # TODO: complete the docstring above
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not is_within_directory(path, member_path):
            raise Exception("Attempted Path Traversal in Tar File")

    tar.extractall(path, members, numeric_owner=numeric_owner)


class Resen:
    """This class manages Resen buckets and host memory.

    Parameters
    ----------
    None

    Attributes
    ----------
    __resen_root_dir : pathlike
        The path to the Resen config directory. Contains bucket information and Resen cores.
    __dockerhelper : DockerHelper
        An instance of a custom class which takes care on the under-the-hood Docker operations.
    __valid_cores : list
        A list containing json information on available Resen cores.
    __selinux : Bool
        True if Security-Enhanced Linux is enabled.
    __win_vbox_map : pathlike
        Path to Docker VM if Docker Toolbox is in use (Windows). Else, is None.
    __storage_whitelist : list
        A list of acceptable paths on host to mount to. Hard-coded to "/home/jovyan/mount".
    __buckets : list
        A list of json information for each bucket.
    __bucket_names : list
        A list of bucket names, which are extracted from the `buckets` attribute.
    __locked : Bool
        A Bool which ensures only one instance of Resen is running at a time on host.

    Examples
    --------
    >>> r = Resen()
    >>> r.get_config_dir()
    /home/username/.config/resen
    """

    def __init__(self):
        """Class constructor."""
        # get configuration info
        self.__resen_root_dir = self.get_config_dir()

        # set lock
        self.__locked = False
        self.__lock()

        # initialize docker helper
        self.__dockerhelper = DockerHelper()

        # load configuration
        self.__load_config()
        self.__valid_cores = self.get_valid_cores()
        self.__selinux = self.__detect_selinux()

        self.__win_vbox_map = self.__get_win_vbox_map()

        ### TODO - Does this still need to include '/home/jovyan/work' for server compatability?
        ### If so, can we move the white list to resencmd.py? The server shouldn't ever try to
        ### mount to an illegal location but the user might.
        self.__storage_whitelist = ["/home/jovyan/mount"]

    def __load_config(self):
        """Load config file that contains information on existing buckets.

        This function loads the resen config file in self.__resen_root_dir and sets attributes,
        such as self.__buckets. This function is called only once within the class: in the
        class constructor.

        Parameters
        ----------
        None

        Returns
        -------
        None

        See Also
        --------
        Resen.get_config_dir : Get Resen config directory.
        """
        # define config file name
        bucket_config = os.path.join(self.__resen_root_dir, "buckets.json")

        # TODO: handle exceptions due to file reading problems (incorrect file permissions)
        # TODO: update status of buckets to double check that status is the same as in bucket.json
        try:
            # check if buckets.json exists, if not, initialize empty dictionary
            with open(bucket_config, "r") as f:
                params = json.load(f)
        except FileNotFoundError:
            # if config file doesn't exist, initialize and empty list
            params = []

        self.__buckets = params
        self.__bucket_names = [x["name"] for x in self.__buckets]

    def save_config(self):
        # TODO: make sure bucket json info isn't just dumped into file without confirming the format is correct!!!
        # Format should be:
        # params = {}
        # params["name"] = bucket_name
        # params["image"] = None
        # params["container"] = None
        # params["port"] = []
        # params["storage"] = []
        # params["status"] = None
        # params["jupyter"] = {}
        # params["jupyter"]["token"] = None
        # params["jupyter"]["port"] = None
        """Save all bucket info to config file.

        Parameters
        ----------
        None

        Returns
        -------
        None

        See Also
        --------
        Resen.get_config_dir : Get Resen config directory.
        """
        # define config file name #TODO: should this be a member variable / attribute?
        bucket_config = os.path.join(self.__resen_root_dir, "buckets.json")
        # TODO: handle exceptions due to file writing problems (no free disk space, incorrect file permissions)
        with open(bucket_config, "w") as f:
            json.dump(self.__buckets, f)

    def get_bucket(self, bucket_name):
        """Retrieve a bucket object by its name.

        Parameters
        ----------
        bucket_name : string
            The name of the bucket to be retrieved.

        Returns
        -------
        dictionary
            Retrieved bucket.

        Raises
        ------
        ValueError
            If `bucket_name` doesn't exist.

        See Also
        --------
        Resen.get_bucket_names : Get Resen bucket names.

        Examples
        --------
        >>> r = Resen()
        >>> r.get_bucket("b2")
        Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "resen/Resen.py", line 285, in get_bucket
            raise ValueError(f"Bucket with name: {bucket_name} does not exist!")
        ValueError: Bucket with name: b2 does not exist!
        >>> r.get_bucket_names()
        ['b1']
        >>> r.get_bucket("b1")
        {'name': 'b1', 'image': {'version': '2021.1.0', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:824018435d5d42217e4b342b16c7a0f0eb649b3f4148e7f8c11d7c39e34cae3d',
        'repodigest': 'sha256:c449da829228f6f25e24500a67c0f1cd1f6992be3c0d1b5772e837f2023ec506',
        'envpath': '/home/jovyan/envs/py38'},
        'container': '851bd05f6749a590f1a86f833fc0908dedd8b680a117b9396daa0e01f7574069',
        'port': [[9000, 9000, True]], 'storage': [], 'status': 'exited',
        'jupyter': {'token': None, 'port': None}}
        """
        try:
            ind = self.__bucket_names.index(bucket_name)
        except ValueError:
            raise ValueError(f"Bucket with name: {bucket_name} does not exist!")

        bucket = self.__buckets[ind]
        return bucket

    def create_bucket(self, bucket_name):
        """Create an empty bucket.

        Parameters
        ----------
        bucket_name : string
            The name of the empty bucket to be created.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If a bucket called `bucket_name` already exists.

        See Also
        --------
        Resen.save_config : Save all bucket info to config file.

        Examples
        --------
        >>> r = Resen()
        >>> r.get_bucket("b2")
        Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "resen/Resen.py", line 285, in get_bucket
            raise ValueError(f"Bucket with name: {bucket_name} does not exist!")
        ValueError: Bucket with name: b2 does not exist!
        >>> r.create_bucket("b2")
        >>> r.get_bucket_names()
        ['b1', 'b2']
        >>> r.get_bucket("b2")
        {'name': 'b2', 'image': None, 'container': None, 'port': [], 'storage': [],
        'status': None, 'jupyter': {'token': None, 'port': None}}
        """
        # raise error if bucket_name already in uses
        if bucket_name in self.__bucket_names:
            raise ValueError(f"Bucket with name: {bucket_name} already exists!")

        params = {}
        params["name"] = bucket_name
        params["image"] = None
        params["container"] = None
        params["port"] = []
        params["storage"] = []
        params["status"] = None
        params["jupyter"] = {}
        params["jupyter"]["token"] = None
        params["jupyter"]["port"] = None

        # now add the new bucket to the self.__buckets config and then update the config file
        self.__buckets.append(params)
        self.__bucket_names = [x["name"] for x in self.__buckets]
        self.save_config()

    def remove_bucket(self, bucket_name):
        """Remove a bucket, including the corresponding Docker container.

        Parameters
        ----------
        bucket_name : string
            The name of the bucket to be removed.

        Returns
        -------
        None

        Raises
        ------
        RuntimeError
            If bucket called `bucket_name` is running.

        See Also
        --------
        DockerHelper.remove_container : Remove the container associated with the provided bucket.
        """
        self.update_bucket_statuses()
        bucket = self.get_bucket(bucket_name)

        # cannot remove bucket if currently running - raise error
        if bucket["status"] == "running":
            raise RuntimeError(
                f"ERROR: Bucket {bucket['name']} is running, cannot remove."
                f"Stop the bucket first with 'stop {bucket['name']}'."
            )

        # are other buckets using the same image?
        # if so, we shouldn't try to remove the image!
        rm_image_id = bucket["image"]["image_id"]
        buckets_with_same_id = []
        for bucket in self.__buckets:
            other_id = bucket["image"]["image_id"]
            other_name = bucket["name"]
            if other_id == rm_image_id and other_name != bucket_name:
                buckets_with_same_id.append(other_name)

        remove_image = len(buckets_with_same_id) == 0

        # if docker container created, remove it first and update status
        if (
            bucket["status"] in ["created", "exited"]
            and bucket["container"] is not None
        ):
            # if bucket imported, clean up by removing image and import directory
            if "import_dir" in bucket:
                self.__dockerhelper.remove_container(bucket, remove_image=remove_image)
                # also remove temporary import directory
                shutil.rmtree(bucket["import_dir"])
            else:
                self.__dockerhelper.remove_container(bucket)

            bucket["status"] = None
            bucket["container"] = None
            self.save_config()

        # identify bucket index and remove it from both buckets and bucket_names
        ind = self.__bucket_names.index(bucket_name)
        self.__buckets.pop(ind)
        self.__bucket_names.pop(ind)
        self.save_config()

    def set_image(self, bucket_name, docker_image):
        """Set the Docker image to use for a bucket.

        Parameters
        ----------
        bucket_name : string
            The name of the bucket whose image will be set.
        docker_image : string
            The resen-core version which defines the Docker image for the bucket
            called `bucket_name`.

        Returns
        -------
        None

        Raises
        ------
        RuntimeError
            If the bucket called `bucket_name` has already been started.
        ValueError
            If `docker_image` is not in self.__valid_cores.

        See Also
        --------
        ResenCmd.do_create : Create a new bucket by responding to the prompts provided.
        Resen.get_valid_cores : Get list of available Resen cores.

        Examples
        --------
        >>> r = Resen()
        >>> cores = r.get_valid_cores()
        >>> version0 = cores[0]["version"]
        >>> print(cores[0]["version"])
        2019.1.0rc1
        >>> r.get_bucket_names()
        ['b1', 'b2']
        >>> r.create_bucket("b3")
        >>> r.get_bucket_names()
        ['b1', 'b2', 'b3']
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': None, 'container': None, 'port': [], 'storage': [],
        'status': None, 'jupyter': {'token': None, 'port': None}}
        >>> r.set_image("b3", version0)
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'}, 'container': None, 'port': [], 'storage': [],
        'status': None, 'jupyter': {'token': None, 'port': None}}
        """

        # TODO It should be fine to overwrite an existing image if the container hasn't been started yet
        # TODO would be helpful to save image org and repo as well for export purposes
        # TODO should we check if the image ID is available locally and if not pull it HERE insead of in the container creation?

        # get bucket
        bucket = self.get_bucket(bucket_name)

        # if container has been created, cannot change the image
        if bucket["status"] is not None:
            raise RuntimeError("Bucket has already been started, cannot set new image.")

        # check that input is a valid image
        valid_versions = [x["version"] for x in self.__valid_cores]
        if not docker_image in valid_versions:
            raise ValueError(
                f"Invalid resen-core version {docker_image}. Valid versions: "
                f"{', '.join(valid_versions)}"
            )

        ind = valid_versions.index(docker_image)
        image = self.__valid_cores[ind]
        bucket["image"] = image

        self.save_config()

    def add_storage(self, bucket_name, local, container, permissions="r"):
        """Add a host machine storage location to the bucket.

        Parameters
        ----------
        bucket_name : string
            The name of the bucket for which storage will be mounted.
        local : pathlike
            Path to local mount location.
        container : pathlike
            Mount location within bucket.
        permissions : {"r", "ro", "rw"}, default="r"
            File permissions for mounted storage.

        Returns
        -------
        None

        Raises
        ------
        RuntimeError
            If bucket has already been started, storage cannot be added.
        FileNotFoundError
            If `local` does not exist.
        FileExistsError
            If `local` is already in use as storage for another bucket,
            or if `container` is already in use as another bucket.
        ValueError
            If `container` is not a whitelisted location,
            or if `permissions` is not one of the allowed values - {"r", "ro", "rw"}

        See Also
        --------
        ResenCmd.do_create : Create a new bucket by responding to the prompts provided.
        Resen.remove_storage : Remove a storage location for a bucket.

        Examples
        --------
        >>> r = Resen()
        >>> r.get_bucket_names()
        ['b1', 'b2', 'b3']
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'}, 'container': None, 'port': [], 'storage': [],
        'status': None, 'jupyter': {'token': None, 'port': None}}
        >>> r.add_storage("b3", "/home/username/test_dir", "home/username/test_dir")
        Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "resen/Resen.py", line 582, in add_storage
            raise ValueError(
        ValueError: Invalid mount location. Can only mount storage into: /home/jovyan/mount.
        >>> r.add_storage("b3", "/home/username/test_dir", "/home/jovyan/mount")
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'}, 'container': None, 'port': [],
        'storage': [['/home/username/test_dir', '/home/jovyan/mount', 'ro']],
        'status': None, 'jupyter': {'token': None, 'port': None}}
        """
        # TODO: in  'Raises' section above, what does "whitelisted location" mean?

        # TODO: investiage difference between mounting a directory and fileblock
        #       See: https://docs.docker.com/storage/

        # get bucket
        bucket = self.get_bucket(bucket_name)

        # if container has been created, cannot add storage
        if bucket["status"] is not None:
            raise RuntimeError(
                f"Bucket has already been started, cannot add storage: {local}"
            )

        # check that local file path exists
        if not Path(local).is_dir():
            raise FileNotFoundError("Cannot find local storage location!")

        # if docker toolbox, change path to be the docker VM path instead of the host machine path
        if self.__win_vbox_map:
            local = Path(
                local.replace(self.__win_vbox_map[0], self.__win_vbox_map[1])
            ).as_posix()

        # check if input locations already exist in bucket list of storage
        existing_local = [x[0] for x in bucket["storage"]]
        if local in existing_local:
            raise FileExistsError("Local storage location already in use in bucket!")
        existing_container = [x[1] for x in bucket["storage"]]
        if container in existing_container:
            raise FileExistsError(
                "Container storage location already in use in bucket!"
            )

        # check that user is mounting in a whitelisted location
        valid = False
        child = Path(container)
        for loc in self.__storage_whitelist:
            path = Path(loc)
            if path == child or path in child.parents:
                valid = True
        if not valid:
            raise ValueError(
                "Invalid mount location. Can only mount storage into: "
                f"{', '.join(self.__storage_whitelist)}."
            )

        # check and adjust permissions
        if permissions not in ["r", "ro", "rw"]:
            raise ValueError("Invalid permissions. Valid options are 'r' and 'rw'.")

        if permissions in ["r", "ro"]:
            permissions = "ro"

        if self.__selinux:
            permissions += ",Z"

        # Add storage location
        bucket["storage"].append([local, container, permissions])
        self.save_config()

    def remove_storage(self, bucket_name, local):
        """Remove a storage location for a bucket.

        Parameters
        ----------
        bucket_name : string
            The name of the bucket.
        local : pathlike
            Path to local mount location.

        Returns
        -------
        None

        Raises
        ------
        RuntimeError
            If bucket/container has already been started, storage cannot be removed.
        FileNotFoundError
            If `local` is not a storage location associated with `bucket_name`.

        See Also
        --------
        Resen.add_storage : Add a host machine storage location to the bucket.

        Examples
        --------
        >>> r = Resen()
        >>> r.get_bucket_names()
        ['b1', 'b2', 'b3']
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'}, 'container': None, 'port': [],
        'storage': [['/home/username/test_dir', '/home/jovyan/mount', 'ro']],
        'status': None, 'jupyter': {'token': None, 'port': None}}
        >>> r.remove_storage("b3", "/home/username/test_dir")
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'}, 'container': None, 'port': [], 'storage': [],
        'status': None, 'jupyter': {'token': None, 'port': None}}
        """

        # get bucket
        bucket = self.get_bucket(bucket_name)

        # if container created, cannot remove storage
        if bucket["status"] is not None:
            raise RuntimeError(
                f"Bucket has already been started, cannot remove storage: {local}"
            )

        # if docker toolbox, change path to be the docker VM path instead of the host machine path
        if self.__win_vbox_map:
            local = Path(
                local.replace(self.__win_vbox_map[0], self.__win_vbox_map[1])
            ).as_posix()

        # find index of storage
        existing_storage = [x[0] for x in bucket["storage"]]
        try:
            ind = existing_storage.index(local)
        # raise exception if input location does not exist
        except ValueError:
            raise FileNotFoundError(
                f"Storage location {local} not associated with bucket {bucket_name}"
            )

        bucket["storage"].pop(ind)
        self.save_config()

    def add_port(self, bucket_name, local=None, container=None, tcp=True):
        """Add a port to a bucket.

        Parameters
        ----------
        bucket_name : string
            The name of the bucket.
        local : int, dafult=None
            Port to be assigned to `bucket_name`.
        container : pathlike, default=None
            Path to bucket's container.
        tcp : Bool, default=True
            If True, TCP protocol will be used. Otherwise, the UDP protocol will be used. See
            DockerHelper.create_continer for more.

        Returns
        -------
        None

        Raises
        ------
        RuntimeError
            If bucket has already been started, port cannot be added.
        ValueError
            If port already exists in list of ports.

        See Also
        --------
        Resen.get_port : Find and bind an available port for a bucket.
        Resen.remove_port : Remove a port from a bucket.
        DockerHelper.create_container : Create a docker container with the image, mounts, and
            ports set in this bucket. If the image does not exist locally, pull it.

        Examples
        --------
        >>> r = Resen()
        >>> r.get_bucket_names()
        ['b1', 'b2', 'b3']
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'}, 'container': None, 'port': [], 'storage': [],
        'status': None, 'jupyter': {'token': None, 'port': None}}
        >>> r.add_port("b3")
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'}, 'container': None, 'port': [[9001, 9001, True]],
        'storage': [], 'status': None, 'jupyter': {'token': None, 'port': None}}
        """
        # get bucket
        bucket = self.get_bucket(bucket_name)

        # if container has been created, cannot add port
        if bucket["status"] is not None:
            raise RuntimeError(
                f"Bucket has already been started, cannot add port: {local}"
            )

        if not local and not container:
            # this is not atomic, so it is possible that another process might snatch up the port
            local = self.get_port()
            container = local

        else:
            # check if local/container port already exists in list of ports
            existing_local = [x[0] for x in bucket["port"]]
            if local in existing_local:
                raise ValueError("Local port location already in use in bucket!")
            existing_container = [x[1] for x in bucket["port"]]
            if container in existing_container:
                raise ValueError("Container port location already in use in bucket!")

        bucket["port"].append([local, container, tcp])
        self.save_config()

    def remove_port(self, bucket_name, local):
        """Remove a port from a bucket.

        Parameters
        ----------
        bucket_name : string
            The name of the bucket.
        local : int, dafult=None
            Port to be removed from `bucket_name`.

        Returns
        -------
        None

        Raises
        ------
        RuntimeError
            If bucket has already been started, port cannot be removed.
        ValueError
            If the port `local` is not assigned to `bucket_name`.

        See Also
        --------
        Resen.add_port : Add a port to a bucket.

        Examples
        --------
        >>> r = Resen()
        >>> r.get_bucket_names()
        ['b1', 'b2', 'b3']
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'}, 'container': None, 'port': [[9001, 9001, True]],
        'storage': [], 'status': None, 'jupyter': {'token': None, 'port': None}}
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'}, 'container': None, 'port': [], 'storage': [],
        'status': None, 'jupyter': {'token': None, 'port': None}}
        """
        # get bucket
        bucket = self.get_bucket(bucket_name)

        # if container has been created, cannot remove port
        if bucket["status"] is not None:
            raise RuntimeError(
                f"Bucket has already been started, cannot remove port: {local}"
            )

        # find port and remove it
        existing_port = [x[0] for x in bucket["port"]]
        try:
            ind = existing_port.index(local)
        # raise exception if port is not assigned to bucket
        except ValueError:
            raise ValueError(
                "Port location %s not associated with bucket %s" % (local, bucket_name)
            )

        bucket["port"].pop(ind)
        self.save_config()

    def get_port(self):
        """Find and bind an available port for a bucket.

        Parameters
        ----------
        None

        Returns
        -------
        int
            Available port which has been opened/bound.
            Defaults to 9000 when no ports have been assigned.

        See Also
        --------
        Resen.add_port : Add a port to a bucket.
        """
        # XXX: this is not atomic, so it is possible that another process might snatch up the port
        # TODO: check if port location exists on host - maybe not?  If usuer manually assigns port, ok to trust they know what they're doing?
        # TODO: check if port avaiable on host (from https://stackoverflow.com/questions/2470971/fast-way-to-test-if-a-port-is-in-use-using-python)
        port = 9000
        assigned_ports = [y[0] for x in self.__buckets for y in x["port"]]

        while True:
            if port in assigned_ports:
                port += 1
                continue

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("localhost", port))
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    return port
                except Exception as exc:
                    print(port, str(exc))
                    port += 1

    def create_container(self, bucket_name, give_sudo=True):
        """Create a Docker container for a bucket.

        Parameters
        ----------
        bucket_name : string
            Name of the bucket whose Docker container will be created.
        give_sudo : bool, default=True
            If True, set up sudo permissions for jovyan.

        Returns
        -------
        None

        Raises
        ------
        RuntimeError
            If `bucket_name` does not have a (Docker) image assigned to it. See Resen.set_image.

        See Also
        --------
        Resen.set_image : Set the Docker image to use for a bucket.
        DockerHelper.create_container : Create a docker container with the image, mounts, and
            ports set in this bucket. If the image does not exist locally, pull it.

        Examples
        --------
        >>> r = Resen()
        >>> r.get_bucket_names()
        ['b1', 'b2', 'b3']
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'}, 'container': None, 'port': [], 'storage': [],
        'status': None, 'jupyter': {'token': None, 'port': None}}
        >>> r.create_container("b3", False)
        Pulling image: resen-core:2019.1.0rc1
        This may take some time...
        [===============================>]100.0 %, 3.281/3.28GB Elapsed t: 0:01:42
        Done!
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'},
        'container': '82e4b02571bcca061c9822f1610b75e0238e1c81f006b2ff6dcf0f5d0a595577',
        'port': [], 'storage': [], 'status': 'created', 'jupyter': {'token': None, 'port': None}}
        """
        # get bucket
        bucket = self.get_bucket(bucket_name)

        # Make sure we have an image assigned to the bucket
        if bucket["image"] is None:
            raise RuntimeError("Bucket does not have an image assigned to it.")

        container_id, status = self.__dockerhelper.create_container(bucket)
        bucket["container"] = container_id
        bucket["status"] = status
        self.save_config()

        if give_sudo:
            # start bucket and execute any commands needed for proper set-up
            self.start_bucket(bucket_name)
            # run commands to set up sudo for jovyan
            self.set_sudo(bucket_name)
            self.stop_bucket(bucket_name)

    def start_bucket(self, bucket_name):
        """Start a bucket.

        Parameters
        ----------
        bucket_name : string
            Name of the bucket whose Docker container will be started.

        Returns
        -------
        None

        Raises
        ------
        RuntimeError
            If bucket called `bucket_name` does not have a Docker container created for it yet.
            If the Docker container failed to start.

        See Also
        --------
        Resen.create_container : Create a Docker container for a bucket.
        DockerHelper.start_container : Start a container.

        Examples
        --------
        >>> r = Resen()
        >>> r.get_bucket_names()
        ['b1', 'b2', 'b3']
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'},
        'container': '82e4b02571bcca061c9822f1610b75e0238e1c81f006b2ff6dcf0f5d0a595577',
        'port': [], 'storage': [], 'status': 'created', 'jupyter': {'token': None, 'port': None}}
        >>> r.start_bucket("b3")
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'},
        'container': '82e4b02571bcca061c9822f1610b75e0238e1c81f006b2ff6dcf0f5d0a595577',
        'port': [], 'storage': [], 'status': 'running', 'jupyter': {'token': None, 'port': None}}
        """
        # get bucket
        bucket = self.get_bucket(bucket_name)

        # if bucket is already running, do nothing
        if bucket["status"] in ["running"]:
            return

        # If a container hasn't been created yet, raise error
        if bucket["container"] is None:
            raise RuntimeError(
                "Container for this bucket has not been created yet. Cannot start bucket."
            )

        # start the container and update status
        status = self.__dockerhelper.start_container(bucket)
        bucket["status"] = status
        self.save_config()

        # raise error if bucket did not start sucessfully
        if status != "running":
            raise RuntimeError(f"Failed to start bucket {bucket['name']}")

    def stop_bucket(self, bucket_name):
        """Stop a bucket.

        Parameters
        ----------
        bucket_name : string
            Name of the bucket whose Docker container will be stopped.

        Returns
        -------
        None

        Raises
        ------
        RuntimeError
            If the Docker container failed to stop.

        See Also
        --------
        DockerHelper.stop_container : Stop a container.

        Examples
        --------
        >>> r = Resen()
        >>> r.get_bucket_names()
        ['b1', 'b2', 'b3']
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'},
        'container': '82e4b02571bcca061c9822f1610b75e0238e1c81f006b2ff6dcf0f5d0a595577',
        'port': [], 'storage': [], 'status': 'running', 'jupyter': {'token': None, 'port': None}}
        >>> r.stop_bucket("b3")
        >>> r.get_bucket("b3")
        {'name': 'b3', 'image': {'version': '2019.1.0rc1', 'repo': 'resen-core',
        'org': 'earthcubeingeo',
        'image_id': 'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
        'repodigest': 'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b',
        'envpath': '/home/jovyan/envs/py36'},
        'container': '82e4b02571bcca061c9822f1610b75e0238e1c81f006b2ff6dcf0f5d0a595577',
        'port': [], 'storage': [], 'status': 'exited', 'jupyter': {'token': None, 'port': None}}
        """

        self.update_bucket_statuses()
        # get bucket
        bucket = self.get_bucket(bucket_name)

        # if bucket is already stopped, do nothing
        if bucket["status"] in ["created", "exited"]:
            return

        # stop the container and update status
        status = self.__dockerhelper.stop_container(bucket)
        bucket["status"] = status
        self.save_config()

        if status != "exited":
            raise RuntimeError(f"Failed to stop bucket {bucket['name']}")

    def execute_command(
        self, bucket_name, command, user="jovyan", detach=True, tty=False
    ):
        """Execute a command in the bucket.

        Parameters
        ----------
        bucket_name : string
            Name of the bucket.
        command : string
            Command to be execute within bucket's Docker container.
        user : string, default="jovyan"
            User which will be used to execute command.
        detach: Bool, default=True
            If True, detach from exec command. See DockerHelper.execute_command for more details.
        tty : Bool, default=True
            If True, allocate a pseudo-TTY. See DockerHelper.execute_command for more details.

        Returns
        -------
        int
            The exit code from command execution.

        Raises
        ------
        RuntimeError
            If the bucket is not running.
            If command fails to execute, i.e., if (detach is True and the exit code is not None) or
            (detach is False and the exit code is not 0).

        See Also
        --------
        DockerHelper.execute_command : Execute a command in a container.

        Examples
        --------
        >>> r = Resen()
        >>> r.get_bucket_names()
        ['b1', 'b2', 'b3']
        >>> r.execute_command("b3", "echo hello", detach=False)
        Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "resen/Resen.py", line 963, in execute_command
            raise RuntimeError(f"Bucket {bucket['name']} is not running!")
        RuntimeError: Bucket b3 is not running!
        >>> r.start_bucket("b3")
        >>> r.execute_command("b3", "echo hello", detach=False)
        (0, b'hello\n')
        >>> r.execute_command("b3", "ld", detach=False)
        Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "resen/Resen.py", line 971, in execute_command
            raise RuntimeError(f"Failed to execute command {command}")
        RuntimeError: Failed to execute command ld
        >>> r.execute_command("b3", "ls", detach=False)
        (0, b'')
        """
        self.update_bucket_statuses()
        # get bucket
        bucket = self.get_bucket(bucket_name)

        # raise error if bucket not running
        if bucket["status"] not in ["running"]:
            raise RuntimeError(f"Bucket {bucket['name']} is not running!")

        # execute command
        result = self.__dockerhelper.execute_command(
            bucket, command, user=user, detach=detach, tty=tty
        )
        code, _ = result
        if (detach and code is not None) or (not detach and code != 0):
            raise RuntimeError(f"Failed to execute command {command}")

        return result

    def set_sudo(self, bucket_name, password="ganimede"):
        """Add jovyan user to sudoers.

        Parameters
        ----------
        bucket_name : string
            Name of the bucket.
        password : string
            Password for user "jovyan".

        Returns
        -------
        None

        See Also
        --------
        Resen.execute_command : Execute a command in the bucket.

        Examples
        --------
        >>> r = Resen()
        >>> r.get_bucket_names()
        ['b1', 'b2', 'b3']
        >>> r.set_sudo("b3")
        Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "resen/Resen.py", line 1186, in set_sudo
            self.execute_command(bucket_name, command, user="root", detach=False, tty=True)
        File "resen/Resen.py", line 1137, in execute_command
            raise RuntimeError(f"Bucket {bucket['name']} is not running!")
        RuntimeError: Bucket b3 is not running!
        >>> r.start_bucket("b3")
        >>> r.set_sudo("b3")
        """
        command = f"""bash -cl 'echo "jovyan:{password}" | chpasswd && usermod -aG sudo jovyan && sed --in-place "s/^#\s*\(%sudo\s\+ALL=(ALL:ALL)\s\+ALL\)/\\1/" /etc/sudoers'"""  # TODO: test this
        self.execute_command(bucket_name, command, user="root", detach=False, tty=True)

    def start_jupyter(self, bucket_name, local_port=None, container_port=None):
        """Start a jupyter server for a bucket.

        Open a web browser window to a jupyter lab session.
        Server will use the specified local and container ports (ports must be a matched pair!)

        Parameters
        ----------
        bucket_name : string
            Name of the bucket.
        local_port : int, default=None
            Port from where jupyter server can be accessed.
            Must be a matched pair with `container_port`.
        container_port :
            Port from where jupyter server can be accessed.
            Must be a matched pair with `local_port`.

        Returns
        -------
        None

        Raises
        ------
        RuntimeError
            If jupyter server failed to start.
            If `local_port` or `container_port` not provided and
            no port has not been assigned to `bucket_name`.
            See Resen.add_port to add a port, or provide them as parameters to this function.

        See Also
        --------
        Resen.execute_command : Execute a command in the bucket.
        Resen.get_jupyter_pid : Get PID for the jupyter server running in a particular bucket.
        Resen.add_port : Add a port to a bucket.
        """
        # TODO:
        # Identify port ONLY with local port?
        # Select port automatically if none provided?
        # Allow multiple jupyter servers to run simultaniously?  Would this ever be useful?

        # get bucket
        bucket = self.get_bucket(bucket_name)

        # check if jupyter server already running - if so, proint the url to the screen
        pid = self.get_jupyter_pid(bucket_name)
        if pid is not None:
            port = bucket["jupyter"]["port"]
            token = bucket["jupyter"]["token"]
            url = f"http://localhost:{port}/?token={token}"
            print(
                f"Jupyter lab is already running and can be accessed in a browser at: {url}"
            )
            return

        # if ports are not specified, use the first port set from the bucket
        if not local_port or not container_port:
            if len(bucket["port"]) != 0:
                local_port = bucket["port"][0][0]
                container_port = bucket["port"][0][1]

            raise RuntimeError(
                f"Local port or container has not been assigned. "
                "Please provide a local port or have one assigned to bucket {bucket_name}"
            )

        # Get the python environment path, if none found, default to py36
        envpath = bucket["image"].get("envpath", "/home/jovyan/envs/py36")

        # set a random token and form
        token = "%048x" % random.randrange(16**48)
        command = (
            f"bash -cl 'source {envpath}/bin/activate && jupyter lab --no-browser --ip 0.0.0.0 "
            f"--port {container_port} --NotebookApp.token={token} "
            "--KernelSpecManager.ensure_native_kernel=False'"
        )

        # exectute command to start jupyter server
        self.execute_command(bucket_name, command, detach=True)
        time.sleep(0.1)

        # now check that jupyter is running
        self.update_bucket_statuses()
        pid = self.get_jupyter_pid(bucket_name)

        if pid is None:
            raise RuntimeError("Failed to start jupyter server!")

        # set jupyter token an port
        bucket["jupyter"]["token"] = token
        bucket["jupyter"]["port"] = local_port
        self.save_config()

        # print url to access jupyter lab to screen and automatically open in web browser
        url = f"http://localhost:{local_port}/?token={token}"
        print(f"Jupyter lab can be accessed in a browser at: {url}")
        time.sleep(3)
        webbrowser.open(url)

    def stop_jupyter(self, bucket_name):
        """Stop jupyter server for a bucket.

        Parameters
        ----------
        bucket_name : string
            Name of the bucket.

        Returns
        -------
        None

        Raises
        ------
        RuntimeError
            If the jupyter server fails to stop.

        See Also
        --------
        Resen.get_jupyter_pid : Get PID for the jupyter server running in a particular bucket.
        """
        # get bucket
        bucket = self.get_bucket(bucket_name)

        # if jupyter server not running, do nothing
        pid = self.get_jupyter_pid(bucket_name)
        if pid is None:
            return

        # Get the python environment path, if none found, default to py36
        envpath = bucket["image"].get("envpath", "/home/jovyan/envs/py36")

        # form python command to stop jupyter and execute it
        # TODO: is there no more concise way to do this? lots of super long, hard-coded commands
        port = bucket["jupyter"]["port"]
        python_cmd = (
            'exec(\\"try:  from jupyter_server.serverapp import shutdown_server, '
            "list_running_servers\\n"
        )
        python_cmd += (
            "except:  from notebook.notebookapp import shutdown_server, "
            "list_running_servers\\n"
        )
        python_cmd += (
            'svrs = [x for x in list_running_servers() if x[\\\\\\"port\\\\\\"] == '
            f"{port}]; "
        )
        python_cmd += (
            'sts = True if len(svrs) == 0 else shutdown_server(svrs[0]); print(sts)\\")'
        )
        command = f"bash -cl '{envpath}/bin/python -c \"{python_cmd} \"'"
        self.execute_command(bucket_name, command, detach=False)

        # now verify it is dead
        pid = self.get_jupyter_pid(bucket_name)
        if not pid is None:
            raise RuntimeError("Failed to stop jupyter lab.")

        # Update jupyter token and port to None
        bucket["jupyter"]["token"] = None
        bucket["jupyter"]["port"] = None
        self.save_config()

        return

    def get_jupyter_pid(self, bucket_name):
        """Get PID for the jupyter server running in a particular bucket.

        Parameters
        ----------
        bucket_name : string
            Name of the bucket.

        Returns
        -------
        None
        """
        _, output = self.execute_command(bucket_name, "ps -ef", detach=False)
        output = output.decode("utf-8").split("\n")

        pid = None
        for line in output:
            if (
                "jupyter-lab" in line or "jupyter lab" in line
            ) and "--no-browser --ip 0.0.0.0" in line:
                parsed_line = [x for x in line.split(" ") if x != ""]
                pid = parsed_line[1]
                break

        return pid

    def export_bucket(
        self, bucket_name, outfile, exclude_mounts=[], img_repo=None, img_tag=None
    ):
        """Export a bucket to file.

        Parameters
        ----------
        bucket_name : string
            Name of the bucket.
        outfile : string
            Name of the file to save to.
        excluded_mounts : list, default=[]
            Mounted locations to exclude from the bucket export.
        img_repo : string, default=None
            Name of bucket when exporting. If None, the bucket will be exported as `bucket_name`.
        img_tag : string, default=None
            Tag used in import/export. If None, the tag defaults to "latest".

        Returns
        -------
        None

        See Also
        --------
        DockerHelper.export_container
        """
        # TODO: some kind of status bar would be useful - this takes a while
        # TODO: maybe see if we can determine expected image size and free disk space
        # Should we include "human readable" metadata?

        # make sure the output filename has the .tgz or .tar.gz extension on it
        name, ext = os.path.splitext(outfile)
        if not ext == ".tar":
            outfile = name + ".tar"

        # get bucket
        bucket = self.get_bucket(bucket_name)

        # create temporary directory that will become the final bucket tar file
        print(f"Exporting bucket: {str(bucket_name)}...")
        with tempfile.TemporaryDirectory() as bucket_dir:
            bucket_dir_path = Path(bucket_dir)

            # initialize manifest
            manifest = {}

            if not img_repo:
                img_repo = bucket["name"].lower()
            if not img_tag:
                img_tag = "latest"

            # export container to image *.tar file
            image_file_name = f"{bucket_name}_image.tgz"
            print("...exporting image...")
            self.__dockerhelper.export_container(
                bucket, bucket_dir_path.joinpath(image_file_name), img_repo, img_tag
            )
            print("...done")
            manifest["image"] = image_file_name
            manifest["image_repo"] = img_repo
            manifest["image_tag"] = img_tag

            # save all mounts individually as *.tgz files
            manifest["mounts"] = []
            for mount in bucket["storage"]:
                # skip mount if it is listed in exclude_mounts
                if mount[0] in exclude_mounts:
                    continue

                source_dir = Path(mount[0])
                mount_file_name = f"{source_dir.name}_mount.tgz"
                print(f"...exporting mount: {str(source_dir)}")
                with tarfile.open(
                    str(bucket_dir_path.joinpath(mount_file_name)),
                    "w:gz",
                    compresslevel=1,
                ) as tar:
                    tar.add(str(source_dir), arcname=source_dir.name)

                manifest["mounts"].append([mount_file_name, mount[1], mount[2]])

            # save manifest file
            print("...saving manifest")
            with open(str(bucket_dir_path.joinpath("manifest.json")), "w") as f:
                json.dump(manifest, f)

            # save entire bucket as tar file
            with tarfile.open(outfile, "w") as tar:
                for f in os.listdir(str(bucket_dir_path)):
                    tar.add(str(bucket_dir_path.joinpath(f)), arcname=f)

        print("...Bucket export complete!")

    def import_bucket(
        self,
        bucket_name,
        filename,
        extract_dir=None,
        img_repo=None,
        img_tag=None,
        remove_image_file=False,
    ):
        """
        Import a bucket from file.

        Import a bucket from a tgz file. Extract image and mounts. Set up new bucket
        with image and mounts. This does NOT add ports (these should be selected based
        on new local computer) and container is NOT created/started.

        Parameters
        ----------
        bucket_name : string
            Name of the bucket.
        outfile : string
            Name of the file to import from.
        extract_dir : pathlike, default=None
            Where to extract the bucket to.
        img_repo : string, default=None
            Name of bucket when importing.
            If None, the bucket name defaults to that which was exported.
        img_tag : string, default=None
            Tag used in import/export.
            If None, the tag defaults to that which was exported.

        Returns
        -------
        None

        See Also
        --------
        DockerHelper.import_image
        """

        if not extract_dir:
            extract_dir = Path(filename).resolve().with_name(f"resen_{bucket_name}")
        else:
            extract_dir = Path(extract_dir)

        # untar bucket file
        with tarfile.open(filename) as tar:
            safe_extract(tar, path=str(extract_dir))

        # read manifest
        with open(str(extract_dir.joinpath("manifest.json")), "r") as f:
            manifest = json.load(f)

        # create new bucket
        self.create_bucket(bucket_name)
        bucket = self.get_bucket(bucket_name)

        if not img_repo:
            img_repo = manifest["image_repo"]
        full_repo = f"earthcubeingeo/{img_repo}"

        if not img_tag:
            img_tag = manifest["image_tag"]

        # load image
        image_file = str(extract_dir.joinpath(manifest["image"]))
        img_id = self.__dockerhelper.import_image(image_file, full_repo, img_tag)

        # add image to bucket
        bucket["image"] = {
            "version": img_tag,
            "repo": img_repo,
            "org": "earthcubeingeo",
            "image_id": img_id,
            "repodigest": "",
        }

        # add mounts to bucket
        for mount in manifest["mounts"]:
            # extract mount from tar file
            with tarfile.open(str(extract_dir.joinpath(mount[0]))) as tar:
                safe_extract(tar, path=str(extract_dir))
                local = extract_dir.joinpath(tar.getnames()[0])
            # remove mount tar file
            os.remove(str(extract_dir.joinpath(mount[0])))
            # add mount to bucket with original container path
            self.add_storage(bucket_name, str(local), mount[1], permissions=mount[2])

        bucket["import_dir"] = str(extract_dir)
        self.save_config()

        # clean up image file
        if remove_image_file:
            os.remove(image_file)

    def bucket_diskspace(self, bucket_name):
        """
        Determine the amount of disk space used by a bucket.

        Parameters
        ----------
        bucket_name : string
            Name of the bucket.

        Returns
        -------
        dictionary
            Reported size of bucket and mounted storage.

        See Also
        --------
        Resen.dir_size : Determine total size of directory in bytes.
        DockerHelper.get_container_size
        """
        # get bucket
        bucket = self.get_bucket(bucket_name)

        report = {}
        report["container"] = self.__dockerhelper.get_container_size(bucket) / 1.0e6
        report["storage"] = []

        total_size = 0.0
        for mount in bucket["storage"]:
            mount_size = self.dir_size(mount[0]) / 1.0e6
            report["storage"].append({"local": mount[0], "size": mount_size})
            total_size += mount_size

        report["total_storage"] = total_size

        return report

    def dir_size(self, directory):
        """
        Determine total size of directory in bytes.

        XXX This method doesn't follow symlinks.

        Parameters
        ----------
        directory : pathlike
            Directory whose size will be determined.

        Returns
        -------
        int
            Size of `directory` in bytes.
        """
        total_size = 0
        for dirpath, _, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                # skip if it is symbolic link
                if not os.path.islink(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size

    def list_buckets(self, names_only=False, bucket_name=None):
        """Generate a nicely formated string listing all the buckets and their statuses.

        Parameters
        ----------
        names_only : Bool, default=False
            If True, print only the names of buckets.
        bucket_name : string, default=None
            If not None, prints the status of the bucket called `bucket_name`.

        Returns
        -------
        None

        Raises
        ------
        AssertionError
            If `names_only` is not a Boolean.

        See Also
        --------
        ResenCmd.do_list : List all resen buckets.
        ResenCmd.do_status : Print the status of a bucket.

        Examples
        --------
        >>> r=Resen()
        >>> r.list_buckets()
        Bucket Name         Version                  Status
        b1                  2021.1.0                 exited
        b2                  None                     None
        b3                  2019.1.0rc1              exited
        >>> r.list_buckets("b1")
        Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "resen/Resen.py", line 1658, in list_buckets
            assert isinstance(names_only, bool), "names_only must be a boolean."
        AssertionError: names_only must be a boolean.
        >>> r.list_buckets(bucket_name="b1")
        b1
        ==

        Resen-core Version:  2021.1.0
        Status:  exited
        Jupyter Token:  None
        Jupyter Port:  None

        Storage:
        Local                                   Bucket                                  Permissions

        Ports:
        Local          Bucket
        9000           9000
        """
        assert isinstance(names_only, bool), "names_only must be a boolean."

        if bucket_name is None:
            if names_only:
                print("{:<0}".format("Bucket Name"))
                for name in self.__bucket_names:
                    print("{:<0}".format(str(name)))
            else:
                print("{:<20}{:<25}{:<25}".format("Bucket Name", "Version", "Status"))
                for bucket in self.__buckets:
                    name = self.__trim(str(bucket["name"]), 18)
                    try:
                        image = self.__trim(str(bucket["image"]["version"]), 23)
                    except TypeError as err:
                        image = "None"
                    status = self.__trim(str(bucket["status"]), 23)
                    print("{:<20}{:<25}{:<25}".format(name, image, status))

        else:
            bucket = self.get_bucket(bucket_name)

            print("%s\n%s\n" % (bucket["name"], "=" * len(bucket["name"])))
            try:
                print("Resen-core Version: ", bucket["image"]["version"])
            except TypeError as err:
                print("Resen-core Version: None")
            print("Status: ", bucket["status"])
            print("Jupyter Token: ", bucket["jupyter"]["token"])
            print("Jupyter Port: ", bucket["jupyter"]["port"])
            if bucket["jupyter"]["token"]:
                print(
                    f"Jupyter lab URL: http://localhost:{bucket['jupyter']['port']}/?"
                    f"token={bucket['jupyter']['token']}"
                )

            print("\nStorage:")
            print("{:<40}{:<40}{:<40}".format("Local", "Bucket", "Permissions"))
            for mount in bucket["storage"]:
                print("{:<40}{:<40}{:<40}".format(mount[0], mount[1], mount[2]))

            print("\nPorts:")
            print("{:<15}{:<15}".format("Local", "Bucket"))
            for port in bucket["port"]:
                print("{:<15}{:<15}".format(port[0], port[1]))

    def update_bucket_statuses(self):
        """Update container status for all buckets.

        Parameters
        ----------
        None

        Returns
        -------
        None

        See Also
        --------
        DockerHelper.get_container_status : Get the status of a particular container.
        """
        for bucket in self.__buckets:
            if bucket["container"] is None:
                continue

            status = self.__dockerhelper.get_container_status(bucket)
            bucket["status"] = status
            self.save_config()

    def update_core_list(self):
        """Pull resen cores from github.

        Pull Docker images used to create Resen buckets from GitHub at
        https://raw.githubusercontent.com/EarthCubeInGeo/resen-core/master/cores.json.

        Parameters
        ----------
        None

        Returns
        -------
        None

        See Also
        --------
        Resen.get_valid_cores : Get list of available Resen cores.
        """
        core_list_url = (
            "https://raw.githubusercontent.com/EarthCubeInGeo/"
            "resen-core/master/cores.json"
        )
        core_filename = os.path.join(self.__resen_root_dir, "cores", "cores.json")

        try:
            req = requests.get(core_list_url)
        except (
            requests.exceptions.SSLError
        ) as exc:  # TODO: give user hints on how to fix this error
            print(f"WARNING: Couldn't update RESEN cores from {core_list_url}!")
            print(exc)
            return
            # print(
            #     f"WARNING: Couldn't update RESEN cores from {core_list_url}! "
            #     "If you're using a VPN, try turning that off."
            # )
            # return
        with open(core_filename, "wb") as f:
            f.write(req.content)

        self.__valid_cores = self.get_valid_cores()

    def update_docker_settings(self):
        """Update Resen settings related to Docker on Windows.

        Parameters
        ----------
        None

        Returns
        -------
        None

        See Also
        --------
        """
        # get docker inputs from resen cmd line
        self.__get_win_vbox_map(True)

    def get_valid_cores(self):
        """Get list of available Resen cores.

        Get list of valid and available Resen cores (appropriate Docker images) for user
        to choose and create buckets from.

        Parameters
        ----------
        pull_cores : Bool, default=False
            If True, update_core_list() will be run to pull cores from GitHub.

        Returns
        -------
        list
            List of strings, which represent the Resen core version available.

        See Also
        --------
        Resen.update_core_list : Pull resen cores from GitHub.
        """
        # define core list directory
        core_dir = os.path.join(self.__resen_root_dir, "cores")

        # If core directory does not exist, create it and download the default core list file
        if not os.path.exists(core_dir):
            os.makedirs(core_dir)
            self.update_core_list()

        # for each JSON file in core directory, read in list of cores
        json_files = glob.glob(os.path.join(core_dir, "*.json"))

        cores = []
        for filename in sorted(json_files):
            try:
                with open(filename) as f:
                    cores.extend(json.load(f))
            except:
                print(f"WARNING: Problem reading {filename}. Skipping.")

        return cores

    def get_bucket_names(self):
        """Get Resen bucket names.

        Parameters
        ----------
        None

        Returns
        -------
        list
            List of bucket names
        """

        return self.__bucket_names

    def get_config_dir(self):
        """Get Resen config directory.

        Resen config firectory depends on host machine and operating system.

        Parameters
        ----------
        None

        Returns
        -------
        pathlike
            Path to Resen config directory.
        """
        appname = "resen"

        if "APPDATA" in os.environ:
            confighome = os.environ["APPDATA"]
        elif "XDG_CONFIG_HOME" in os.environ:
            confighome = os.environ["XDG_CONFIG_HOME"]
        else:
            confighome = os.path.join(os.environ["HOME"], ".config")
        configpath = os.path.join(confighome, appname)

        os.makedirs(configpath, exist_ok=True)

        return configpath

    def get_home_dir(self):
        """Get home directory of app called "resen".

        Parameters
        ----------
        None

        Returns
        -------
        Pathlike
            Path to Resen home directory, a combination of home directory and "resen".
        """
        appname = "resen"
        homedir = os.path.expanduser("~")

        return os.path.join(homedir, appname)

    def __process_exists(self, pid):
        """Check whether a process is running.

        Parameters
        ----------
        pid : int
            PID which whose running status will be checked.

        Returns
        -------
        Bool
            True if process with PID `pid` is running. False otherwise.
        """
        # TODO Need to do different things for *nix vs. Windows
        # see https://stackoverflow.com/questions/568271/
        # how-to-check-if-there-exists-a-process-with-a-given-pid-in-python

        if os.name == "nt":
            # only works on windows
            from win32com.client import (
                GetObject,
            )  # TODO: maybe we shouldn't do the import here? what's pep8 on conditional imports?

            WMI = GetObject("winmgmts:")
            processes = WMI.InstancesOf("Win32_Process")
            pids = [process.Properties_("ProcessID").Value for process in processes]
            return pid in pids
        # only works on *nix systems
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:  # errno.EPERM
            return True  # Operation not permitted (i.e., process exists)
        return True  # no error, we can send a signal to the process

    def __lock(self):
        # NOTE: dev note: if we want to be more advanced, need psutil as dependency
        # get some telemetry to fingerprint with
        cur_pid = os.getpid()  # process id

        # check if lockfile exists
        self.__lockfile = os.path.join(self.__resen_root_dir, "lock")
        if os.path.exists(self.__lockfile):
            # parse existing file
            with open(self.__lockfile, "r") as f:
                pid = int(f.read())
                if self.__process_exists(pid):
                    raise RuntimeError("Another instance of Resen is already running!")

        with open(self.__lockfile, "w") as f:
            f.write(str(cur_pid))
        self.__locked = True

    def __unlock(self):
        """Remove lockfile.

        This method is only called in conjunction wiht the destructor method, Resen.__del__,
        and attempts to remove the member variable self.__lockfile.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        if not self.__locked:
            return

        try:
            os.remove(self.__lockfile)
            self.__locked = False
        except FileNotFoundError:
            pass
        except Exception as exc:
            print(f"WARNING: Unable to remove lockfile: {str(exc)}")

    def __detect_selinux(self):
        """Detect whether Security-Enhanced Linux, SELinux, is enabled.

        This method is needed to determine permissions for bucket generation.

        Parameters
        ----------
        None

        Returns
        -------
        Bool
            True if SELinux is found. False otherwise.
        """
        try:
            with Popen(
                ["/usr/sbin/getenforce"], stdin=PIPE, stdout=PIPE, stderr=PIPE
            ) as pop:
                output, _ = pop.communicate()
                output = output.decode("utf-8").strip("\n")
                return_code = pop.returncode

            if return_code == 0 and output == "Enforcing":
                return True
            return False
        except FileNotFoundError:
            return False

    def __get_win_vbox_map(self, reset=False):
        """Get Docker settings for Windows users.

        Parameters
        ----------
        reset : Bool, default=False
            When True, users will be re-queried for system settings.

        Returns
        -------
        None
        """
        # quick fix for determining windows with docker tool box
        if platform.system().startswith("Win"):
            vm_info = os.path.join(
                self.__resen_root_dir, "docker_toolbox_path_info.json"
            )

            # ask user about docker toolbox, save responses for future use
            if reset or (not os.path.exists(vm_info)):
                print(
                    "If your are unsure of the appropriate responses below, please "
                    "refer to the Resen documentation"
                    " (https://resen.readthedocs.io/en/latest/installation/"
                    "installation.windows.html#docker) for more details and assistance."
                )
                while True:
                    rsp = input(
                        "Resen appears to be running on a Windows system. "
                        "Are you using Docker Toolbox? (y/n): "
                    )
                    if rsp == "y":
                        print(
                            "Please specify the mapping between shared folders "
                            "on the host machine and the Docker VM."
                        )
                        hostpath = input("Host machine path: ")
                        vmpath = input("Docker VM path: ")

                        print(
                            "WARNING: Resen will remember that you're using Docker Toolbox. "
                            "To change these settings later, run the 'change_settings' command."
                        )
                        save_dict = {}
                        save_dict["host_machine_path"] = hostpath
                        save_dict["docker_vm_path"] = vmpath
                        with open(vm_info, "w") as f:
                            json.dump(save_dict, f)

                        return [hostpath, vmpath]
                    if rsp == "n":
                        print(
                            "WARNING: Resen will remember that you're NOT using Docker Toolbox. "
                            "To change these settings later, run the 'change_settings' command."
                        )
                        save_dict = {}
                        with open(vm_info, "w") as f:
                            json.dump(save_dict, f)
                        return None
                    print("Invalid input. Please type 'y' or 'n'")
            else:
                with open(vm_info, "r") as f:
                    vm_info_dict = json.load(f)
                try:
                    hostpath = vm_info_dict["host_machine_path"]
                    vmpath = vm_info_dict["docker_vm_path"]
                    return [hostpath, vmpath]
                except Exception:
                    return None

    def __trim(self, string, length):
        """Trim string to given length.

        Parameters
        ----------
        string : string
            String to be trimmed.
        length : int
            Length to trim string to.

        Returns
        -------
        string
            Trimmed string.
        """
        if len(string) > length:
            return string[: length - 3] + "..."
        return string

    def __del__(self):
        """Class destructor."""
        self.__unlock()

    # TODO: def reset_bucket(self,bucket_name):
    # used to reset a bucket to initial state (stop existing container,
    # delete it, create new container)


def main():  # TODO: what's this for?
    pass


if __name__ == "__main__":
    main()
