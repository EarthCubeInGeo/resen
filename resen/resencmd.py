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

import sys
import cmd  # for command line interface
import shlex
import pathlib
import os
import resen

VERSION = resen.__version__


class ResenCmd(cmd.Cmd):
    def __init__(self, program_name):
        cmd.Cmd.__init__(self)
        self.prompt = "[resen] >>> "
        self.program = program_name

    def do_create(self, args):
        """Usage:
        create : Create a new bucket by responding to the prompts provided."""

        _, num_inputs = self.parse_args(args)
        if num_inputs != 0:
            print("WARNING: 'create' takes no args. See 'help create'.")
            return

        # First, ask user for bucket name
        print("Please enter a name for your bucket.")
        bucket_name = self.get_valid_name(">>> Enter bucket name: ")

        # First, ask user about the bucket they want to create
        valid_versions = sorted([x["version"] for x in self.program.valid_cores])
        if len(valid_versions) == 0:
            print(
                "WARNING: No valid versions of resen-core are available! Please run"
                ' the "update" command to pull resen cores from online.'
            )
            return
        print("Please choose a version of resen-core.")
        docker_image = self.get_valid_version(">>> Select a version: ", valid_versions)

        # Mounting persistent storage
        msg = "Local directories can be mounted to /home/jovyan/mount in a bucket.  "
        msg += "You can specify either r or rw privileges for each directory mounted.  "
        print(msg)
        mounts = []

        # query for mounts to mount
        answer = self.get_yn(">>> Mount storage to /home/jovyan/mount? (y/n): ")
        while answer == "y":
            local_path = self.get_valid_local_path(">>> Enter local path: ")
            container_path = self.get_valid_container_path(
                ">>> Enter bucket path: ", "/home/jovyan/mount"
            )
            permissions = self.get_permissions(">>> Enter permissions (r/rw): ")
            mounts.append([local_path, container_path, permissions])
            answer = self.get_yn(
                ">>> Mount additional storage to /home/jovyan/mount? (y/n): "
            )

        # should we start jupyterlab when done creating bucket?
        msg = ">>> Start bucket and jupyterlab? (y/n): "
        start = self.get_yn(msg) == "y"

        try:
            self.program.create_bucket(bucket_name)
            print("...adding core...")
            self.program.set_image(bucket_name, docker_image)
            print("...adding ports...")
            self.program.add_port(bucket_name)
            print("...adding mounts...")
            for mount in mounts:
                self.program.add_storage(bucket_name, mount[0], mount[1], mount[2])
            self.program.create_container(bucket_name)
            print("Bucket created successfully!")
        except Exception as exc:
            print("Bucket creation failed!")
            print(exc)
            return

        if start:
            # start bucket
            self.program.start_bucket(bucket_name)
            print("...starting jupyterlab...")
            self.program.start_jupyter(bucket_name)

    def do_remove(self, args):
        """Usage:
        remove bucket_name : Remove bucket named bucket_name."""
        inputs, num_inputs = self.parse_args(args)
        if num_inputs != 1:
            print("Syntax Error. See 'help remove'.")
            return

        bucket_name = inputs[0]
        try:
            self.program.remove_bucket(bucket_name)
        except (ValueError, RuntimeError) as exc:
            print(exc)
            return

    def do_list(self, args):
        """Usage:
        >>> list \t\t: List all resen buckets.
        >>> list --names \t: Print only bucket names.
        """
        inputs, num_inputs = self.parse_args(args)
        names_only = False
        if num_inputs == 0:
            pass
        elif num_inputs == 1:
            if inputs[0][0] == "-":
                if inputs[0] == "--names":
                    names_only = True
                else:
                    print("Syntax Error. See 'help status'.")
                    return
        else:
            print("Syntax Error. See 'help status'.")
            return

        self.program.list_buckets(names_only=names_only)

    def do_status(self, args):
        """Usage:
        >>> status bucket_name \t: Print status of bucket with name "bucket_name"
        """
        inputs, num_inputs = self.parse_args(args)
        names_only = False
        bucket_name = None
        if num_inputs == 1:
            bucket_name = inputs[0]
        else:
            print("Syntax Error. See 'help status'.")
            return

        self.program.list_buckets(names_only=names_only, bucket_name=bucket_name)

    def do_start(self, args):
        """Usage:
        >>> start bucket_name : Start jupyter on bucket bucket_name
        """
        inputs, num_inputs = self.parse_args(args)

        if num_inputs != 1:
            print("Syntax Error. See 'help start'.")
            return

        # get bucket name from input
        bucket_name = inputs[0]
        try:
            self.program.start_bucket(
                bucket_name
            )  # does nothing if bucket already started
            self.program.start_jupyter(bucket_name)
        except (ValueError, RuntimeError) as exc:
            print(exc)
            return

    def do_stop(self, args):
        """Usage:
        stop bucket_name : Stop jupyter on bucket bucket_name."""
        inputs, num_inputs = self.parse_args(args)
        if num_inputs != 1:
            print("Syntax Error. See 'help stop'.")
            return

        bucket_name = inputs[0]
        try:
            self.program.stop_jupyter(bucket_name)
            self.program.stop_bucket(bucket_name)
        except (ValueError, RuntimeError) as exc:
            print(exc)
            return

    def do_export(self, args):
        """Usage:
        export bucket_name: Export bucket to a sharable *.tar file."""
        inputs, num_inputs = self.parse_args(args)
        if num_inputs != 1:
            print("Syntax Error. See 'help export'.")
            return

        bucket_name = inputs[0]

        file_name = self.get_valid_local_path(
            ">>> Enter name for output tar file: ", pathtype="potfile"
        )

        print(
            "By default, the output image will be named "
            f"'{bucket_name.lower()}' and tagged 'latest'."
        )
        rsp = self.get_yn(">>> Would you like to change the name and tag? (y/n): ")
        if rsp == "y":
            img_name = self.get_valid_tag(">>> Image name: ")
            img_tag = self.get_valid_tag(">>> Image tag: ")
        else:
            img_name = None
            img_tag = None

        report = self.program.bucket_diskspace(bucket_name)

        # identify storage locations to exclude
        exclude_list = []
        total_size = 0.0
        if len(report["storage"]) > 0:
            print(
                "The following local directories are mounted to the bucket (total "
                f"{int(report['total_storage'])} MB):"
            )
            for mount in report["storage"]:
                print(mount["local"])
            msg = ">>> Would you like to include all of these in the exported bucket? (y/n): "
            rsp = self.get_yn(msg)
            if rsp == "n":
                for mount in report["storage"]:
                    rsp = self.get_yn(
                        f">>> Include {mount['local']} [{mount['size']} MB]? (y/n): "
                    )
                    if rsp == "n":
                        exclude_list.append(mount["local"])
                    else:
                        total_size += mount["size"]
            else:
                total_size = report["total_storage"]

        # Find the maximum output file size and required disk space for bucket export
        output = report["container"] + total_size
        required = max(report["container"] * 3.0, output * 2.0)

        print(
            f"This export could require up to {int(required)} MB of disk space to complete "
            "and will produce an output file up to {int(output)} MB."
        )
        rsp = self.get_yn(">>> Are you sure you would like to continue? (y/n): ")
        if rsp == "n":
            print("Export bucket canceled!")
            return
        try:
            print(f"Exporting bucket {bucket_name}. This will take several minutes.")
            self.program.export_bucket(
                bucket_name,
                file_name,
                exclude_mounts=exclude_list,
                img_repo=img_name,
                img_tag=img_tag,
            )
        except (ValueError, RuntimeError) as exc:
            print(exc)
            return

    def do_import(self, args):
        """Usage:
        import : Import a bucket from a .tgz file by providing input."""

        _, num_inputs = self.parse_args(args)
        if num_inputs != 0:
            print("WARNING: 'import' takes no args. See 'help import'.")
            return

        print("Please enter a name for your bucket.")
        bucket_name = self.get_valid_name(">>> Enter bucket name: ")

        file_name = self.get_valid_local_path(
            ">>> Enter name for input tar file: ", pathtype="file"
        )

        rsp = self.get_yn(
            ">>> Would you like to keep the default name and tag for the imported image? (y/n): "
        )
        if rsp == "n":
            img_name = self.get_valid_tag(">>> Image name: ")
            img_tag = self.get_valid_tag(">>> Image tag: ")
        else:
            img_name = None
            img_tag = None

        resen_home_dir = self.program.resen_home_dir
        default_import = os.path.join(resen_home_dir, bucket_name)
        print(
            "The default directory to extract the bucket metadata and mounts to is "
            f"{default_import}."
        )
        rsp = self.get_yn(
            ">>> Would you like to specify an alternate directory? (y/n): "
        )
        if rsp == "y":
            while True:
                extract_dir = input(">>> Enter path to directory: ")
                if not os.path.exists(extract_dir):
                    rsp = self.get_yn(
                        ">>> Directory does not exist. Create it? (y/n): "
                    )
                    if rsp == "y":
                        try:
                            os.makedirs(extract_dir)
                            break
                        except Exception:
                            print("Invalid: Directory cannot be created!")
                else:
                    dir_contents = os.listdir(extract_dir)
                    if len(dir_contents) == 0:
                        break
                    print("Invalid: Directory must be empty!")
        else:
            extract_dir = default_import

        # query for aditional mounts
        mounts = []
        answer = self.get_yn(
            ">>> Mount additional storage to the imported bucket? (y/n): "
        )
        while answer == "y":
            local_path = self.get_valid_local_path(">>> Enter local path: ")
            container_path = self.get_valid_container_path(
                ">>> Enter bucket path: ", "/home/jovyan/mount"
            )
            permissions = self.get_permissions(">>> Enter permissions (r/rw): ")
            mounts.append([local_path, container_path, permissions])
            answer = self.get_yn(
                ">>> Mount additional storage to /home/jovyan/mount? (y/n): "
            )

        # should we clean up the bucket archive?
        msg = f">>> Remove {str(file_name)} after successful import? (y/n): "
        remove_archive = self.get_yn(msg) == "y"

        # should we start jupyterlab when done creating bucket?
        msg = ">>> Start bucket and jupyterlab? (y/n): "
        start = self.get_yn(msg) == "y"

        try:
            print(f"Importing bucket {bucket_name}. This may take several mintues.")
            print("...extracting bucket...")
            self.program.import_bucket(
                bucket_name,
                file_name,
                extract_dir=extract_dir,
                img_repo=img_name,
                img_tag=img_tag,
                remove_image_file=True,
            )
            print("...adding ports...")
            self.program.add_port(bucket_name)
            print("...adding mounts...")
            for mount in mounts:
                self.program.add_storage(bucket_name, mount[0], mount[1], mount[2])
            self.program.create_container(bucket_name, give_sudo=False)
        except (ValueError, RuntimeError) as exc:
            print("Bucket import failed!")
            print(exc)
            return

        if start:
            # start bucket
            try:
                self.program.start_bucket(bucket_name)
                print("...starting jupyterlab...")
                self.program.start_jupyter(bucket_name)
            except Exception as exc:
                print(exc)
                return

        if remove_archive:
            print(f"Deleting {str(file_name)} as requested.")
            os.remove(file_name)

    def do_update(self, args):
        """update : Update default list of resen-cores available."""

        _, num_inputs = self.parse_args(args)
        if num_inputs != 0:
            print("WARNING: 'update' takes no args. See 'help update'.")
            return

        self.program.update_core_list()

    def do_change_settings(self, args):
        """update : Change your docker settings for Windows."""

        _, num_inputs = self.parse_args(args)
        if num_inputs != 0:
            print(
                "WARNING: 'change_settings' takes no args. See 'help change_settings'."
            )
            return

        self.program.update_docker_settings()

    def do_quit(self, args):
        """quit : Terminates the application."""
        # TODO: turn off currently running buckets or leave them running? leave running but

        _, num_inputs = self.parse_args(args)
        if num_inputs != 0:
            print("WARNING: 'quit' takes no args. See 'help quit'.")
            return False

        print("Exiting")
        return True  # We must return True for RESEN to quit!

    def emptyline(self):
        pass

    def default(self, line):
        print(f"Unrecognized command: '{str(line)}'. Use 'help'.")

    def parse_args(self, args):
        inputs = shlex.split(args)
        num_inputs = len(inputs)
        return inputs, num_inputs

    # The following functions are highly specialized

    def get_yn(self, msg):
        valid_inputs = ["y", "n"]
        while True:
            answer = input(msg)
            if answer in valid_inputs:
                return answer
            else:
                print(
                    f"Invalid input. Valid input are {valid_inputs[0]} or {valid_inputs[1]}."
                )

    def get_valid_name(self, msg):
        print(
            "Valid names may not contain spaces and must start with a letter and be "
            "less than 20 characters long."
        )
        while True:
            name = input(msg)

            # check if bucket_name has spaces in it and is greater than 20 characters
            # also bucket name must start with a letter
            if not name:
                print("Please enter a vaild name.")
            elif " " in name:
                print("Bucket names may not contain spaces.")
            elif len(name) > 20:
                print("Bucket names must be less than 20 characters.")
            elif not name[0].isalpha():
                print("Bucket names must start with an alphabetic character.")
            elif name in self.program.bucket_names:
                print("Cannot use the same name as an existing bucket!")
            else:
                return name

    def get_valid_version(self, msg, valid_versions):
        print(f"Available versions: {', '.join(valid_versions)}")
        while True:
            version = input(msg)
            if version in valid_versions:
                return version
            print(f"Invalid version. Available versions: {', '.join(valid_versions)}")

    def get_valid_local_path(self, msg, pathtype="directory"):
        while True:
            path = input(msg)
            path = pathlib.Path(path)

            # define different checks for different types of path
            check = {
                "directory": path.is_dir(),
                "file": path.is_file(),
                "potfile": path.parent.is_dir(),
            }
            if check[pathtype]:
                return str(path)
            print("Cannot find local path entered.")

    def get_valid_container_path(self, msg, base):
        while True:
            path = input(msg)
            path = pathlib.PurePosixPath(path)
            if base in [str(x) for x in list(path.parents)]:
                return str(path)
            print(f"Invalid path. Must start with: {base}")

    def get_permissions(self, msg):
        valid_inputs = ["r", "rw"]
        while True:
            answer = input(msg)
            if answer in valid_inputs:
                return answer
            print(
                f"Invalid input. Valid input are {valid_inputs[0]} or {valid_inputs[1]}."
            )

    def get_valid_tag(self, msg):
        while True:
            tag = input(msg)

            # check if bucket_name has spaces in it and is greater than 20 characters
            # also bucket name must start with a letter
            if " " in tag:
                print("Tags may not contain spaces.")
            elif len(tag) > 128:
                print("Tags must be less than 128 characters.")
            elif not tag[0].isalpha():
                print("Tags must start with an alphabetic character.")
            elif not tag.islower():
                print("Tags may only contain lower case letters.")
            else:
                return tag


def main():
    # width = 45
    # intro = list()
    # # generated with http://patorjk.com/software/taag/#p=display&f=Big&t=RESEN
    # intro.append(' _____  ______  _____ ______ _   _ '.center(width))
    # intro.append('|  __ \|  ____|/ ____|  ____| \ | |'.center(width))
    # intro.append('| |__) | |__  | (___ | |__  |  \| |'.center(width))
    # intro.append('|  _  /|  __|  \___ \|  __| | . ` |'.center(width))
    # intro.append('| | \ \| |____ ____) | |____| |\  |'.center(width))
    # intro.append('|_|  \_\______|_____/|______|_| \_|'.center(width))
    # intro.append(''.center(width))

    intro = []
    intro.append("    ___ ___ ___ ___ _  _ ")
    intro.append("   | _ \ __/ __| __| \| |")
    intro.append("   |   / _|\__ \ _|| .` |")
    intro.append("   |_|_\___|___/___|_|\_|")
    intro.append("")
    intro.append(f"Resen {VERSION} -- Reproducible Software Environment")
    intro.append("")
    intro = "\n".join(intro)

    try:
        res = resen.Resen()
    except RuntimeError:
        print("ERROR: another instance of Resen is already running!")
        sys.exit(1)

    ResenCmd(res).cmdloop(intro)


if __name__ == "__main__":
    main()
