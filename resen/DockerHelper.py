#!/usr/bin/env python

import os
import gzip
import datetime
import docker
import requests

# all the docker commands wrapped up nicely


# how do we call docker commands? subprocess? os.call?
# TODO: Use the docker SDK (https://docker-py.readthedocs.io/en/stable/)
class DockerHelper:
    """Class to wrapp up native Docker commands as methods to be use in resen."""
    def __init__(self):
        # TODO: define these in a dictionary or json file for each version of resen-core
        # need to get information for each resen-core from somewhere.
        # Info like, what internal port needs to be exposed? Where do we get the image from? etc.
        # mounting directory in the container?
        # What does container.reload() do?  Do we need it?  Where?
        self.container_prefix = "resen_"

        try:
            self.docker = docker.from_env()
        except Exception as exc:
            print(
                f"ERROR: Problem starting Docker client: {exc}.\nPlease confirm that Docker "
                "is running.\nIf issues persist, be sure to "
                "allow the default Docker socket in Advanced Docker desktop Settings."
            )
            raise

    # def create_container(self,**input_kwargs):
    def create_container(self, bucket):
        """
        Create a docker container with the image, mounts, and ports set in this bucket.
        If the image does not exist locally, pull it.
        """

        # set up basic keyword argument dict
        kwargs = {}
        kwargs["name"] = self.container_prefix + bucket["name"]
        kwargs["command"] = "bash"
        kwargs["tty"] = True
        kwargs["ports"] = {}

        # if bucket has ports, add these to kwargs
        for host, container, tcp in bucket["port"]:
            if tcp:
                key = f"{container}/tcp"
            else:
                key = f"{container}/udp"
            kwargs["ports"][key] = host

        # if bucket has mounts, add these to kwargs
        kwargs["volumes"] = {}
        for host, container, permissions in bucket["storage"]:
            temp = {"bind": container, "mode": permissions}
            kwargs["volumes"][host] = temp

        # check if we have image
        try:
            local_image_ids = [x.id for x in self.docker.images.list()]
        except Exception as exc:
            print("Problem getting the list of images!")
            print(
                "Be sure to allow the  "
                "default Docker socket in Advanced Docker desktop Settings. "
            )
            print(exc)
            raise

        # if not, pull it
        if bucket["image"]["image_id"] not in local_image_ids:
            self.stream_pull_image(bucket["image"])

        # start the container
        try:
            container = self.docker.containers.create(
                bucket["image"]["image_id"], **kwargs
            )
        except Exception as exc:
            print("Problem creating the Bucket!")
            print(exc)
            raise

        return container.id, container.status

    def remove_container(self, bucket, remove_image=False):
        """
        Remove the container associated with the provided bucket.
        """
        container = self.docker.containers.get(bucket["container"])
        container.remove()

        if remove_image:
            self.docker.images.remove(bucket["image"]["image_id"])

    def start_container(self, bucket):
        """
        Start a container.
        """
        # need to check if bucket config has changed since last run
        container = self.docker.containers.get(bucket["container"])
        container.start()  # this does nothing if already started
        container.reload()

        return container.status

    def stop_container(self, bucket):
        """
        Stop a container.
        """
        container = self.docker.containers.get(bucket["container"])
        container.stop()  # this does nothing if already stopped
        container.reload()

        return container.status

    def execute_command(self, bucket, command, user="jovyan", detach=True, tty=False):
        """
        Execute a command in a container.  Returns the exit code and output
        """
        container = self.docker.containers.get(bucket["container"])
        result = container.exec_run(command, user=user, detach=detach, tty=tty)

        return result.exit_code, result.output

    # def stream_pull_image(self,pull_image):
    def stream_pull_image(self, image):
        """
        Pull image from dockerhub.
        """

        # time formatting
        def truncate_secs(delta_time, fmt=":%.2d"):
            delta_str = str(delta_time).split(":")
            return ":".join(delta_str[:-1]) + fmt % (float(delta_str[-1]))

        # get terminal dimensions
        def get_terminal_dims():
            """Returns integers rows and columns of the terminal."""
            terminal_size = os.get_terminal_size()
            return terminal_size.lines, terminal_size.columns

        # progress bar
        def update_bar(sum_total, accumulated, t_0, current_time, init_bar_chars=34):
            """Updates the progress bar.

            Args:
                sum_total: total number of bytes to download
                accumulated: bytes already downloaded
                t_0: time when pulling image started
                current_time: current time
                init_bar_chars: default number of characters of the bar
                              including [,>, spaces,  and ],
                              e.g. [===>   ] would be 9 characters.
            """
            percentage = accumulated / sum_total * 100
            time_info = f"Elapsed t: {truncate_secs(current_time - t_0)}"
            bartext = "%5.1f %%, %5.3f/%4.2fGB %s" % (
                percentage,
                accumulated / 1024**3,
                sum_total / 1024**3,
                time_info,
            )
            _, columns = get_terminal_dims()
            max_bar_length = max(5, columns - len(bartext) - 1)
            bar_chars = min(init_bar_chars, max_bar_length)
            nchars = int(percentage * (bar_chars - 3) / 100)
            loading_bar = (
                "\r[" + nchars * "=" + ">" + (bar_chars - 3 - nchars) * " " + "]"
            )
            total_out = loading_bar + bartext
            max_out = min(columns, len(total_out))  # don't print beyond columns
            print(total_out[:max_out], end="")

        print(f"Pulling image: {image['repo']}:{image['version']}")
        print("   This may take some time...")

        id_list = []
        id_current = []
        id_total = 0
        t_0 = prev_time = datetime.datetime.now()
        # define pull_image sha256
        pull_image = f"{image['org']}/{image['repo']}@{image['repodigest']}"
        try:
            # Use a lower level pull call to stream the pull
            for line in self.docker.api.pull(pull_image, stream=True, decode=True):
                if "progress" not in line:
                    continue
                line_current = line["progressDetail"]["current"]
                if line["id"] not in id_list:
                    id_list.append(line["id"])
                    id_current.append(line_current)
                    id_total += line["progressDetail"]["total"]
                else:
                    id_current[id_list.index(line["id"])] = line_current
                current_time = datetime.datetime.now()

                # To limit print statements to no more than 1 per second.
                if (current_time - prev_time).total_seconds() < 1:
                    continue

                prev_time = current_time
                update_bar(id_total, sum(id_current), t_0, current_time)

            # Last update of the progress bar:
            update_bar(id_total, sum(id_current), t_0, current_time)
        except Exception as exc:
            raise RuntimeError(
                f"\nException encountered while pulling image {pull_image}\n"\
                    f"Exception: {str(exc)}") from exc

        # avoid erasing the progress bar at the end
        print()

        # When pulling using repodigest sha256, no tag is assigned, so assign one
        docker_image = self.docker.images.get(pull_image)
        docker_image.tag(f"{image['org']}/{image['repo']}", tag=image["version"])
        print("Done!")

    def export_container(self, bucket, filename, repo, tag):
        """
        Export existing container to a tared image file.  After tar file has been created,
        image of container is removed.
        """

        # TODO:
        # Add checks that image was sucessfully saved before removing it?

        container = self.docker.containers.get(bucket["container"])

        # set a long timeout for this - image save takes a while
        default_timeout = self.docker.api.timeout
        self.docker.api.timeout = 60.0 * 60.0 * 24.0

        # image_name = '{}:{}'.format(repo,tag)
        full_repo = f"{bucket['image']['org']}/{repo}"
        image_name = f"{full_repo}:{tag}"

        try:
            # create new image from container
            container.commit(repository=full_repo, tag=tag)

            # save image as *.tar file
            image = self.docker.images.get(image_name)
            out = image.save()

            with gzip.open(str(filename), "wb", compresslevel=1) as f:
                for chunk in out:
                    f.write(chunk)

        except requests.exceptions.ReadTimeout:
            raise RuntimeError("Timeout while exporting bucket!")

        finally:
            # remove image after it has been saved or if a timeout occurs
            self.docker.images.remove(image_name)

            # reset default timeout
            self.docker.api.timeout = default_timeout

    def import_image(self, filename, repo, tag):
        """
        Import an image from a tar file.  Return the image ID.
        """

        with open(str(filename), "rb") as file:
            image = self.docker.images.load(file)[0]

        # add tag
        image.tag(repo, tag)

        return image.id

    def get_container_size(self, bucket):
        """Determine the size of the container (disk space)


        Parameters
        ----------
        bucket : dictionary
            The bucket dictionary with info about the bucket, e.g. the
            container hash id.

        Returns
        -------
        float :
            The size of the container
        """
        # determine the size of the container (disk space)
        # docker container inspect
        # (https://docs.docker.com/engine/reference/commandline/container_inspect/)
        # should be able to be used for this purpose, but it looks like the docker SDK equivilent
        # (APIClient.inspect_container()) does not include fuctionality for the --size flag
        # (https://docker-py.readthedocs.io/en/stable/api.html#module-docker.api.container),
        # so the dict returned does not have size information

        info = self.docker.api.containers(
            all=True, size=True, filters={"id": bucket["container"]}
        )[0]

        return info["SizeRw"] + info["SizeRootFs"]

    def get_container_status(self, bucket):
        """
        Get the status of a particular container.
        """
        container = self.docker.containers.get(bucket["container"])
        container.reload()  # maybe redundant

        return container.status
