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

# The fuctions remove_storage and remove_port will probably be used MINMALLY.  Is it worth keeping them?


import os
import cmd  # for command line interface
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
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)

    prefix = os.path.commonprefix([abs_directory, abs_target])

    return prefix == abs_directory


def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not is_within_directory(path, member_path):
            raise Exception("Attempted Path Traversal in Tar File")

    tar.extractall(path, members, numeric_owner=numeric_owner)


class Resen:
    def __init__(self):
        # get configuration info
        self.resen_root_dir = self._get_config_dir()
        self.resen_home_dir = self._get_home_dir()

        # set lock
        self.__locked = False
        self.__lock()

        # initialize docker helper
        self.dockerhelper = DockerHelper()

        # load configuration
        self.load_config()
        self.valid_cores = self.__get_valid_cores()
        self.selinux = self.__detect_selinux()

        self.win_vbox_map = self.__get_win_vbox_map()

        ### NOTE - Does this still need to include '/home/jovyan/work' for server compatability?
        ### If so, can we move the white list to resencmd.py? The server shouldn't ever try to
        ### mount to an illegal location but the user might.
        self.storage_whitelist = ["/home/jovyan/mount"]

    def load_config(self):
        """
        Load config file that contains information on existing buckets.
        """
        # define config file name
        bucket_config = os.path.join(self.resen_root_dir, "buckets.json")

        # TODO: handle exceptions due to file reading problems (incorrect file permissions)
        # TODO: update status of buckets to double check that status is the same as in bucket.json
        try:
            # check if buckets.json exists, if not, initialize empty dictionary
            with open(bucket_config, "r") as f:
                params = json.load(f)
        except FileNotFoundError:
            # if config file doesn't exist, initialize and empty list
            params = list()

        self.buckets = params
        self.bucket_names = [x["name"] for x in self.buckets]

    def save_config(self):
        """
        Save config file with information on existing buckets
        """
        # define config file name
        bucket_config = os.path.join(self.resen_root_dir, "buckets.json")
        # TODO: handle exceptions due to file writing problems (no free disk space, incorrect file permissions)
        with open(bucket_config, "w") as f:
            json.dump(self.buckets, f)

    def get_bucket(self, bucket_name):
        """
        Retrieve a bucket object by its name.  Raise an error if the bucket does not exist.
        """
        try:
            ind = self.bucket_names.index(bucket_name)
        except ValueError:
            raise ValueError("Bucket with name: %s does not exist!" % bucket_name)

        bucket = self.buckets[ind]
        return bucket

    def create_bucket(self, bucket_name):
        """
        Create "empty" bucket.  Only name assigned.
        """
        # raise error if bucket_name already in uses
        if bucket_name in self.bucket_names:
            raise ValueError(f"Bucket with name: {bucket_name} already exists!")

        params = dict()
        params["name"] = bucket_name
        params["image"] = None
        params["container"] = None
        params["port"] = list()
        params["storage"] = list()
        params["status"] = None
        params["jupyter"] = dict()
        params["jupyter"]["token"] = None
        params["jupyter"]["port"] = None

        # now add the new bucket to the self.buckets config and then update the config file
        self.buckets.append(params)
        self.bucket_names = [x["name"] for x in self.buckets]
        self.save_config()

    def remove_bucket(self, bucket_name):
        """
        Remove a bucket, including the corresponding container.
        """

        self.update_bucket_statuses()
        bucket = self.get_bucket(bucket_name)

        # cannot remove bucket if currently running - raise error
        if bucket["status"] == "running":
            raise RuntimeError(
                f"ERROR: Bucket {bucket['name']} is running, cannot remove."
            )

        # are other buckets using the same image?
        # if so, we shouldn't try to remove the image!
        rm_image_id = bucket["image"]["image_id"]
        buckets_with_same_id = list()
        for x in self.buckets:
            other_id = x["image"]["image_id"]
            other_name = x["name"]
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
                self.dockerhelper.remove_container(bucket, remove_image=remove_image)
                # also remove temporary import directory
                shutil.rmtree(bucket["import_dir"])
            else:
                self.dockerhelper.remove_container(bucket)

            bucket["status"] = None
            bucket["container"] = None
            self.save_config()

        # identify bucket index and remove it from both buckets and bucket_names
        ind = self.bucket_names.index(bucket_name)
        self.buckets.pop(ind)
        self.bucket_names.pop(ind)
        self.save_config()

    def set_image(self, bucket_name, docker_image):
        """
        Set the image to use in a bucket
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
        valid_versions = [x["version"] for x in self.valid_cores]
        if not docker_image in valid_versions:
            raise ValueError(
                "Invalid resen-core version %s. Valid versions: %s"
                % (docker_image, ", ".join(valid_versions))
            )

        ind = valid_versions.index(docker_image)
        image = self.valid_cores[ind]
        bucket["image"] = image

        self.save_config()

    def add_storage(self, bucket_name, local, container, permissions="r"):
        """
        Add a host machine storage location to the bucket.
        """
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
        if self.win_vbox_map:
            local = Path(
                local.replace(self.win_vbox_map[0], self.win_vbox_map[1])
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
        for loc in self.storage_whitelist:
            path = Path(loc)
            if path == child or path in child.parents:
                valid = True
        if not valid:
            raise ValueError(
                "Invalid mount location. Can only mount storage into: "
                f"{', '.join(self.storage_whitelist)}."
            )

        # check and adjust permissions
        if permissions not in ["r", "ro", "rw"]:
            raise ValueError("Invalid permissions. Valid options are 'r' and 'rw'.")

        if permissions in ["r", "ro"]:
            permissions = "ro"

        if self.selinux:
            permissions += ",Z"

        # Add storage location
        bucket["storage"].append([local, container, permissions])
        self.save_config()

    def remove_storage(self, bucket_name, local):
        """
        Remove a storage location from the bucket.
        """

        # get bucket
        bucket = self.get_bucket(bucket_name)

        # if container created, cannot remove storage
        if bucket["status"] is not None:
            raise RuntimeError(
                f"Bucket has already been started, cannot remove storage: {local}"
            )

        # if docker toolbox, change path to be the docker VM path instead of the host machine path
        if self.win_vbox_map:
            local = Path(
                local.replace(self.win_vbox_map[0], self.win_vbox_map[1])
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
        """
        Add a port to the bucket
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
        """
        Remove a port from the bucket
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
        # XXX: this is not atomic, so it is possible that another process might snatch up the port
        # TODO: check if port location exists on host - maybe not?  If usuer manually assigns port, ok to trust they know what they're doing?
        # TODO: check if port avaiable on host (from https://stackoverflow.com/questions/2470971/fast-way-to-test-if-a-port-is-in-use-using-python)
        port = 9000
        assigned_ports = [y[0] for x in self.buckets for y in x["port"]]

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
        # get bucket
        bucket = self.get_bucket(bucket_name)

        # Make sure we have an image assigned to the bucket
        if bucket["image"] is None:
            raise RuntimeError("Bucket does not have an image assigned to it.")

        container_id, status = self.dockerhelper.create_container(bucket)
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
        """
        Start the bucket
        """
        # get bucket
        bucket = self.get_bucket(bucket_name)

        # if bucket is already running, do nothing
        if bucket["status"] in ["running"]:
            return

        # If a container hasn't been created yet, raise error
        if bucket["container"] is None:
            raise RuntimeError(
                "Container for this bucket has not been created yet.  Cannot start bucket."
            )

        # start the container and update status
        status = self.dockerhelper.start_container(bucket)
        bucket["status"] = status
        self.save_config()

        # raise error if bucket did not start sucessfully
        if status != "running":
            raise RuntimeError(f"Failed to start bucket {bucket['name']}")

    def stop_bucket(self, bucket_name):
        """
        Stop bucket
        """

        self.update_bucket_statuses()
        # get bucket
        bucket = self.get_bucket(bucket_name)

        # if bucket is already stopped, do nothing
        if bucket["status"] in ["created", "exited"]:
            return

        # stop the container and update status
        status = self.dockerhelper.stop_container(bucket)
        bucket["status"] = status
        self.save_config()

        if status != "exited":
            raise RuntimeError(f"Failed to stop bucket {bucket['name']}")

    def execute_command(
        self, bucket_name, command, user="jovyan", detach=True, tty=False
    ):
        """
        Execute a command in the bucket.  Returns the exit code and output form the command,
        if applicable (if not detached?).
        """
        self.update_bucket_statuses()
        # get bucket
        bucket = self.get_bucket(bucket_name)

        # raise error if bucket not running
        if bucket["status"] not in ["running"]:
            raise RuntimeError(f"Bucket {bucket['name']} is not running!")

        # execute command
        result = self.dockerhelper.execute_command(
            bucket, command, user=user, detach=detach, tty=tty
        )
        code, _ = result
        if (detach and code is not None) or (not detach and code != 0):
            raise RuntimeError(f"Failed to execute command {command}")

        return result

    def set_sudo(self, bucket_name, password="ganimede"):
        """
        Add jovyan user to sudoers
        """
        command = f"""bash -cl 'echo "jovyan:{password}" | chpasswd && usermod -aG sudo jovyan && sed --in-place "s/^#\s*\(%sudo\s\+ALL=(ALL:ALL)\s\+ALL\)/\\1/" /etc/sudoers'"""  # TODO: test this
        self.execute_command(bucket_name, command, user="root", detach=False, tty=True)

    def start_jupyter(self, bucket_name, local_port=None, container_port=None):
        """
        Start a jupyter server in the bucket and open a web browser window to a jupyter lab session.
        Server will use the specified local and container ports (ports must be a matched pair!)
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
        if not local_port and not container_port:
            local_port = bucket["port"][0][0]
            container_port = bucket["port"][0][1]

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
        """
        Stop jupyter server
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
        """
        Get PID for the jupyter server running in a particular bucket
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
        """
        Export a bucket
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
            self.dockerhelper.export_container(
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

        return

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
        Import bucket from tgz file. Extract image and mounts. Set up new bucket
        with image and mounts. This does NOT add ports (these should be selected based
        on new local computer) and container is NOT created/started.
        """

        if not extract_dir:
            extract_dir = (
                Path(filename).resolve().with_name("resen_{}".format(bucket_name))
            )
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
        full_repo = "earthcubeingeo/{}".format(img_repo)

        if not img_tag:
            img_tag = manifest["image_tag"]

        # load image
        image_file = str(extract_dir.joinpath(manifest["image"]))
        img_id = self.dockerhelper.import_image(image_file, full_repo, img_tag)

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

        return

    def bucket_diskspace(self, bucket_name):
        """
        Determine the amount of disk space used by a bucket
        """
        # get bucket
        bucket = self.get_bucket(bucket_name)

        report = {}
        report["container"] = self.dockerhelper.get_container_size(bucket) / 1.0e6
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
        Determine total size of directory in bytes, doesn't follow symlinks.
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
        """
        Generate a nicely formated string listing all the buckets and their statuses
        """
        if bucket_name is None:
            if names_only:
                print("{:<0}".format("Bucket Name"))
                for name in self.bucket_names:
                    print("{:<0}".format(str(name)))
            else:
                print("{:<20}{:<25}{:<25}".format("Bucket Name", "Version", "Status"))
                for bucket in self.buckets:
                    name = self.__trim(str(bucket["name"]), 18)
                    image = self.__trim(str(bucket["image"]["version"]), 23)
                    status = self.__trim(str(bucket["status"]), 23)
                    print("{:<20}{:<25}{:<25}".format(name, image, status))

        else:
            bucket = self.get_bucket(bucket_name)

            print("%s\n%s\n" % (bucket["name"], "=" * len(bucket["name"])))
            print("Resen-core Version: ", bucket["image"]["version"])
            print("Status: ", bucket["status"])
            print("Jupyter Token: ", bucket["jupyter"]["token"])
            print("Jupyter Port: ", bucket["jupyter"]["port"])
            if bucket["jupyter"]["token"]:
                print(
                    "Jupyter lab URL: http://localhost:%s/?token=%s"
                    % (bucket["jupyter"]["port"], bucket["jupyter"]["token"])
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
        """
        Update container status for all buckets
        """
        for bucket in self.buckets:
            if bucket["container"] is None:
                continue

            status = self.dockerhelper.get_container_status(bucket)
            bucket["status"] = status
            self.save_config()

    def update_core_list(self):
        core_list_url = (
            "https://raw.githubusercontent.com/EarthCubeInGeo/"
            "resen-core/master/cores.json"
        )
        core_filename = os.path.join(self.resen_root_dir, "cores", "cores.json")

        try:
            req = requests.get(core_list_url)
        except (
            requests.exceptions.SSLError
        ) as exc:  # TODO: give user hints on how to fix this error
            print(f"WARNING: Couldn't update RESEN cores from {core_list_url}!")
            print(exc)
            return
            # print(
            #     f"WARNING: Couldn't update RESEN cores from {core_list_url}! If you're using a VPN, try turning that off."
            # )
            # return
        with open(core_filename, "wb") as f:
            f.write(req.content)

        self.valid_cores = self.__get_valid_cores()

    def update_docker_settings(self):
        # get docker inputs from resen cmd line
        self.valid_cores = self.__get_win_vbox_map(True)

    def __get_valid_cores(self):
        # define core list directory
        core_dir = os.path.join(self.resen_root_dir, "cores")

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

    def _get_config_dir(self):
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

    def _get_home_dir(self):
        appname = "resen"
        homedir = os.path.expanduser("~")

        return os.path.join(homedir, appname)

    def __process_exists(self, pid):
        # Need to do different things for *nix vs. Windows
        # see https://stackoverflow.com/questions/568271/
        # how-to-check-if-there-exists-a-process-with-a-given-pid-in-python

        if os.name == "nt":
            # only works on windows
            from win32com.client import GetObject

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
        else:
            return True  # no error, we can send a signal to the process

    def __lock(self):
        # dev note: if we want to be more advanced, need psutil as dependency
        # get some telemetry to fingerprint with
        cur_pid = os.getpid()  # process id

        # check if lockfile exists
        self.__lockfile = os.path.join(self.resen_root_dir, "lock")
        if os.path.exists(self.__lockfile):
            # parse existing file
            with open(self.__lockfile, "r") as f:
                pid = int(f.read())
                if self.__process_exists(pid):
                    raise RuntimeError("Another instance of Resen is already running!")

        telem = "%d" % (cur_pid)
        with open(self.__lockfile, "w") as f:
            f.write(telem)
        self.__locked = True

    def __unlock(self):
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
        try:
            pop = Popen(["/usr/sbin/getenforce"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
            output, _ = pop.communicate()
            output = output.decode("utf-8").strip("\n")
            rc = pop.returncode

            if rc == 0 and output == "Enforcing":
                return True
            return False
        except FileNotFoundError:
            return False

    def __get_win_vbox_map(self, reset=False):
        # quick fix for determining windows with docker tool box
        if platform.system().startswith("Win"):
            vm_info = os.path.join(self.resen_root_dir, "docker_toolbox_path_info.json")

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
        if len(string) > length:
            return string[: length - 3] + "..."
        return string

    def __del__(self):
        self.__unlock()

    # TODO: def reset_bucket(self,bucket_name):
    # used to reset a bucket to initial state (stop existing container, delete it, create new container)


def main():  # TODO: what's this for?
    pass


if __name__ == "__main__":
    main()
