#!/usr/bin/env python

import docker
import time

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

        self.docker = docker.from_env(timeout=300)

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
            temp = {'bind': container, 'mode': permissions}
            create_kwargs['volumes'][host] = temp

        # check if we have image, if not, pull it
        local_image_ids = [x.id for x in self.docker.images.list()]
        if image_id not in local_image_ids:
            print("Pulling image: %s" % image_name)
            print("   This may take some time...")
            status = self.stream_pull_image(pull_image)
            image = self.docker.images.get(pull_image)
            repo,digest = pull_image.split('@')
            # When pulling from repodigest sha256 no tag is assigned. So:
            image.tag(repo, tag=image_name)
            print("Done!")

        container_id = self.docker.containers.create(image_id,**create_kwargs)

        return container_id.id

    def stream_pull_image(self,pull_image):
        import datetime
        # time formatting
        def truncate_secs(delta_time, fmt=":%.2d"):
            delta_str = str(delta_time).split(':')
            return ":".join(delta_str[:-1]) + fmt%(float(delta_str[-1]))
        # progress bar
        def update_bar(sum_total,accumulated,t0,current_time, scale=0.5):
            percentage = accumulated/sum_total*100
            nchars = int(percentage*scale)
            bar = "\r["+nchars*"="+">"+(int(100*scale)-nchars)*" "+"]"
            time_info = "Elapsed time: %s"%truncate_secs(current_time - t0)
            print(bar+" %6.2f %%, %5.3f/%4.2fGB %s"%(percentage,
                accumulated/1024**3,sum_total/1024**3,time_info),end="")

        id_list = []
        id_current = []
        id_total = 0
        t0 = prev_time = datetime.datetime.now()
        try:
            # Use a lower level pull call to stream the pull
            for line in self.docker.api.pull(pull_image,stream=True, decode=True):
                if 'progress' not in line:
                    continue
                line_current = line['progressDetail']['current']
                if line['id'] not in id_list:
                    id_list.append(line['id'])
                    id_current.append(line_current)
                    id_total += line['progressDetail']['total']
                else:
                    id_current[id_list.index(line['id'])] = line_current
                current_time = datetime.datetime.now()
                if (current_time-prev_time).total_seconds()<1:
                    # To limit print statements to no more than 1 per second.
                    continue
                prev_time = current_time
                update_bar(id_total,sum(id_current),t0,current_time)
            # Last update of the progress bar:
            update_bar(id_total,sum(id_current),t0,current_time)
        except Exception as e:
            raise RuntimeError("\nException encountered while pulling image {}\nException: {}".format(pull_image,str(e)))

        print() # to avoid erasing the progress bar at the end

        return True

    def start_container(self, container_id):
        # need to check if bucket config has changed since last run
        container = self.get_container(container_id)
        container.start()   # this does nothing if already started
        container.reload()
        time.sleep(0.1)
        return container.status


    def execute_command(self,container_id,command,detach=True):
        container = self.get_container(container_id)
        result = container.exec_run(command,detach=detach)
        return result.exit_code, result.output


    def stop_container(self,container_id):
        container = self.get_container(container_id)
        container.stop()    # this does nothing if already stopped
        container.reload()
        time.sleep(0.1)
        return container.status

    def remove_container(self,container_id):
        container = self.get_container(container_id)
        container.remove()
        return True


    def export_container(self,container_id,tag=None, filename=None):
        container = self.get_container(container_id)

        # create new image from container
        container.commit(repository='earthcubeingeo/resen-lite',tag=tag)

        # save image as *.tar file
        image_name = 'earthcubeingeo/resen-lite:{}'.format(tag)
        image = self.docker.images.get(image_name)
        out = image.save()
        with open(filename, 'wb') as f:
            for chunk in out:
                f.write(chunk)

        # remove image after it has been saved
        self.docker.images.remove(image_name)

        # TODO:
        # Add checks that image was sucessfully saved before removing it?
        # Pass in repository name - currently hard-coded
        # Repository naming conventions?
        # Does the tag name matter?

        return True

    def import_image(self,filename,name=None):
        cli = docker.APIClient()
        cli.import_image_from_file(filename,repository=name)
        # client = docker.from_env()
        print(self.docker.images.list())
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
