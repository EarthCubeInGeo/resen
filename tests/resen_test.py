"""
Testing suite
"""

import unittest
from unittest.mock import patch, call
import os
import io
import sys
import time
import tempfile
import resen

class ResenTests(unittest.TestCase):

    def test_init(self):
        res = resen.Resen()
        self.assertIsInstance(res, resen.Resen)

# These next several tests just check that each Resen function called the appropriate BucketManager Function.
# Does NOT check that the BucketManager methods work properly.  That will be later
    def test_create_bucket(self):
        res = resen.Resen()
        with patch.object(res.bucket_manager, 'create_bucket') as mock:
            res.create_bucket('test_a19sui4670flawl')
        mock.assert_called_with('test_a19sui4670flawl')

    def test_list_buckets(self):
        res = resen.Resen()
        with patch.object(res.bucket_manager, 'list_buckets') as mock:
            res.list_buckets()
            res.list_buckets(names_only=True)
            res.list_buckets(bucket_name='test_a19sui4670flawl')
        mock.assert_has_calls([call(bucket_name=None, names_only=False), call(bucket_name=None, names_only=True), call(bucket_name='test_a19sui4670flawl', names_only=False)])

    def test_remove_bucket(self):
        res = resen.Resen()
        with patch.object(res.bucket_manager, 'remove_bucket') as mock:
            res.remove_bucket('test_a19sui4670flawl')
        mock.assert_called_with('test_a19sui4670flawl')

    def test_add_storage(self):
        res = resen.Resen()
        with patch.object(res.bucket_manager, 'add_storage') as mock:
            res.add_storage('test_a19sui4670flawl', '/local/path', '/container/path', 'r')
        mock.assert_called_with('test_a19sui4670flawl', '/local/path', '/container/path', 'r')

    def test_remove_storage(self):
        res = resen.Resen()
        with patch.object(res.bucket_manager, 'remove_storage') as mock:
            res.remove_storage('test_a19sui4670flawl', '/local/path')
        mock.assert_called_with('test_a19sui4670flawl', '/local/path')

    def test_add_port(self):
        res = resen.Resen()
        with patch.object(res.bucket_manager, 'add_port') as mock:
            res.add_port('test_a19sui4670flawl', 9000, 9000)
            res.add_port('test_a19sui4670flawl', 9000, 9000, tcp=False)
        mock.assert_has_calls([call('test_a19sui4670flawl', 9000, 9000, tcp=True), call('test_a19sui4670flawl', 9000, 9000, tcp=False)])

    def test_remove_port(self):
        res = resen.Resen()
        with patch.object(res.bucket_manager, 'remove_port') as mock:
            res.remove_port('test_a19sui4670flawl', 9000)
        mock.assert_called_with('test_a19sui4670flawl', 9000)

    def test_add_image(self):
        res = resen.Resen()
        with patch.object(res.bucket_manager, 'add_image') as mock:
            res.add_image('test_a19sui4670flawl', 'docker_image01')
        mock.assert_called_with('test_a19sui4670flawl', 'docker_image01')

    def test_start_bucket(self):
        res = resen.Resen()
        with patch.object(res.bucket_manager, 'start_bucket') as mock:
            res.start_bucket('test_a19sui4670flawl')
        mock.assert_called_with('test_a19sui4670flawl')

    def test_stop_bucket(self):
        res = resen.Resen()
        with patch.object(res.bucket_manager, 'stop_bucket') as mock:
            res.stop_bucket('test_a19sui4670flawl')
        mock.assert_called_with('test_a19sui4670flawl')

    def test_start_jupyter(self):
        res = resen.Resen()
        with patch.object(res.bucket_manager, 'start_jupyter') as mock:
            res.start_jupyter('test_a19sui4670flawl', 9000, 9000)
        mock.assert_called_with('test_a19sui4670flawl', 9000, 9000)

    def test_stop_jupyter(self):
        res = resen.Resen()
        with patch.object(res.bucket_manager, 'stop_jupyter') as mock:
            res.stop_jupyter('test_a19sui4670flawl')
        mock.assert_called_with('test_a19sui4670flawl')

    def test_get_config_dir(self):
        res = resen.Resen()
        config_path = res._get_config_dir()
        # check that a valid path was returned
        self.assertTrue(os.path.isdir(config_path))

    def test_lock(self):
        res = resen.Resen()

        # __lock is called as part of init
        # check that __locked is True
        self.assertTrue(res._Resen__locked)
        # check that lockfile exists
        self.assertTrue(os.path.exists(res._Resen__lockfile))
        # an instance of resen is running, so we expect this to raise and error
        with self.assertRaises(RuntimeError): res._Resen__lock()

    def test_unlock(self):
        res = resen.Resen()
        res._Resen__unlock()
        # check that __locked is False
        self.assertFalse(res._Resen__locked)
        # check that the lockfile has been removed
        self.assertFalse(os.path.exists(res._Resen__lockfile))

    def test_del(self):
        # check that __unlock is called
        res = resen.Resen()
        with patch.object(res, '_Resen__unlock') as mock:
            res.__del__()
        mock.assert_called()



### QUESTIONS ###
# - Should base_config_dir be hard-coded or use Resen class function _get_config_dir to get it?
# - Is the BucketManager class only accessable through Resen class?  The resen package only includes Resen class, not BucketManager.
# - Should the list of cores be hard-coded?  What about when we add more cores?
# - What to do about functions called in the class initialization?
# - What is the port tcp flag for?
# - Is it strictly nessisary to test the bucket name and run status in every single function?  Is there a more efficient way?
# - Can buckets have multiple images?
# - Do the jupyter lab browser windows need to be automatically closed (or not opened at all)?
# - TODO: Use get_container instead of finding container ID manually (many places)

class BucketManagerTests(unittest.TestCase):

    def test_init(self):
        res = resen.Resen()
        bm = res.bucket_manager
        # should check if this is a BucketManager instance, but don't know how to do that because we don't have access to the BucketManager class directly.


    def test_get_valid_cores(self):
        res = resen.Resen()
        bm = res.bucket_manager
        cores = bm._BucketManager__get_valid_cores()
        # check that the correct list of cores were returned
        self.assertEqual([{'version': '2019.1.0rc2', 'repo': 'resen-core', 'org': 'earthcubeingeo', 'image_id': 'sha256:8b4750aa5186bdcf69a50fa10b0fd24a7c2293ef6135a9fdc594e0362443c99c', 'repodigest': 'sha256:2fe3436297c23a0d5393c8dae8661c40fc73140e602bd196af3be87a5e215bc2'}], cores)

    def test_load_config(self):
        res = resen.Resen()
        bm = res.bucket_manager
        bm.load_config()
        # check that the bucket and bucket_names lists were created
        self.assertIsInstance(bm.buckets, list)
        self.assertIsInstance(bm.bucket_names, list)
        ### NOTE: This doesn't really work because load_config is run in the BucketManager __init__, so the test will pass regardless of whether load_config() is called.

    def test_save_config(self):
        res = resen.Resen()
        bm = res.bucket_manager
        bm.save_config()

        bucket_config = os.path.join(bm.resen_root_dir,'buckets.json')

        # check that the config file exists
        self.assertTrue(os.path.isfile(bucket_config))

        # check that the config file was modified less than a second ago
        self.assertLess(time.time()-os.path.getmtime(bucket_config), 1.0)

    def test_create_bucket(self):
        res = resen.Resen()
        bm = res.bucket_manager

        status = bm.create_bucket('test_a19sui4670flawl')

        # check return status
        self.assertTrue(status)

        # check that the same bucket can't be created again
        status = bm.create_bucket('test_a19sui4670flawl')
        self.assertFalse(status)

        # check that the bucket exists in the list of buckets
        self.assertTrue('test_a19sui4670flawl' in bm.bucket_names)

        # tear down by removing bucket
        bm.remove_bucket('test_a19sui4670flawl')

    def test_list_buckets(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating bucekt
        bm.create_bucket('test_a19sui4670flawl')

        capturedOutput = io.StringIO()                  # Create StringIO object
        sys.stdout = capturedOutput                     # redirect stdout

        # check that full status was printed to screen
        status = bm.list_buckets()
        self.assertTrue('test_a19sui4670...  None                     None' in capturedOutput.getvalue())
        # check status
        self.assertTrue(status)

        # check that names only are printed to screen
        status = res.list_buckets(names_only=True)
        self.assertTrue('test_a19sui4670flawl' in capturedOutput.getvalue())
        # check status
        self.assertTrue(status)

        # check that status of a single bucket is printed to the screen
        status = res.list_buckets(bucket_name='test_a19sui4670flawl')
        self.assertTrue("{'bucket': {'name': 'test_a19sui4670flawl'}, 'docker': {'image': None, 'container': None, 'port': [], 'storage': [], 'status': None, 'jupyter': {'token': None, 'port': None}}}" in capturedOutput.getvalue())
        # check status
        self.assertTrue(status)

        # check response of queary for bucket that does not exist
        status = res.list_buckets(bucket_name='test_a19sui4670')
        self.assertFalse(status)

        sys.stdout = sys.__stdout__

        # tear down by removing bucket
        bm.remove_bucket('test_a19sui4670flawl')

    def test_trim(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # check string that is not truncated
        strout = res.bucket_manager._BucketManager__trim('abcdefg', 10)
        self.assertEqual('abcdefg', strout)

        # check string that is truncated
        strout = res.bucket_manager._BucketManager__trim('abcdefghijkl', 10)
        self.assertEqual('abcdefg...', strout)

    def test_remove_bucket(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating bucekt
        bm.create_bucket('test_a19sui4670flawl')

        # check return status
        status = bm.remove_bucket('test_a19sui4670flawl')
        self.assertTrue(status)

        # check that the bucket is not in the list of buckets
        self.assertTrue('test_a19sui4670flawl' not in bm.bucket_names)

        # check response status for bucket that does not exist
        status = bm.remove_bucket('test_a19sui4670flawl')
        self.assertFalse(status)

        # check response status for bucket that is running

    def test_load(self):
        # placeholder for load function
        pass

    def test_export(self):
        # placeholder for export function
        pass

    def test_freeze_bucket(self):
        # placeholder for freeze_bucket function
        pass

    def test_add_storage(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating bucket
        bm.create_bucket('test_a19sui4670flawl')

        # check status of adding valid storage
        local = tempfile.gettempdir()   # get valid local filepath with tempfile
        status = bm.add_storage('test_a19sui4670flawl', local, '/home/jovyan/work')
        self.assertTrue(status)

        # check that storage was added to bucket list
        ind = bm.bucket_names.index('test_a19sui4670flawl')
        self.assertEqual([local, '/home/jovyan/work', 'ro'], bm.buckets[ind]['docker']['storage'][0])

        # check status for invalid bucket name
        status = bm.add_storage('test_a19sui4670', local, '/home/jovyan/work')
        self.assertFalse(status)

        # check status for running bucket

        # check status for adding same storage again
        status = bm.add_storage('test_a19sui4670flawl', local, '/home/jovyan/work')
        self.assertFalse(status)

        # check status for unallowed container location
        status = bm.add_storage('test_a19sui4670flawl', local, '/home')
        self.assertFalse(status)

        # check status for invalid permission
        status = bm.add_storage('test_a19sui4670flawl', local, '/home/jovyan/work', permissions='a')
        self.assertFalse(status)

        # tear down by removing bucket
        bm.remove_bucket('test_a19sui4670flawl')

    def test_remove_storage(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating bucket and adding valid storage
        bm.create_bucket('test_a19sui4670flawl')
        local = tempfile.gettempdir()   # get valid local filepath with tempfile
        bm.add_storage('test_a19sui4670flawl', local, '/home/jovyan/work')

        # check status for invalid bucket name
        status = bm.remove_storage('test_a19sui4670', local)
        self.assertFalse(status)

        # check status for running bucket

        # check status for invalid storage location
        status = bm.remove_storage('test_a19sui4670flawl', '/bad/path')
        self.assertFalse(status)

        # check status for properly removing storage
        status = bm.remove_storage('test_a19sui4670flawl', local)
        self.assertTrue(status)

        # check that storage is now empty in bucket list
        ind = bm.bucket_names.index('test_a19sui4670flawl')
        self.assertEqual([], bm.buckets[ind]['docker']['storage'])

        # tear down by removing bucket
        bm.remove_bucket('test_a19sui4670flawl')

    def test_add_port(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating bucket
        bm.create_bucket('test_a19sui4670flawl')

        # check status for adding valid port
        status = bm.add_port('test_a19sui4670flawl', 9500, 9500)
        self.assertTrue(status)

        # check that port is now in bucket list
        ind = bm.bucket_names.index('test_a19sui4670flawl')
        self.assertEqual([9500, 9500, True], bm.buckets[ind]['docker']['port'][0])

        # check to make sure same port can't be added again
        status = bm.add_port('test_a19sui4670flawl', 9500, 9500)
        self.assertFalse(status)

        # check status for invalid bucket name
        status = bm.add_port('test_a19sui4670', 9600, 9600)
        self.assertFalse(status)

        # check status for running bucket

        # tear down by removing bucket
        bm.remove_bucket('test_a19sui4670flawl')

    def test_remove_port(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating bucket and adding valid port
        bm.create_bucket('test_a19sui4670flawl')
        bm.add_port('test_a19sui4670flawl', 9500, 9500)

        # check status for invalid bucket name
        status = bm.remove_port('test_a19sui4670', 9500)
        self.assertFalse(status)

        # check status for running bucket

        # check status for invalid port
        status = bm.remove_port('test_a19sui4670flawl', 9600)
        self.assertFalse(status)

        # check status for properly removing port
        status = bm.remove_port('test_a19sui4670flawl', 9500)
        self.assertTrue(status)

        # check that port list is now empty
        ind = bm.bucket_names.index('test_a19sui4670flawl')
        self.assertEqual([], bm.buckets[ind]['docker']['port'])        

        # tear down by removing bucket
        bm.remove_bucket('test_a19sui4670flawl')

    def test_add_image(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating bucket
        bm.create_bucket('test_a19sui4670flawl')

        # check status for invalid bucket name
        status = bm.add_image('test_a19sui4670', '2019.1.0rc2')
        self.assertFalse(status)

        # check status for invalid image
        status = bm.add_image('test_a19sui4670flawl', 'bad_image')
        self.assertFalse(status)

        # check status of valid image added
        status = bm.add_image('test_a19sui4670flawl', '2019.1.0rc2')
        self.assertTrue(status)

        # check that image is now in bucket list
        ind = bm.bucket_names.index('test_a19sui4670flawl')
        self.assertEqual('2019.1.0rc2', bm.buckets[ind]['docker']['image'])        

        # check that the same image can't be added again
        status = bm.add_image('test_a19sui4670flawl', '2019.1.0rc2')
        self.assertFalse(status)

        # tear down by removing bucket
        bm.remove_bucket('test_a19sui4670flawl')

    def test_start_bucket(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating bucket
        bm.create_bucket('test_a19sui4670flawl')

        # check status for invalid bucket name
        status = bm.start_bucket('test_a19sui4670')
        self.assertFalse(status)

        # check starting bucket without image
        status = bm.start_bucket('test_a19sui4670flawl')
        self.assertFalse(status)

        # add image and check starting bucket correctly
        bm.add_image('test_a19sui4670flawl', '2019.1.0rc2')
        status = bm.start_bucket('test_a19sui4670flawl')
        self.assertTrue(status)

        # check that a container ID was added to the bucket list
        ind = bm.bucket_names.index('test_a19sui4670flawl')
        self.assertIsNotNone(bm.buckets[ind]['docker']['container'])

        # check starting a running bucket
        status = bm.start_bucket('test_a19sui4670flawl')
        self.assertFalse(status)

        # tear down by stopping and removing bucket
        bm.stop_bucket('test_a19sui4670flawl')
        bm.remove_bucket('test_a19sui4670flawl')

    def test_stop_bucket(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating and starting bucket
        bm.create_bucket('test_a19sui4670flawl')
        bm.add_image('test_a19sui4670flawl', '2019.1.0rc2')
        bm.start_bucket('test_a19sui4670flawl')

        # check status for invalid bucket name
        status = bm.stop_bucket('test_a19sui4670')
        self.assertFalse(status)

        # check status for stopping bucket correctly
        status = bm.stop_bucket('test_a19sui4670flawl')
        self.assertTrue(status)

        # check status for bucket that's already stoped
        status = bm.stop_bucket('test_a19sui4670flawl')
        self.assertFalse(status)

        # tear down by stopping and removing bucket
        bm.remove_bucket('test_a19sui4670flawl')

    def test_execute_command(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating bucket
        bm.create_bucket('test_a19sui4670flawl')
        bm.add_image('test_a19sui4670flawl', '2019.1.0rc2')

        # check status for invalid bucket name
        status = bm.execute_command('test_a19sui4670', 'pwd')
        self.assertFalse(status)

        # check status for running command in bucket that has not started
        status = bm.execute_command('test_a19sui4670flawl', 'pwd')
        self.assertFalse(status)

        # start bucket and check status for running command
        bm.start_bucket('test_a19sui4670flawl')
        status = bm.execute_command('test_a19sui4670flawl', 'pwd')
        self.assertTrue(status)

        # tear down by removing bucket
        bm.stop_bucket('test_a19sui4670flawl')
        bm.remove_bucket('test_a19sui4670flawl')

    def test_start_jupyter(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating bucket
        bm.create_bucket('test_a19sui4670flawl')
        bm.add_port('test_a19sui4670flawl', 9500, 9500)
        bm.add_image('test_a19sui4670flawl', '2019.1.0rc2')

        # check status for invalid bucket name
        status = bm.start_jupyter('test_a19sui4670', 9500, 9500)
        self.assertFalse(status)

        # check status for starting jupyter
        bm.start_bucket('test_a19sui4670flawl')
        status = bm.start_jupyter('test_a19sui4670flawl', 9500, 9500)
        self.assertTrue(status)

        # somehow check that jupyter is running?


        # check status for starting jupyter when already running
        status = bm.start_jupyter('test_a19sui4670flawl', 9500, 9500)
        self.assertTrue(status)

        # tear down by stopping jupyter and removing bucket
        bm.stop_jupyter('test_a19sui4670flawl')
        bm.stop_bucket('test_a19sui4670flawl')
        bm.remove_bucket('test_a19sui4670flawl')

    def test_stop_jupyter(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating bucket and starting jupyter
        bm.create_bucket('test_a19sui4670flawl')
        bm.add_port('test_a19sui4670flawl', 9501, 9501)
        bm.add_image('test_a19sui4670flawl', '2019.1.0rc2')
        bm.start_bucket('test_a19sui4670flawl')
        bm.start_jupyter('test_a19sui4670flawl', 9501, 9501)

        # check status for invalid bucket name
        status = bm.stop_jupyter('test_a19sui4670')
        self.assertFalse(status)

        # check status for stopping jupyter
        status = bm.stop_jupyter('test_a19sui4670flawl')
        self.assertTrue(status)

        # check status for stopping jupyter when not running
        status = bm.stop_jupyter('test_a19sui4670flawl')
        self.assertTrue(status)

        # tear down by stopping and removing bucket
        bm.stop_bucket('test_a19sui4670flawl')
        bm.remove_bucket('test_a19sui4670flawl')

    def test_get_jupyter_pid(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating bucket and starting jupyter
        bm.create_bucket('test_a19sui4670flawl')
        bm.add_port('test_a19sui4670flawl', 9502, 9502)
        bm.add_image('test_a19sui4670flawl', '2019.1.0rc2')
        bm.start_bucket('test_a19sui4670flawl')
        bm.start_jupyter('test_a19sui4670flawl', 9502, 9502)

        # check that pid is a valid pid
        ind = bm.bucket_names.index('test_a19sui4670flawl')
        pid = bm.get_jupyter_pid(bm.buckets[ind]['docker']['container'])
        self.assertIsNotNone(pid)           # PID is not None
        self.assertGreaterEqual(int(pid), 0)     # PID >= 0
        result = bm.dockerhelper.execute_command(bm.buckets[ind]['docker']['container'], 'kill -0 {}'.format(pid), detach=False)
        self.assertEqual(result[0], 0)      # In the container, the PID can be queried (kill -0 PID returns an exit code of 0)

        # tear down by stopping jupyter and removing bucket
        bm.stop_jupyter('test_a19sui4670flawl')
        bm.stop_bucket('test_a19sui4670flawl')
        bm.remove_bucket('test_a19sui4670flawl')

    def test_update_bucket_statuses(self):
        # not really sure how to test this one
        pass

    def test_get_container(self):
        res = resen.Resen()
        bm = res.bucket_manager

        # set up by creating bucket
        bm.create_bucket('test_a19sui4670flawl')

        # check status for invalid bucket name
        status = bm.get_container('test_a19sui4670')
        self.assertFalse(status)

        # check that container ID is None before bucket is started
        container_id = bm.get_container('test_a19sui4670flawl')
        self.assertIsNone(container_id)

        # start bucket and check container ID
        bm.start_bucket('test_a19sui4670flawl')
        print(container_id)
        ind = bm.bucket_names.index('test_a19sui4670flawl')
        self.assertEqual(bm.buckets[ind]['docker']['container'], container_id)

        # tear down by stoping and removing bucket
        bm.stop_bucket('test_a19sui4670flawl')
        bm.remove_bucket('test_a19sui4670flawl')

    def test_detect_selinux(self):
        # don't know how to test this one either
        pass

if __name__ == '__main__':
    unittest.main()