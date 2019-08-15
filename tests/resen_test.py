"""
Testing suite
"""

import unittest
from unittest.mock import patch, call
import os
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


###########################################################################################################################
###########################################################################################################################
### The following are really tests of the BucketManager class.  They are poorly formed, and should be revised before using.
###########################################################################################################################
###########################################################################################################################

    # def test_create_remove_bucket(self):
    #     res = resen.Resen()

    #     # check creating a bucket
    #     status = res.create_bucket('test_a19sui4670flawl')
    #     self.assertTrue(status)

    #     # check that the same bucket can't be created again
    #     status = res.create_bucket('test_a19sui4670flawl')
    #     self.assertFalse(status)

    #     # check that the bucket exists in the list of buckets
    #     self.assertTrue('test_a19sui4670flawl' in res.bucket_manager.bucket_names)

    #     # check removing the bucket
    #     status = res.remove_bucket('test_a19sui4670flawl')
    #     self.assertTrue(status)


    # def test_list_buckets(self):

    #     res = resen.Resen()

    #     capturedOutput = io.StringIO()                  # Create StringIO object
    #     sys.stdout = capturedOutput                     # redirect stdout

    #     # check that full status was printed to screen
    #     status = res.list_buckets()
    #     self.assertTrue('test_a19sui4670...  None                     None' in capturedOutput.getvalue())
    #     # check status
    #     self.assertTrue(status)

    #     # check that names only are printed to screen
    #     status = res.list_buckets(names_only=True)
    #     self.assertTrue('test_a19sui4670flawl' in capturedOutput.getvalue())
    #     # check status
    #     self.assertTrue(status)

    #     # check that status of a single bucket is printed to the screen
    #     status = res.list_buckets(bucket_name='test_a19sui4670flawl')
    #     self.assertTrue("{'bucket': {'name': 'test_a19sui4670flawl'}, 'docker': {'image': None, 'container': None, 'port': [], 'storage': [], 'status': None, 'jupyter': {'token': None, 'port': None}}}" in capturedOutput.getvalue())
    #     # check status
    #     self.assertTrue(status)

    #     # check response of queary for bucket that does not exist
    #     status = res.list_buckets(bucket_name='test_a19sui4670')
    #     self.assertFalse(status)

    #     sys.stdout = sys.__stdout__

    # def test_trim(self):

    #     res = resen.Resen()

    #     strout = res.bucket_manager._BucketManager__trim('abcdefg', 10)
    #     print(strout)

    #     strout = res.bucket_manager._BucketManager__trim('abcdefghijkl', 10)
    #     print(strout)

if __name__ == '__main__':
    unittest.main()