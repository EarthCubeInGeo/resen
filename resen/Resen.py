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


# TODO
# 1) list available resen-core version from dockerhub
# 2) create a bucket manifest from existing bucket
# 3) load a bucket from manifest file (supports moving from cloud to local, or from one computer to another) 
# 4) keep track of whether a jupyter server is running or not already and provide shutdown_jupyter and open_jupyter commands
# 5) freeze a bucket
# 6) check for python 3, else throw error
# 7) when starting a bucket again, need to recreate the container if ports and/or storage locations changed. Can do so with: https://stackoverflow.com/a/33956387
#    until this happens, we cannot modify storage nor ports after a bucket has been started
# 8) check that a local port being added isn't already used by another bucket.
# 9) check that a local storage location being added isn't already used by another bucket.


import os
import cmd         # for command line interface
import json        # used to store bucket manifests locally and for export
import time        # used for waiting (time.sleep())
import random      # used to generate tokens for jupyter server
import tempfile    # use this to get unique name for docker container
import webbrowser  # use this to open web browser
from pathlib import Path            # used to check whitelist paths
from subprocess import Popen, PIPE  # used for selinux detection

import docker


class Resen():
    def __init__(self):
        self.base_config_dir = self._get_config_dir()
        self.__locked = False
        self.__lock()

        self.bucket_manager = BucketManager(self.base_config_dir)

    def create_bucket(self,bucket_name):
        return self.bucket_manager.create_bucket(bucket_name)

    def list_buckets(self,names_only=False,bucket_name=None):
        return self.bucket_manager.list_buckets(names_only=names_only,bucket_name=bucket_name)

    def remove_bucket(self,bucket_name):
        return self.bucket_manager.remove_bucket(bucket_name)

    def add_storage(self,bucket_name,local,container,permissions):
        return self.bucket_manager.add_storage(bucket_name,local,container,permissions)

    def remove_storage(self,bucket_name,local):
        return self.bucket_manager.remove_storage(bucket_name,local)

    def add_port(self,bucket_name,local,container,tcp=True):
        return self.bucket_manager.add_port(bucket_name,local,container,tcp=tcp)

    def remove_port(self,bucket_name,local):
        return self.bucket_manager.remove_port(bucket_name,local)

    def add_image(self,bucket_name,docker_image):
        return self.bucket_manager.add_image(bucket_name,docker_image)

    def start_bucket(self,bucket_name):
        return self.bucket_manager.start_bucket(bucket_name)

    def stop_bucket(self,bucket_name):
        return self.bucket_manager.stop_bucket(bucket_name)

    def start_jupyter(self,bucket_name,local,container,lab=True):
        return self.bucket_manager.start_jupyter(bucket_name,local,container,lab=lab)

    def _get_config_dir(self):
        appname = 'resen'

        if 'APPDATA' in os.environ:
            confighome = os.environ['APPDATA']
        elif 'XDG_CONFIG_HOME' in os.environ:
            confighome = os.environ['XDG_CONFIG_HOME']
        else:
            confighome = os.path.join(os.environ['HOME'],'.config')
        configpath = os.path.join(confighome, appname)

        # TODO: add error checking
        if not os.path.exists(configpath):
            os.makedirs(configpath)

        return configpath

    def __lock(self):
        self.__lockfile = os.path.join(self.base_config_dir,'lock')
        if os.path.exists(self.__lockfile):
            raise RuntimeError('Another instance of Resen is already running!')

        with open(self.__lockfile,'w') as f:
            f.write('locked')
        self.__locked = True

    def __unlock(self):
        if not self.__locked:
            return

        try:
            os.remove(self.__lockfile)
            self.__locked = False
        except FileNotFoundError:
            pass
        except Exception as e:
            print("WARNING: Unable to remove lockfile: %s" % str(e))

    def __del__(self):
        self.__unlock()


# All the bucket stuff
# TODO: check status of bucket before updating it in case the bucket has changed status since last operation
class BucketManager():
# - use a bucket
#     - how many are allowed to run simultaneously?
#     - use the bucket how? only through jupyter notebook/lab is Ashton's vote. Terminal provided there

    def __init__(self,resen_root_dir):

        self.resen_root_dir = resen_root_dir
        self.dockerhelper = DockerHelper()
        # load 
        self.load_config()
        self.valid_cores = self.__get_valid_cores()
        self.selinux = self.__detect_selinux()
        self.storage_whitelist = ['/home/jovyan/work','/home/jovyan/mount']

    def __get_valid_cores(self):
        # TODO: download json file from resen-core github repo
        #       and if that fails, fallback to hardcoded list
        return [{"version":"2019.1.0rc1","repo":"resen-core","org":"earthcubeingeo",
            "image_id":'sha256:ac8e2819e502a307be786e07ea4deda987a05cdccba1d8a90a415ea103c101ff',
            "repodigest":'sha256:1da843059202f13443cd89e035acd5ced4f9c21fe80d778ce2185984c54be00b'},]

    def load_config(self):
        bucket_config = os.path.join(self.resen_root_dir,'buckets.json')
        # check if buckets.json exists, if not, initialize empty dictionary
        if not os.path.exists(bucket_config):
            params = list()

        else:
        # if it does exist, load it and return
        # TODO: handle exceptions due to file reading problems (incorrect file permissions)
            with open(bucket_config,'r') as f: 
                params = json.load(f)

        self.buckets = params
        self.bucket_names = [x['bucket']['name'] for x in self.buckets]

        # TODO: update status of buckets to double check that status is the same as in bucket.json

    def save_config(self):
        bucket_config = os.path.join(self.resen_root_dir,'buckets.json')
        # TODO: handle exceptions due to file writing problems (no free disk space, incorrect file permissions)
        with open(bucket_config,'w') as f: 
            json.dump(self.buckets,f)

    def create_bucket(self,bucket_name):
    #     - add a location for home directory persistent storage
    #     - how many cpu/ram resources are allowed to be used?
    #     - json file contains all config info about buckets
    #         - used to share and freeze buckets
    #         - track information about buckets (1st time using, which are running?)
        if bucket_name in self.bucket_names:
            print("ERROR: Bucket with name: %s already exists!" % (bucket_name))
            return False

        params = dict()
        params['bucket'] = dict()
        params['docker'] = dict()
        params['bucket']['name'] = bucket_name
        params['docker']['image'] = None
        params['docker']['container'] = None
        params['docker']['port'] = list()
        params['docker']['storage'] = list()
        params['docker']['status'] = None

        # now add the new bucket to the self.buckets config and then update the config file
        self.buckets.append(params)
        self.bucket_names = [x['bucket']['name'] for x in self.buckets]
        self.save_config()

        return True

    def list_buckets(self,names_only=False,bucket_name=None):
        if bucket_name is None:
            if names_only:
                print("{:<0}".format("Bucket Name"))
                for name in self.bucket_names:
                    print("{:<0}".format(str(name)))
            else:

                print("{:<20}{:<25}{:<25}".format("Bucket Name","Docker Image","Status"))
                for bucket in self.buckets:
                    name = self.__trim(str(bucket['bucket']['name']),18)
                    image = self.__trim(str(bucket['docker']['image']),23)
                    status = self.__trim(str(bucket['docker']['status']),23)
                    print("{:<20}{:<25}{:<25}".format(name, image, status))

        else:   # TODO, print all bucket info for bucket_name
            if not bucket_name in self.bucket_names:
                print("ERROR: Bucket with name: %s does not exist!" % bucket_name)
                return False

            ind = self.bucket_names.index(bucket_name)
            # TODO: make this print a nice table
            print(self.buckets[ind])

        return True

    def __trim(self,string,length):
        if len(string) > length:
            return string[:length-3]+'...'
        else:
            return string

    def remove_bucket(self,bucket_name):
        if not bucket_name in self.bucket_names:
            print("ERROR: Bucket with name: %s does not exist!" % bucket_name)
            return False

        self.update_bucket_statuses()
        ind = self.bucket_names.index(bucket_name)
        bucket = self.buckets[ind]

        if bucket['docker']['status'] == 'running':
            #container is running and we should throw an error
            print('ERROR: Bucket %s is running, cannot remove.' % (bucket['bucket']['name']))
            return False

        if bucket['docker']['status'] in ['created','exited'] and bucket['docker']['container'] is not None:
            # then we can remove container and update status
            success = self.dockerhelper.remove_container(bucket['docker']['container'])
            if success:
                self.buckets[ind]['docker']['status'] = None
                self.buckets[ind]['docker']['container'] = None
                self.save_config()

        ind = self.bucket_names.index(bucket_name)
        bucket = self.buckets[ind]
        if bucket['docker']['container'] is None:
            self.buckets.pop(ind)
            self.bucket_names = [x['bucket']['name'] for x in self.buckets]
            self.save_config()
            return True
        else:
            print('ERROR: Failed to remove bucket %s' % (bucket['bucket']['name']))
            return False

    def load(self):
    # - import a bucket
    #     - docker container export? (https://docs.docker.com/engine/reference/commandline/container_export/)
    #     - check iodide, how do they share
        pass

    def export(self):
    # export a bucket
    # 
        pass

    def freeze_bucket(self):
    # - bucket freeze (create docker image)
    #     - make a Dockerfile, build it, save it to tar.gz
    #     - docker save (saves an image): https://docs.docker.com/engine/reference/commandline/save/
    #       or docker container commit: https://docs.docker.com/engine/reference/commandline/container_commit/
    #     - docker image load (opposite of docker save): https://docs.docker.com/engine/reference/commandline/image_load/
        pass

    def add_storage(self,bucket_name,local,container,permissions='r'):
        # TODO: investiage difference between mounting a directory and fileblock
        #       See: https://docs.docker.com/storage/

        if not bucket_name in self.bucket_names:
            print("ERROR: Bucket with name: %s does not exist!" % bucket_name)
            return False

        ind = self.bucket_names.index(bucket_name)
        # check if bucket is running
        if self.buckets[ind]['docker']['status'] is not None:
            print("ERROR: Bucket has already been started, cannot add storage: %s" % (local))
            return False

        # check if storage already exists in list of storage
        existing_local = [x[0] for x in self.buckets[ind]['docker']['storage']]
        if local in existing_local:
            print("ERROR: Local storage location already in use in bucket!")
            return False
        existing_container = [x[1] for x in self.buckets[ind]['docker']['storage']]
        if container in existing_container:
            print("ERROR: Container storage location already in use in bucket!")
            return False

        # check that user is mounting in a whitelisted location
        valid = False
        child = Path(container)
        for loc in self.storage_whitelist:
            p = Path(loc)
            if p in child.parents:
                valid = True
        if not valid:
            print("ERROR: Invalid mount location. Can only mount storage into: %s." % ', '.join(self.storage_whitelist))
            return False

        if not permissions in ['r','ro','rw']:
            print("ERROR: Invalid permissions. Valid options are 'r' and 'rw'.")
            return False

        if permissions in ['r','ro']:
            permissions = 'ro'

        if self.selinux:
            permissions += ',Z'

        # TODO: check if storage location exists on host
        self.buckets[ind]['docker']['storage'].append([local,container,permissions])
        self.save_config()
        
        return True

    def remove_storage(self,bucket_name,local):
        if not bucket_name in self.bucket_names:
            print("ERROR: Bucket with name: %s does not exist!" % bucket_name)
            return False

        ind = self.bucket_names.index(bucket_name)
        # check if bucket is running
        if self.buckets[ind]['docker']['status'] is not None:
            print("ERROR: Bucket has already been started, cannot remove storage: %s" % (local))
            return False
        
        # check if storage already exists in list of storage
        existing_storage = [x[0] for x in self.buckets[ind]['docker']['storage']]
        try:
            ind2 = existing_storage.index(local)
            self.buckets[ind]['docker']['storage'].pop(ind2)
            self.save_config()
        except ValueError:
            print("ERROR: Storage location %s not associated with bucket %s" % (local,bucket_name))
            return False
        
        return True

    def add_port(self,bucket_name,local,container,tcp=True):
        if not bucket_name in self.bucket_names:
            print("ERROR: Bucket with name: %s does not exist!" % bucket_name)
            return False

        ind = self.bucket_names.index(bucket_name)
        # check if bucket is running
        if self.buckets[ind]['docker']['status'] is not None:
            print("ERROR: Bucket has already been started, cannot add port: %s" % (local))
            return False

        # check if local port already exists in list of ports
        existing_local = [x[0] for x in self.buckets[ind]['docker']['port']]
        if local in existing_local:
            print("ERROR: Local port location already in use in bucket!")
            return False

        # TODO: check if port location exists on host
        self.buckets[ind]['docker']['port'].append([local,container,tcp])
        self.save_config()
        
        return True

    def remove_port(self,bucket_name,local):
        if not bucket_name in self.bucket_names:
            print("ERROR: Bucket with name: %s does not exist!" % bucket_name)
            return False

        ind = self.bucket_names.index(bucket_name)
        # check if bucket is running
        if self.buckets[ind]['docker']['status'] is not None:
            print("ERROR: Bucket has already been started, cannot remove port: %s" % (local))
            return False
        
        # check if port already exists in list of port
        existing_port = [x[0] for x in self.buckets[ind]['docker']['port']]
        try:
            ind2 = existing_port.index(local)
            self.buckets[ind]['docker']['port'].pop(ind2)
            self.save_config()
        except ValueError:
            print("ERROR: port location %s not associated with bucket %s" % (local,bucket_name))
            return False
        
        return True

    def add_image(self,bucket_name,docker_image):
        if not bucket_name in self.bucket_names:
            print("ERROR: Bucket with name: %s does not exist!" % bucket_name)
            return False

        # TODO: check if "docker_image" is a valid resen-core image

        # check if image is already added  exists in list of storage
        ind = self.bucket_names.index(bucket_name)
        existing_image = self.buckets[ind]['docker']['image']
        if not existing_image is None:
            print("ERROR: Image %s was already added to bucket %s" % (existing_image,bucket_name))
            return False

        valid_versions = [x['version'] for x in self.valid_cores]
        if not docker_image in valid_versions:
            print("ERROR: Invalid resen-core version %s. Valid version: %s" % (docker_image,', '.join(valid_versions)))
            return False
        
        for x in self.valid_cores:
            if docker_image == x['version']:
                image = x['version']
                image_id = x['image_id']
                pull_image = '%s/%s@%s' % (x['org'],x['repo'],x['repodigest'])
                break

        self.buckets[ind]['docker']['image'] = image
        self.buckets[ind]['docker']['image_id'] = image_id
        self.buckets[ind]['docker']['pull_image'] = pull_image
        self.save_config()
        
        return True

    # TODO: def change_image(self,bucket_name,new_docker_image)
    # but only if container=None and status=None, in other words, only if the bucket has never been started.


    def start_bucket(self,bucket_name):
        # check if container has been previously started, create one if needed, start bucket if not running
        if not bucket_name in self.bucket_names:
            print("ERROR: Bucket with name: %s does not exist!" % bucket_name)
            return False

        ind = self.bucket_names.index(bucket_name)
        bucket = self.buckets[ind]
        
        # Make sure we have an image assigned to the bucket
        existing_image = bucket['docker']['image']
        if existing_image is None:
            print("ERROR: Bucket does not have an image assigned to it.")
            return False

        if bucket['docker']['container'] is None:
            # no container yet created, so create one
            kwargs = dict()
            kwargs['ports'] = bucket['docker']['port']
            kwargs['storage'] = bucket['docker']['storage']
            kwargs['bucket_name'] = bucket['bucket']['name']
            kwargs['image_name'] = bucket['docker']['image']
            kwargs['image_id'] = bucket['docker']['image_id']
            kwargs['pull_image'] = bucket['docker']['pull_image']
            container_id = self.dockerhelper.create_container(**kwargs)

            self.buckets[ind]['docker']['container'] = container_id
            self.save_config()

        self.update_bucket_statuses()
        ind = self.bucket_names.index(bucket_name)
        bucket = self.buckets[ind]

        if bucket['docker']['status'] in ['created', 'exited']:
            # then we can start the container and update status
            success = self.dockerhelper.start_container(bucket['docker']['container'])
            if success:
                self.buckets[ind]['docker']['status'] = 'running'
                self.save_config()
                return True
            else:
                print('ERROR: Failed to start bucket %s' % (bucket['bucket']['name']))
                return False
        else:
            #contained is already running and we should throw an error
            print('ERROR: Bucket %s is already running!' % (bucket['bucket']['name']))
            return False
    
    def stop_bucket(self,bucket_name):
        if not bucket_name in self.bucket_names:
            print("ERROR: Bucket with name: %s does not exist!" % bucket_name)
            return False

        self.update_bucket_statuses()
        ind = self.bucket_names.index(bucket_name)
        bucket = self.buckets[ind]

        if bucket['docker']['status'] in ['running']:
            # then we can start the container and update status
            success = self.dockerhelper.stop_container(bucket['docker']['container'])
            if success:
                self.buckets[ind]['docker']['status'] = 'exited'
                self.save_config()
                return True
            else:
                print('ERROR: Failed to stop bucket %s' % (bucket['bucket']['name']))
                return False
        else:
            #contained is already running and we should throw an error
            print('ERROR: Bucket %s is not running!' % (bucket['bucket']['name']))
            return False

    def execute_command(self,bucket_name,command,detach=True):
        if not bucket_name in self.bucket_names:
            print("ERROR: Bucket with name: %s does not exist!" % bucket_name)
            return False

        self.update_bucket_statuses()
        ind = self.bucket_names.index(bucket_name)
        bucket = self.buckets[ind]

        if bucket['docker']['status'] in ['running']:
            # then we can start the container and update status
            result = self.dockerhelper.execute_command(bucket['docker']['container'],command)
            status, output = result
            if (detach and status is None) or (not detach and status==0):
                return True
            else:
                print('ERROR: Failed to execute command %s' % (command))
                return False
        else:
            #contained is already running and we should throw an error
            print('ERROR: Bucket %s is not running!' % (bucket['bucket']['name']))
            return False

    def start_jupyter(self,bucket_name,local_port,container_port,lab=True):
        if not bucket_name in self.bucket_names:
            print("ERROR: Bucket with name: %s does not exist!" % bucket_name)
            return False

        if lab:
            style = 'lab'
        else:
            style = 'notebook'
        
        token = '%048x' % random.randrange(16**48)

        command = "bash -cl 'source activate py36 && jupyter %s --no-browser --ip 0.0.0.0 --port %s --NotebookApp.token=%s --KernelSpecManager.ensure_native_kernel=False'"
        command = command % (style, container_port, token)

        status = self.execute_command(bucket_name,command,detach=True)
        if status == False:
            return False
        time.sleep(0.1)
        # now check that jupyter is running
        self.update_bucket_statuses()
        ind = self.bucket_names.index(bucket_name)
        bucket = self.buckets[ind]
        result = self.dockerhelper.execute_command(bucket['docker']['container'],'ps -ef',detach=False)
        output = result[1].decode('utf-8').split('\n')

        pid = None
        for line in output:
            if 'jupyter' in line and token in line:
                parsed_line = [x for x in line.split(' ') if x != '']
                pid = parsed_line[1]
                break
            
        if pid is not None:
            url = 'http://localhost:%s/?token=%s' % (local_port,token)
            print("Jupyter %s can be accessed in a browser at: %s" % (style, url))
            time.sleep(3)
            webbrowser.open(url)
            return True
        else:
            print("ERROR: Failed to start jupyter server!")
            return False

    def update_bucket_statuses(self):
        for i,bucket in enumerate(self.buckets):
            container_id = bucket['docker']['container']
            if container_id is None:
                continue

            status = self.dockerhelper.get_container_status(container_id)
            if status:
                self.buckets[i]['docker']['status'] = status
                self.save_config()

    def get_container(self,bucket_name):
        if not bucket_name in self.bucket_names:
            print("ERROR: Bucket with name: %s does not exist!" % bucket_name)
            return False

        ind = self.bucket_names.index(bucket_name)
        return self.buckets[ind]['docker']['container']

    def __detect_selinux(self):
        try:
            p = Popen(['/usr/sbin/getenforce'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
            output, err = p.communicate()
            output = output.decode('utf-8').strip('\n')   
            rc = p.returncode

            if rc == 0 and output == 'Enforcing':
                return True
            else:
                return False
        except FileNotFoundError:
            return False


    # TODO: def reset_bucket(self,bucket_name):
    # used to reset a bucket to initial state (stop existing container, delete it, create new container)


# all the docker commands wrapped up nicely

# how do we call docker commands? subprocess? os.call?
# TODO: Use the docker SDK (https://docker-py.readthedocs.io/en/stable/)
class DockerHelper():
    def __init__(self):
        # TODO: define these in a dictionary or json file for each version of resen-core
        # need to get information for each resen-core from somewhere. 
        # Info like, what internal port needs to be exposed? Where do we get the image from? etc.
        # mounting directory in the container?
        self.container_prefix = 'resen_'

        self.docker = docker.from_env()

    def create_container(self,**input_kwargs):
        # TODO: Does container already exist? Does image exist (if not, pull it)?
        ports = input_kwargs.get('ports',None)
        storage = input_kwargs.get('storage',None)
        bucket_name = input_kwargs.get('bucket_name',None)
        image_name = input_kwargs.get('image_name',None)
        image_id = input_kwargs.get('image_id',None)
        pull_image = input_kwargs.get('pull_image',None)


        # TODO: jupyterlab or jupyter notebook, pass ports, mount volumes, generate token for lab/notebook server
        create_kwargs = dict()
        create_kwargs['name'] = self.container_prefix + bucket_name
        create_kwargs['command'] = 'bash'
        create_kwargs['tty'] = True
        create_kwargs['ports'] = dict()

        for host, container, tcp in ports:
            if tcp:
                key = '%s/tcp' % (container)
            else:
                key = '%s/udp' % (container)
            create_kwargs['ports'][key] = host

        create_kwargs['volumes'] = dict()
        for host, container, permissions in storage:
            # TODO: if SELinux, modify permissions to include ",Z"
            key = host
            temp = {'bind': container, 'mode': permissions}
            create_kwargs['volumes'][key] = temp

        # check if we have image, if not, pull it
        local_image_ids = [x.id for x in self.docker.images.list()]
        if image_id not in local_image_ids:
            print("Pulling image: %s" % image_name)
            print("   This may take some time...")
            DockerHelper.stream_pull_image(pull_image)
            image = self.docker.images.get(pull_image)
            repo,digest = pull_image.split('@')
            # When pulling from repodigest sha256 no tag is assigned. So:
            image.tag(repo, tag=image_name)
            print("Done!")

        container_id = self.docker.containers.create(image_id,**create_kwargs)

        return container_id.id

    @staticmethod
    def stream_pull_image(pull_image):
        import datetime
        def truncate_secs(delta_time, fmt=":%.2d"):
            delta_str = str(delta_time).split(':')
            return ":".join(delta_str[:-1]) + fmt%(float(delta_str[-1]))
        def update_bar(sum_total,accumulated,t0,current_time, scale=0.5):
            percentage = accumulated/sum_total*100
            nchars = int(percentage*scale)
            bar = "\r["+nchars*"="+">"+(int(100*scale)-nchars)*" "+"]"
            time_info = "Elapsed time: %s"%truncate_secs(current_time - t0)
            print(bar+" %5.2f %%, %5.3f/%4.2fGB %s"%(percentage,
                accumulated/1024**3,sum_total/1024**3,time_info),end="")

        client = docker.APIClient(base_url='unix://var/run/docker.sock')
        id_list = []
        id_current = []
        id_total = 0
        t0 = prev_time = datetime.datetime.now()
        try:
            for line in client.pull(pull_image,stream=True, decode=True):
                if 'progress' not in line:
                    continue
                line_current = line['progressDetail']['current']
                if line['id'] not in id_list:
                    id_list += [line['id']]
                    id_current += [line_current]
                    id_total += line['progressDetail']['total']
                else:
                    id_current[id_list.index(line['id'])] = line_current
                current_time = datetime.datetime.now()
                if (current_time-prev_time).total_seconds()<1:
                    continue
                prev_time = current_time
                update_bar(id_total,sum(id_current),t0,current_time)
            update_bar(id_total,sum(id_current),t0,current_time)
        except:
            print("\nError pulling image %s"%pull_image)
        print() # to avoid erasing the progress bar at the end

    def start_container(self, container_id):
        # need to check if bucket config has changed since last run
        # need to check if bucket is already running
        container = self.get_container(container_id)
        if container is None:
            return False

        container.start()   # this does nothing if already started
        container.reload()
        time.sleep(0.1)

        if container.status == 'running':
            return True
        else:
            return False


    def execute_command(self,container_id,command,detach=True):
        container = self.get_container(container_id)
        if container is None:
            return False

        result = container.exec_run(command,detach=detach)
        return result.exit_code, result.output



    def stop_container(self,container_id):
        container = self.get_container(container_id)
        if container is None:
            return False

        container.stop()    # this does nothing if already stopped
        container.reload()
        time.sleep(0.1)

        if container.status == 'exited':
            return True
        else:
            return False

    def remove_container(self,container_id):
        container = self.get_container(container_id)
        if container is None:
            return False

        if not container.status == 'exited':
            print("ERROR: Container is still running!")
            return False

        container.remove()

        return True



    # helper functions

    def get_container_status(self, container_id):
        container = self.get_container(container_id)
        if container is None:
            return False
        container.reload()  # maybe redundant

        return container.status

    # get a container object given a container id
    def get_container(self,container_id):
        try:
            container = self.docker.containers.get(container_id)
            return container
        except docker.errors.NotFound:
            print("ERROR: No such container: %s" % container_id)
            return None


#     def list_cores():
#         # list available docker images
#         # - list/pull docker image from docker hub
# #     - docker pull: https://docs.docker.com/engine/reference/commandline/pull/#pull-an-image-from-docker-hub
#         pass



# Configuration information:
#    - store it in .json file somewhere
#    - read the .json file and store config in config classes


# handle all of the bucket configuration info including reading
# and writing bucket config

def main():

    pass


if __name__ == '__main__':

    main()
