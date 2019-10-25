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
import cmd         # for command line interface
import shlex
import resen
import socket
import pathlib
import os

version = resen.__version__


class ResenCmd(cmd.Cmd):

    def __init__(self,resen):
        cmd.Cmd.__init__(self)
        self.prompt = '[resen] >>> '
        self.program = resen
        # get current state of buckets

    # --------------- resen stuff --------------------
    # try to create a bucket by guiding user
    # if
    def do_create_bucket(self,args):
        """Usage:
create_bucket : Create a new bucket by responding to the prompts provided."""

        # First, ask user for bucket name
        print('Please enter a name for your bucket.')
        bucket_name = self.get_valid_name('>>> Enter bucket name: ')

        # First, ask user about the bucket they want to create
        # resen-core version?
        valid_versions = sorted([x['version'] for x in self.program.valid_cores])
        print('Please choose a version of resen-core.')
        docker_image = self.get_valid_version('>>> Select a version: ',valid_versions)


        # Mounting persistent storage
        msg =  'Local directories can be mounted to /home/jovyan/mount in a bucket.  '
        msg += 'You can specify either r or rw privileges  for each directory mounted.  '
        msg += 'Nothing mounted will be included in an exported bucket.  Any scripts, data,'
        msg += 'ect. that you would like to persist in an exported bucket MUST be copied '
        msg += 'into another part of the bucket.'
        print(msg)
        mounts = list()

        # query for mounts to mount
        answer = self.get_yn('>>> Mount storage to /home/jovyan/mount? (y/n): ')
        while answer == 'y':
            local_path = self.get_valid_local_path('>>> Enter local path: ')
            container_path = self.get_valid_container_path('>>> Enter bucket path: ','/home/jovyan/mount')
            permissions = self.get_permissions('>>> Enter permissions (r/rw): ')
            mounts.append([local_path,container_path,permissions])
            answer = self.get_yn('>>> Mount additional storage to /home/jovyan/mount? (y/n): ')

        # should we start jupyterlab when done creating bucket?
        msg = '>>> Start bucket and jupyterlab? (y/n): '
        start = self.get_yn(msg) == 'y'

        # try:
        self.program.create_bucket(bucket_name)
        print("...adding core...")
        self.program.set_image(bucket_name,docker_image)
        print("...adding ports...")
        self.program.add_port(bucket_name)
        print("...adding mounts...")
        for mount in mounts:
            self.program.add_storage(bucket_name,mount[0],mount[1],mount[2])
        self.program.create_container(bucket_name)
        print("Bucket created successfully!")
        # except Exception as e:
        #     print("Bucket creation failed!")
        #     print(e)
        #     return

        if start:
            # start bucket
            self.program.start_bucket(bucket_name)
            print("...starting jupyterlab...")
            self.program.start_jupyter(bucket_name)


    def do_remove_bucket(self,args):
        """Usage:
remove_bucket bucket_name : Remove bucket named bucket_name."""
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 1:
            print("Syntax Error. Usage: remove_bucket bucket_name")
            return

        bucket_name = inputs[0]
        try:
            self.program.remove_bucket(bucket_name)
        except (ValueError, RuntimeError) as e:
            print(e)
            return

    def do_status(self,args):
        """Usage:
>>> status \t\t: Print the status of all resen buckets.
>>> status --names \t: Print only bucket names.
>>> status bucket_name \t: Print status of bucket with name "bucket_name"
        """
        inputs,num_inputs = self.parse_args(args)
        names_only = False
        bucket_name = None
        if num_inputs == 0:
            pass
        elif num_inputs == 1:
            if inputs[0][0] == '-':
                if inputs[0] == '--names':
                    names_only = True
                else:
                    print("Syntax Error. See 'help status'.")
                    return
            else:
                bucket_name = inputs[0]
        else:
            print("Syntax Error. See 'help status'.")
            return

        status = self.program.list_buckets(names_only=names_only,bucket_name=bucket_name)

    def do_start_jupyter(self,args):
        """Usage:
>>> start_jupyter bucket_name : Start jupyter on bucket bucket_name
        """
        inputs,num_inputs = self.parse_args(args)

        if num_inputs == 1:
            pass
        else:
            print("Syntax Error. See 'help start_jupyter'.")
            return


        # get bucket name from input
        bucket_name = inputs[0]

        try:
            self.program.start_bucket(bucket_name) # does nothing if bucket already started
            self.program.start_jupyter(bucket_name)
        except (ValueError, RuntimeError) as e:
            print(e)
            return


    def do_stop_jupyter(self,args):
        """Usage:
stop_jupyter bucket_name : Stop jupyter on bucket bucket_name."""
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 1:
            print("Syntax Error. Usage: stop_bucket bucket_name")
            return

        bucket_name = inputs[0]
        try:
            self.program.stop_jupyter(bucket_name)
            self.program.stop_bucket(bucket_name)
        except (ValueError, RuntimeError) as e:
            print(e)
            return


    def do_export_bucket(self,args):
        """Usage:
export_bucket bucket_name: Export bucket to a sharable *.tar file."""
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 1:
            print("Syntax Error. Usage: export_bucket bucket_name")
            return

        bucket_name = inputs[0]

        file_name = self.get_valid_local_path('>>> Enter name for output tgz file: ', file=True)

        print('By default, the output image will be named "{}" and tagged "latest".'.format(bucket_name.lower()))
        rsp = self.get_yn(">>> Would you like to change the name and tag? (y/n): ")
        if rsp=='y':
            img_name = self.get_valid_tag(">>> Image name: ")
            img_tag = self.get_valid_tag(">>> Image tag: ")
        else:
            img_name = None
            img_tag = None

        report = self.program.bucket_diskspace(bucket_name)

        # identify storage locations to exclude
        exclude_list = []
        total_size = 0.
        if len(report['storage']) > 0:
            print("The following local directories are mounted to the bucket (total %s MB):" % int(report['total_storage']))
            for mount in report['storage']:
                print(mount['local'])
            msg = '>>> Would you like to include all of these in the exported bucket? (y/n): '
            rsp = self.get_yn(msg)
            if rsp == 'n':
                for mount in report['storage']:
                    rsp = self.get_yn(">>> Include %s [%s MB]? (y/n): " % (mount['local'], mount['size']))
                    if rsp == 'n':
                        exclude_list.append(mount['local'])
                    else:
                        total_size += mount['size']
            else:
                total_size = report['total_storage']

        # Find the maximum output file size and required disk space for bucket export
        output = report['container'] + total_size
        required = max(report['container']*3., output*2.)

        print('This export could require up to %s MB of disk space to complete and will produce an output file up to %s MB.' % (int(required), int(output)))
        # msg = '>>> Are you sure you would like to continue? (y/n): '
        rsp = self.get_yn('>>> Are you sure you would like to continue? (y/n): ')


        try:
            print('Exporting bucket %s.  This will take several mintues.' % bucket_name)
            self.program.export_bucket(bucket_name, file_name, exclude_mounts=exclude_list, img_name=img_name, img_tag=img_tag)
        except (ValueError, RuntimeError) as e:
            print(e)
            return


    def do_import_bucket(self,args):
        """Usage:
import_bucket : Import a bucket from a .tgz file by providing input."""
        print('Please enter a name for your bucket.')
        bucket_name = self.get_valid_name('>>> Enter bucket name: ')

        file_name = self.get_valid_local_path('>>> Enter name for input tar file: ', file=True)

        try:
            self.program.import_bucket(bucket_name, file_name)
            self.program.add_port(bucket_name)
            self.program.create_container(bucket_name, sudo=False)
        except (ValueError, RuntimeError) as e:
            print(e)
            return

        # TODO:
        # Have prompt for user to start bucket automatically?
        # success = True
        # print("...adding core...")
        # status = self.program.add_image(bucket_name,docker_image)
        # success = success and status
        # if status:
        #     status = self.program.add_port(bucket_name,local_port,container_port,tcp=True)
        #     success = success and status
        #     if status:
        #         print("...adding mounts...")
        #         for mount in mounts:
        #             status = self.program.add_storage(bucket_name,mount[0],mount[1],mount[2])
        #             success = success and status
        #             if not status:
        #                 print("    Failed to mount storage!")

        # if success:
        #     print("Bucket created successfully!")
        #     if start:
        #         # start bucket
        #         status = self.program.start_bucket(bucket_name)
        #         if not status:
        #             return
        #         # start jupyterlab
        #         print("...starting jupyterlab...")
        #         status = self.program.start_jupyter(bucket_name,local_port,container_port)
        # else:
        #     print("Failed to create bucket!")
        #     status = self.program.remove_bucket(bucket_name)

#     def do_start_bucket(self,args):
#         """Usage:
# start_bucket bucket_name : Start bucket named bucket_name."""
#         inputs,num_inputs = self.parse_args(args)
#         if num_inputs != 1:
#             print("Syntax Error. Usage: start_bucket bucket_name")
#             return

#         bucket_name = inputs[0]
#         status = self.program.start_bucket(bucket_name)

#     def do_stop_bucket(self,args):
#         """Usage:
# stop_bucket bucket_name : Stop bucket named bucket_name."""
#         inputs,num_inputs = self.parse_args(args)
#         if num_inputs != 1:
#             print("Syntax Error. Usage: stop_bucket bucket_name")
#             return

#         bucket_name = inputs[0]
#         status = self.program.stop_bucket(bucket_name)

#     def do_add_storage(self,args):
#         """Usage:
# >>> add_storage bucket_name local_path container_path permissions : Add a local_path storage location available at container_path.
# use "" for paths with spaces in them
# - permissions should be 'r' or 'rw'
#         """
#         inputs,num_inputs = self.parse_args(args)
#         if num_inputs != 4:
#             print("Syntax Error. Usage: add_storage bucket_name local_path container_path permissions")
#             return
#         bucket_name = inputs[0]
#         local_path = inputs[1]
#         container_path = inputs[2]
#         permissions = inputs[3]

#         status = self.program.add_storage(bucket_name,local_path,container_path,permissions)

#     def do_remove_storage(self,args):
#         """Usage:
# >>> remove_storage bucket_name local_path : Remove the local_path storage location in bucket bucket_name.
# use "" for paths with spaces in them
#         """
#         inputs,num_inputs = self.parse_args(args)
#         if num_inputs != 2:
#             print("Syntax Error. Usage: remove_storage bucket_name local_path")
#             return
#         bucket_name = inputs[0]
#         local_path = inputs[1]

#         status = self.program.remove_storage(bucket_name,local_path)

#     def do_add_port(self,args):
#         """Usage:
# >>> add_port bucket_name local_port container_port\t: Map container_port available at local_port.
# >>> add_port bucket_name local_port container_port --udp\t: Map container_port available at local_port.
#         """
#         inputs,num_inputs = self.parse_args(args)

#         tcp = True
#         if num_inputs == 3:
#             pass
#         elif num_inputs == 4:
#             if inputs[3][0] == '-':
#                 if inputs[3] == '--udp':
#                     tcp = False
#                 else:
#                     print("Syntax Error. See 'help add_port'")
#                     return
#         else:
#             print("Syntax Error. See 'help add_port'")
#             return

#         bucket_name = inputs[0]
#         local_port = int(inputs[1])
#         container_port = int(inputs[2])

#         status = self.program.add_port(bucket_name,local_port,container_port,tcp=tcp)

#     def do_remove_port(self,args):
#         """Usage:
# >>> remove_port bucket_name local_port : Remove the local_port mapping from bucket bucket_name.
#         """
#         inputs,num_inputs = self.parse_args(args)
#         if num_inputs != 2:
#             print("Syntax Error. Usage: remove_port bucket_name local_port")
#             return
#         bucket_name = inputs[0]
#         local_port = int(inputs[1])

#         status = self.program.remove_port(bucket_name,local_port)

    # def do_import(self):
    #     """import : Print the status of all resen buckets."""
    #     pass

    # def do_export(self):
    #     """export : Print the status of all resen buckets."""
    #     pass

    # def do_freeze(self):
    #     """freeze : Print the status of all resen buckets."""
    #     pass


    def do_quit(self,arg):
        """quit : Terminates the application."""
        # turn off currently running buckets or leave them running? leave running but
        print("Exiting")
        return True

    do_exit = do_quit
    do_EOF = do_quit

    def emptyline(self):
        pass

    def default(self,line):
        print("Unrecognized command: '%s'. Use 'help'." % (str(line)))
        pass

    def parse_args(self,args):
        inputs = shlex.split(args)
        num_inputs = len(inputs)
        return inputs,num_inputs

    # The following functions are highly specialized

    def get_yn(self,msg):
        valid_inputs = ['y', 'n']
        while True:
            answer = input(msg)
            if answer in valid_inputs:
                return answer
            else:
                print("Invalid input. Valid input are {} or {}.".format(valid_inputs[0],valid_inputs[1]))

    def get_valid_name(self,msg):
        print('Valid names may not contain spaces and must start with a letter and be less than 20 characters long.')
        while True:
            name = input(msg)

            # check if bucket_name has spaces in it and is greater than 20 characters
            # also bucket name must start with a letter
            if ' ' in name:
                print("Bucket names may not contain spaces.")
            elif len(name) > 20:
                print("Bucket names must be less than 20 characters.")
            elif not name[0].isalpha():
                print("Bucket names must start with an alphabetic character.")
            elif name in self.program.bucket_names:
                print("Cannot use the same name as an existing bucket!")
            else:
                return name


    def get_valid_version(self,msg,valid_versions):
        print('Available versions: {}'.format(", ".join(valid_versions)))
        while True:
            version = input(msg)
            if version in valid_versions:
                return version
            else:
                print("Invalid version. Available versions: {}".format(", ".join(valid_versions)))


    def get_valid_local_path(self,msg,file=False):
        while True:
            path = input(msg)
            path = pathlib.PurePosixPath(path)
            if os.path.isdir(str(path)):
                return str(path)
            elif file and os.path.isdir(str(path.parent)):
                return str(path)
            else:
                print('Cannot find local path entered.')

    def get_valid_container_path(self,msg,base):
        while True:
            path = input(msg)
            path = pathlib.PurePosixPath(path)
            if base in [str(x) for x in list(path.parents)]:
                return str(path)
            else:
                print("Invalid path. Must start with: {}".format(base))

    def get_permissions(self,msg):
        valid_inputs = ['r', 'rw']
        while True:
            answer = input(msg)
            if answer in valid_inputs:
                return answer
            else:
                print("Invalid input. Valid input are {} or {}.".format(valid_inputs[0],valid_inputs[1]))

    def get_valid_tag(self,msg):
        while True:
            tag = input(msg)

            # check if bucket_name has spaces in it and is greater than 20 characters
            # also bucket name must start with a letter
            if ' ' in tag:
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


    width = 48
    intro = list()
    intro.append('    ___ ___ ___ ___ _  _ ')
    intro.append('   | _ \ __/ __| __| \| |')
    intro.append('   |   / _|\__ \ _|| .` |')
    intro.append('   |_|_\___|___/___|_|\_|')
    intro.append('')
    intro.append('Resen %s -- Reproducible Software Environment' % version)
    intro.append('')
    intro = '\n'.join(intro)

    try:
        res = resen.Resen()
    except RuntimeError:
        print("ERROR: another instance of Resen is already running!")
        sys.exit(1)

    ResenCmd(res).cmdloop(intro)


if __name__ == '__main__':

    main()
