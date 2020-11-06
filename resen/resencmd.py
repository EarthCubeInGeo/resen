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
from pathlib import Path

version = resen.__version__


class ResenCmd(cmd.Cmd):

    def __init__(self,resen):
        cmd.Cmd.__init__(self)
        self.prompt = '[resen] >>> '
        self.program = resen


    def do_create(self,args):
        """Usage:
create : Create a new bucket by responding to the prompts provided."""

        # First, ask user for bucket name
        print('Please enter a name for your bucket.')
        bucket_name = self.get_valid_name('>>> Enter bucket name: ')

        # First, ask user about the bucket they want to create
        valid_versions = sorted([x['version'] for x in self.program.valid_cores])
        print('Please choose a version of resen-core.')
        docker_image = self.get_valid_version('>>> Select a version: ',valid_versions)

        # Mounting persistent storage
        msg =  'Local directories can be mounted to /home/jovyan/mount in a bucket.  '
        msg += 'You can specify either r or rw privileges for each directory mounted.  '
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

        try:
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
        except Exception as e:
            print("Bucket creation failed!")
            print(e)
            return

        if start:
            # start bucket
            self.program.start_bucket(bucket_name)
            print("...starting jupyterlab...")
            self.program.start_jupyter(bucket_name)


    def do_remove(self,args):
        """Usage:
remove bucket_name : Remove bucket named bucket_name."""
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


    def do_list(self,args):
        """Usage:
>>> list \t\t: List all resen buckets.
>>> list --names \t: Print only bucket names.
        """
        inputs,num_inputs = self.parse_args(args)
        names_only = False
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
            print("Syntax Error. See 'help status'.")
            return

        status = self.program.list_buckets(names_only=names_only)


    def do_status(self,args):
        """Usage:
>>> status bucket_name \t: Print status of bucket with name "bucket_name"
        """
        inputs,num_inputs = self.parse_args(args)
        names_only = False
        bucket_name = None
        if num_inputs == 1:
            bucket_name = inputs[0]
        else:
            print("Syntax Error. See 'help status'.")
            return

        status = self.program.list_buckets(names_only=names_only,bucket_name=bucket_name)


    def do_start(self,args):
        """Usage:
>>> start bucket_name : Start jupyter on bucket bucket_name
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


    def do_stop(self,args):
        """Usage:
stop bucket_name : Stop jupyter on bucket bucket_name."""
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


    def do_export(self,args):
        """Usage:
export bucket_name: Export bucket to a sharable *.tar file."""
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 1:
            print("Syntax Error. Usage: export_bucket bucket_name")
            return

        bucket_name = inputs[0]

        file_name = self.get_valid_local_path('>>> Enter name for output tar file: ', pathtype='potfile')

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
        rsp = self.get_yn('>>> Are you sure you would like to continue? (y/n): ')
        if rsp == 'n':
            print('Export bucket canceled!')
            return
        else:
            try:
                print('Exporting bucket %s.  This will take several minutes.' % bucket_name)
                self.program.export_bucket(bucket_name, file_name, exclude_mounts=exclude_list, img_repo=img_name, img_tag=img_tag)
            except (ValueError, RuntimeError) as e:
                print(e)
                return


    def do_import(self,args):
        """Usage:
import : Import a bucket from a .tgz file by providing input."""

        print('Please enter a name for your bucket.')
        bucket_name = self.get_valid_name('>>> Enter bucket name: ')

        file_name = self.get_valid_local_path('>>> Enter name for input tar file: ', pathtype='file')

        rsp = self.get_yn(">>> Would you like to keep the default name and tag for the imported image? (y/n): ")
        if rsp=='n':
            img_name = self.get_valid_tag(">>> Image name: ")
            img_tag = self.get_valid_tag(">>> Image tag: ")
        else:
            img_name = None
            img_tag = None

        resen_home_dir = self.program.resen_home_dir
        default_import = os.path.join(resen_home_dir,bucket_name)
        print("The default directory to extract the bucket metadata and mounts to is {}.".format(default_import))
        rsp = self.get_yn(">>> Would you like to specify an alternate directory? (y/n): ")
        if rsp=='y':
            while True:
                extract_dir = input('>>> Enter path to directory: ')
                if not os.path.exists(extract_dir):
                    rsp = self.get_yn(">>> Directory does not exist. Create it? (y/n): ")
                    if rsp=='y':
                        try:
                            os.makedirs(extract_dir)
                            break
                        except:
                            print('Invalid: Directory cannot be created!')
                else:
                    dir_contents = os.listdir(extract_dir)
                    if len(dir_contents) == 0:
                        break
                    print("Invalid: Directory must be empty!")
        else:
            extract_dir = default_import

        # query for aditional mounts
        mounts = list()
        answer = self.get_yn('>>> Mount additional storage to the imported bucket? (y/n): ')
        while answer == 'y':
            local_path = self.get_valid_local_path('>>> Enter local path: ')
            container_path = self.get_valid_container_path('>>> Enter bucket path: ','/home/jovyan/mount')
            permissions = self.get_permissions('>>> Enter permissions (r/rw): ')
            mounts.append([local_path,container_path,permissions])
            answer = self.get_yn('>>> Mount additional storage to /home/jovyan/mount? (y/n): ')

        # should we clean up the bucket archive?
        msg = '>>> Remove %s after successful import? (y/n): ' % str(file_name)
        remove_archive = self.get_yn(msg) == 'y'

        # should we start jupyterlab when done creating bucket?
        msg = '>>> Start bucket and jupyterlab? (y/n): '
        start = self.get_yn(msg) == 'y'

        try:
            print('Importing bucket %s.  This may take several mintues.' % bucket_name)
            print("...extracting bucket...")
            self.program.import_bucket(bucket_name,file_name,extract_dir=extract_dir,
                                       img_repo=img_name,img_tag=img_tag,remove_image_file=True)
            print("...adding ports...")
            self.program.add_port(bucket_name)
            print("...adding mounts...")
            for mount in mounts:
                self.program.add_storage(bucket_name,mount[0],mount[1],mount[2])
            self.program.create_container(bucket_name, give_sudo=False)
        except (ValueError, RuntimeError) as e:
            print('Bucket import failed!')
            print(e)
            return

        if start:
            # start bucket
            try:
                self.program.start_bucket(bucket_name)
                print("...starting jupyterlab...")
                self.program.start_jupyter(bucket_name)
            except Exception as e:
                print(e)
                return

        if remove_archive:
            print("Deleting %s as requested." % str(file_name))
            os.remove(file_name)

    def do_update(self,arg):
        """update : Update default list of resen-cores available."""
        self.program.update_core_list()

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
            if not name:
                print("Please enter a vaild name.")
            elif ' ' in name:
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


    def get_valid_local_path(self,msg,pathtype='directory'):
        while True:
            path = input(msg)
            path = pathlib.Path(path)

            # define different checks for different types of path
            check = {'directory':path.is_dir(),'file':path.is_file(),'potfile':path.parent.is_dir()}
            if check[pathtype]:
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
