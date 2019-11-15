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
        valid_versions = sorted([x['version'] for x in self.program.bucket_manager.valid_cores])
        print('Please choose a version of resen-core.')
        docker_image = self.get_valid_version('>>> Select a version: ',valid_versions)


        # Figure out a port to use
        local_port = self.get_port()
        container_port = local_port

        # Mounting persistent storage
        msg =  'Local directories can be mounted to either /home/jovyan/work or '
        msg += '/home/jovyan/mount/ in a bucket. The /home/jovyan/work location is '
        msg += 'a workspace and /home/jovyan/mount/ is intended for mounting in data. '
        msg += 'You will have rw privileges to everything mounted in work, but can '
        msg += 'specified permissions as either r or rw for directories in mount. Code '
        msg += 'and data created in a bucket can ONLY be accessed outside the bucket or '
        msg += 'after the bucket has been deleted if it is saved in a mounted local directory.'
        print(msg)
        mounts = list()

        # query for mount to work
        answer = self.get_yn('>>> Mount storage to /home/jovyan/work? (y/n): ')
        if answer == 'y':
            local_path = self.get_valid_local_path('>>> Enter local path: ')
            container_path = '/home/jovyan/work'
            permissions = 'rw'
            mounts.append([local_path,container_path,permissions])

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

        success = True
        print("...adding core...")
        status = self.program.add_image(bucket_name,docker_image)
        success = success and status
        if status:
            status = self.program.add_port(bucket_name,local_port,container_port,tcp=True)
            success = success and status
            if status:
                print("...adding mounts...")
                for mount in mounts:
                    status = self.program.add_storage(bucket_name,mount[0],mount[1],mount[2])
                    success = success and status
                    if not status:
                        print("    Failed to mount storage!")

        if success:
            print("Bucket created successfully!")
            if start:
                # bucket should already be running
                # start jupyterlab
                print("...starting jupyterlab...")
                status = self.program.start_jupyter(bucket_name,local_port,container_port)
        else:
            print("Failed to create bucket!")
            status = self.program.remove_bucket(bucket_name)

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

    def do_remove_bucket(self,args):
        """Usage:
remove_bucket bucket_name : Remove bucket named bucket_name."""
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 1:
            print("Syntax Error. Usage: remove_bucket bucket_name")
            return

        bucket_name = inputs[0]
        status = self.program.remove_bucket(bucket_name)

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

        if not bucket_name in self.program.bucket_manager.bucket_names:
            print("ERROR: Bucket with name: %s does not exist!" % bucket_name)
            return False

        # get bucket infomrmation (ports and status)
        # This stuff may be better suited to exist in some kind of "status query" inside of Resen.py
        ind = self.program.bucket_manager.bucket_names.index(bucket_name)
        bucket = self.program.bucket_manager.buckets[ind]
        # This automatically selects the first port in the list of ports
        # TODO: Manage multiple ports assigned to one bucket
        ports = bucket['docker']['port'][0]
        running_status = bucket['docker']['status']


        # if bucket is not running, first start bucket
        if running_status != 'running':
            status = self.program.start_bucket(bucket_name)

        # check if jupyter server running

        # then start jupyter 
        status = self.program.start_jupyter(bucket_name,ports[0],ports[1])


    def do_stop_jupyter(self,args):
        """Usage:
stop_jupyter bucket_name : Stop jupyter on bucket bucket_name."""
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 1:
            print("Syntax Error. Usage: stop_bucket bucket_name")
            return

        bucket_name = inputs[0]
        status = self.program.stop_jupyter(bucket_name)
        status = self.program.stop_bucket(bucket_name)


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
            else:
                # check if bucket with that name already exists
                # Is the only reason create_bucket fails if the name is already take?  May need a more rigerous check
                status = self.program.create_bucket(name)
                if status:
                    return name
                else:
                    print("Cannot use the same name as an existing bucket!")

    def get_valid_version(self,msg,valid_versions):
        print('Available versions: {}'.format(", ".join(valid_versions)))
        while True:
            version = input(msg)
            if version in valid_versions:
                return version
            else:
                print("Invalid version. Available versions: {}".format(", ".join(valid_versions)))


    def get_port(self):
        # this is not atomic, so it is possible that another process might snatch up the port
        port = 9000
        assigned_ports = [y[0] for x in self.program.bucket_manager.buckets for y in x['docker']['port']]

        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                assigned = s.connect_ex(('localhost', port)) == 0
            if not assigned and not port in assigned_ports:
                return port
            else:
                port += 1

    def get_valid_local_path(self,msg):
        while True:
            path = input(msg)
            path = pathlib.PurePosixPath(path)
            if os.path.isdir(str(path)):
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


