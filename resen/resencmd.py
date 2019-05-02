#!/usr/bin/env python
####################################################################
#
#  Title: resen
#
#  Author: asreimer
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

version = resen.__version__


class ResenCmd(cmd.Cmd):

    def __init__(self,resen):
        cmd.Cmd.__init__(self)
        self.prompt = '[resen] >>> '
        self.program = resen
        # get current state of buckets

    # --------------- resen stuff --------------------
    def do_create_bucket(self,args):
        """Usage:
create_bucket bucket_name : Create a new bucket with name bucket_name. Must start with a letter, <=20 characters, and no spaces."""
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 1:
            print("Syntax Error")
            return

        bucket_name = inputs[0]
        # check if bucket_name has spaces in it and is greater than 20 characters
        # also bucket name must start with a letter
        if ' ' in bucket_name or len(bucket_name) > 20 or not bucket_name[0].isalpha():
            print("Syntax Error")
            return
        status = self.program.create_bucket(bucket_name)

    def do_start_bucket(self,args):
        """Usage:
start_bucket bucket_name : Start bucket named bucket_name."""
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 1:
            print("Syntax Error")
            return

        bucket_name = inputs[0]
        status = self.program.start_bucket(bucket_name)

    def do_stop_bucket(self,args):
        """Usage:
stop_bucket bucket_name : Stop bucket named bucket_name."""
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 1:
            print("Syntax Error")
            return

        bucket_name = inputs[0]
        status = self.program.stop_bucket(bucket_name)

    def do_remove_bucket(self,args):
        """Usage:
remove_bucket bucket_name : Remove bucket named bucket_name."""
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 1:
            print("Syntax Error")
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
                    print("Syntax Error")
                    return
            else:
                bucket_name = inputs[0]
        else:
            print("Syntax Error")
            return
        
        status = self.program.list_buckets(names_only=names_only,bucket_name=bucket_name)

    def do_start_jupyter(self,args):
        """Usage:
>>> start_jupyter bucket_name local_port bucket_port\t: Start a jupyter notebook server on port bucket_port available at local_port.
>>> start_jupyter bucket_name local_port bucket_port --lab\t: Start a jupyter lab server on port bucket_port available at local_port.
        """
        inputs,num_inputs = self.parse_args(args)
        lab = False
        if num_inputs == 3:
            pass
        elif num_inputs == 4:
            if inputs[3][0] == '-':
                if inputs[3] == '--lab':
                    lab = True
                else:
                    print("Syntax Error")
                    return
        else:
            print("Syntax Error")
            return

        bucket_name = inputs[0]
        local_port = int(inputs[1])
        bucket_port = int(inputs[2])

        status = self.program.start_jupyter(bucket_name,local_port,bucket_port,lab=lab)

    def do_add_image(self,args):
        """Usage:
>>> add_image bucket_name image_name : Add a resen-core to bucket names bucket_name.
        """
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 2:
            print("Syntax Error")
            return
        bucket_name = inputs[0]
        docker_image = inputs[1]

        status = self.program.add_image(bucket_name,docker_image)

    def do_add_storage(self,args):
        """Usage:
>>> add_storage bucket_name local_path container_path permissions : Add a local_path storage location available at container_path.
use "" for paths with spaces in them
- permissions should be 'r' or 'rw'
        """
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 4:
            print("Syntax Error")
            return
        bucket_name = inputs[0]
        local_path = inputs[1]
        container_path = inputs[2]
        permissions = inputs[3]

        status = self.program.add_storage(bucket_name,local_path,container_path,permissions)

    def do_remove_storage(self,args):
        """Usage:
>>> remove_storage bucket_name local_path : Remove the local_path storage location in bucket bucket_name.
use "" for paths with spaces in them
        """
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 2:
            print("Syntax Error")
            return
        bucket_name = inputs[0]
        local_path = inputs[1]

        status = self.program.remove_storage(bucket_name,local_path)

    def do_add_port(self,args):
        """Usage:
>>> add_port bucket_name local_port container_port\t: Map container_port available at local_port.
>>> add_port bucket_name local_port container_port --udp\t: Map container_port available at local_port.
        """
        inputs,num_inputs = self.parse_args(args)

        tcp = True
        if num_inputs == 3:
            pass
        elif num_inputs == 4:
            if inputs[3][0] == '-':
                if inputs[3] == '--udp':
                    tcp = False
                else:
                    print("Syntax Error")
                    return
        else:
            print("Syntax Error")
            return

        bucket_name = inputs[0]
        local_port = int(inputs[1])
        container_port = int(inputs[2])

        status = self.program.add_port(bucket_name,local_port,container_port,tcp=tcp)

    def do_remove_port(self,args):
        """Usage:
>>> remove_port bucket_name local_port : Remove the local_port mapping from bucket bucket_name.
        """
        inputs,num_inputs = self.parse_args(args)
        if num_inputs != 2:
            print("Syntax Error")
            return
        bucket_name = inputs[0]
        local_port = int(inputs[1])

        status = self.program.remove_port(bucket_name,local_port)

    # def do_import(self):
    #     """import : Print the status of all resen buckets."""
    #     pass

    # def do_export(self):
    #     """export : Print the status of all resen buckets."""
    #     pass

    # def do_freeze(self):
    #     """freeze : Print the status of all resen buckets."""
    #     pass


    # --------------- command line stuff -------------------------
    def do_quit(self,arg):
        """quit : Terminates the application."""
        # turn off currently running buckets or leave them running? leave running but 
        print("Exiting")
        return True


    def emptyline(self):
        pass

    def default(self,line):
        print("Unrecognized command: '%s'. Use 'help'." % (str(line)))
        pass

    # use this to preprocess commands
    def precmd(self,line):
        return line

    # # use this to display existing running buckets?
    # def postcmd(self,stop,line):
    #     

    do_exit = do_quit
    do_EOF = do_quit


    def parse_args(self,args):
        inputs = shlex.split(args)
        num_inputs = len(inputs)
        return inputs,num_inputs
    

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
        resen = resen.Resen()
    except RuntimeError:
        print("ERROR: another instance of Resen is already running!")
        sys.exit(1)

    ResenCmd(resen).cmdloop(intro)


if __name__ == '__main__':

    main()


