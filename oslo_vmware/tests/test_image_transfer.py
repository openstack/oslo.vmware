# Copyright (c) 2014 VMware, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Unit tests for functions and classes for image transfer.
"""

import math

from eventlet import greenthread
from eventlet import timeout
import mock

from oslo_vmware import exceptions
from oslo_vmware import image_transfer
from oslo_vmware import rw_handles
from oslo_vmware.tests import base


class BlockingQueueTest(base.TestCase):
    """Tests for BlockingQueue."""

    def test_read(self):
        max_size = 10
        chunk_size = 10
        max_transfer_size = 30
        queue = image_transfer.BlockingQueue(max_size, max_transfer_size)

        def get_side_effect():
            return [1] * chunk_size

        queue.get = mock.Mock(side_effect=get_side_effect)
        while True:
            data_item = queue.read(chunk_size)
            if not data_item:
                break

        self.assertEqual(max_transfer_size, queue._transferred)
        exp_calls = [mock.call()] * int(math.ceil(float(max_transfer_size) /
                                                  chunk_size))
        self.assertEqual(exp_calls, queue.get.call_args_list)

    def test_write(self):
        queue = image_transfer.BlockingQueue(10, 30)
        queue.put = mock.Mock()
        write_count = 10
        for _ in range(0, write_count):
            queue.write([1])
        exp_calls = [mock.call([1])] * write_count
        self.assertEqual(exp_calls, queue.put.call_args_list)

    def test_seek(self):
        queue = image_transfer.BlockingQueue(10, 30)
        self.assertRaises(IOError, queue.seek, 5)

    def test_tell(self):
        queue = image_transfer.BlockingQueue(10, 30)
        self.assertEqual(0, queue.tell())
        queue.get = mock.Mock(return_value=[1] * 10)
        queue.read(10)
        self.assertEqual(10, queue.tell())


class ImageWriterTest(base.TestCase):
    """Tests for ImageWriter class."""

    def _create_image_writer(self):
        self.image_service = mock.Mock()
        self.context = mock.Mock()
        self.input_file = mock.Mock()
        self.image_id = mock.Mock()
        return image_transfer.ImageWriter(self.context, self.input_file,
                                          self.image_service, self.image_id)

    @mock.patch.object(greenthread, 'sleep')
    def test_start(self, mock_sleep):
        writer = self._create_image_writer()
        status_list = ['queued', 'saving', 'active']

        def image_service_show_side_effect(context, image_id):
            status = status_list.pop(0)
            return {'status': status}

        self.image_service.show.side_effect = image_service_show_side_effect
        exp_calls = [mock.call(self.context, self.image_id)] * len(status_list)
        writer.start()
        self.assertTrue(writer.wait())
        self.image_service.update.assert_called_once_with(self.context,
                                                          self.image_id, {},
                                                          data=self.input_file)
        self.assertEqual(exp_calls, self.image_service.show.call_args_list)

    def test_start_with_killed_status(self):
        writer = self._create_image_writer()

        def image_service_show_side_effect(_context, _image_id):
            return {'status': 'killed'}

        self.image_service.show.side_effect = image_service_show_side_effect
        writer.start()
        self.assertRaises(exceptions.ImageTransferException,
                          writer.wait)
        self.image_service.update.assert_called_once_with(self.context,
                                                          self.image_id, {},
                                                          data=self.input_file)
        self.image_service.show.assert_called_once_with(self.context,
                                                        self.image_id)

    def test_start_with_unknown_status(self):
        writer = self._create_image_writer()

        def image_service_show_side_effect(_context, _image_id):
            return {'status': 'unknown'}

        self.image_service.show.side_effect = image_service_show_side_effect
        writer.start()
        self.assertRaises(exceptions.ImageTransferException,
                          writer.wait)
        self.image_service.update.assert_called_once_with(self.context,
                                                          self.image_id, {},
                                                          data=self.input_file)
        self.image_service.show.assert_called_once_with(self.context,
                                                        self.image_id)

    def test_start_with_image_service_show_exception(self):
        writer = self._create_image_writer()
        self.image_service.show.side_effect = RuntimeError()
        writer.start()
        self.assertRaises(exceptions.ImageTransferException, writer.wait)
        self.image_service.update.assert_called_once_with(self.context,
                                                          self.image_id, {},
                                                          data=self.input_file)
        self.image_service.show.assert_called_once_with(self.context,
                                                        self.image_id)


class FileReadWriteTaskTest(base.TestCase):
    """Tests for FileReadWriteTask class."""

    def test_start(self):
        data_items = [[1] * 10, [1] * 20, [1] * 5, []]

        def input_file_read_side_effect(arg):
            self.assertEqual(arg, rw_handles.READ_CHUNKSIZE)
            data = data_items[input_file_read_side_effect.i]
            input_file_read_side_effect.i += 1
            return data

        input_file_read_side_effect.i = 0
        input_file = mock.Mock()
        input_file.read.side_effect = input_file_read_side_effect
        output_file = mock.Mock()
        rw_task = image_transfer.FileReadWriteTask(input_file, output_file)
        rw_task.start()
        self.assertTrue(rw_task.wait())
        self.assertEqual(len(data_items), input_file.read.call_count)

        exp_calls = []
        for i in range(0, len(data_items)):
            exp_calls.append(mock.call(data_items[i]))
        self.assertEqual(exp_calls, output_file.write.call_args_list)

        self.assertEqual(len(data_items),
                         input_file.update_progress.call_count)
        self.assertEqual(len(data_items),
                         output_file.update_progress.call_count)

    def test_start_with_read_exception(self):
        input_file = mock.Mock()
        input_file.read.side_effect = RuntimeError()
        output_file = mock.Mock()
        rw_task = image_transfer.FileReadWriteTask(input_file, output_file)
        rw_task.start()
        self.assertRaises(exceptions.ImageTransferException, rw_task.wait)
        input_file.read.assert_called_once_with(rw_handles.READ_CHUNKSIZE)


class ImageTransferUtilityTest(base.TestCase):
    """Tests for image_transfer utility methods."""

    @mock.patch.object(timeout, 'Timeout')
    @mock.patch.object(image_transfer, 'ImageWriter')
    @mock.patch.object(image_transfer, 'FileReadWriteTask')
    @mock.patch.object(image_transfer, 'BlockingQueue')
    def test_start_transfer(self, fake_BlockingQueue, fake_FileReadWriteTask,
                            fake_ImageWriter, fake_Timeout):

        context = mock.Mock()
        read_file_handle = mock.Mock()
        read_file_handle.close = mock.Mock()
        image_service = mock.Mock()
        image_id = mock.Mock()
        blocking_queue = mock.Mock()

        write_file_handle1 = mock.Mock()
        write_file_handle1.close = mock.Mock()
        write_file_handle2 = None
        write_file_handles = [write_file_handle1, write_file_handle2]

        timeout_secs = 10
        blocking_queue_size = 10
        image_meta = {}
        max_data_size = 30

        fake_BlockingQueue.return_value = blocking_queue
        fake_timer = mock.Mock()
        fake_timer.cancel = mock.Mock()
        fake_Timeout.return_value = fake_timer

        for write_file_handle in write_file_handles:
            image_transfer._start_transfer(context,
                                           timeout_secs,
                                           read_file_handle,
                                           max_data_size,
                                           write_file_handle=write_file_handle,
                                           image_service=image_service,
                                           image_id=image_id,
                                           image_meta=image_meta)

        exp_calls = [mock.call(blocking_queue_size,
                               max_data_size)] * len(write_file_handles)
        self.assertEqual(exp_calls,
                         fake_BlockingQueue.call_args_list)

        exp_calls2 = [mock.call(read_file_handle, blocking_queue),
                      mock.call(blocking_queue, write_file_handle1),
                      mock.call(read_file_handle, blocking_queue)]
        self.assertEqual(exp_calls2,
                         fake_FileReadWriteTask.call_args_list)

        exp_calls3 = mock.call(context, blocking_queue, image_service,
                               image_id, image_meta)
        self.assertEqual(exp_calls3,
                         fake_ImageWriter.call_args)

        exp_calls4 = [mock.call(timeout_secs)] * len(write_file_handles)
        self.assertEqual(exp_calls4,
                         fake_Timeout.call_args_list)

        self.assertEqual(len(write_file_handles),
                         fake_timer.cancel.call_count)

        self.assertEqual(len(write_file_handles),
                         read_file_handle.close.call_count)

        write_file_handle1.close.assert_called_once_with()

    @mock.patch.object(image_transfer, 'FileReadWriteTask')
    @mock.patch.object(image_transfer, 'BlockingQueue')
    def test_start_transfer_with_no_image_destination(self, fake_BlockingQueue,
                                                      fake_FileReadWriteTask):

        context = mock.Mock()
        read_file_handle = mock.Mock()
        write_file_handle = None
        image_service = None
        image_id = None
        timeout_secs = 10
        image_meta = {}
        blocking_queue_size = 10
        max_data_size = 30
        blocking_queue = mock.Mock()

        fake_BlockingQueue.return_value = blocking_queue

        self.assertRaises(ValueError,
                          image_transfer._start_transfer,
                          context,
                          timeout_secs,
                          read_file_handle,
                          max_data_size,
                          write_file_handle=write_file_handle,
                          image_service=image_service,
                          image_id=image_id,
                          image_meta=image_meta)

        fake_BlockingQueue.assert_called_once_with(blocking_queue_size,
                                                   max_data_size)

        fake_FileReadWriteTask.assert_called_once_with(read_file_handle,
                                                       blocking_queue)

    @mock.patch('oslo_vmware.rw_handles.FileWriteHandle')
    @mock.patch('oslo_vmware.rw_handles.ImageReadHandle')
    @mock.patch.object(image_transfer, '_start_transfer')
    def test_download_flat_image(
            self,
            fake_transfer,
            fake_rw_handles_ImageReadHandle,
            fake_rw_handles_FileWriteHandle):

        context = mock.Mock()
        image_id = mock.Mock()
        image_service = mock.Mock()
        image_service.download = mock.Mock()
        image_service.download.return_value = 'fake_iter'

        fake_ImageReadHandle = 'fake_ImageReadHandle'
        fake_FileWriteHandle = 'fake_FileWriteHandle'
        cookies = []
        timeout_secs = 10
        image_size = 1000
        host = '127.0.0.1'
        port = 443
        dc_path = 'dc1'
        ds_name = 'ds1'
        file_path = '/fake_path'

        fake_rw_handles_ImageReadHandle.return_value = fake_ImageReadHandle
        fake_rw_handles_FileWriteHandle.return_value = fake_FileWriteHandle

        image_transfer.download_flat_image(
            context,
            timeout_secs,
            image_service,
            image_id,
            image_size=image_size,
            host=host,
            port=port,
            data_center_name=dc_path,
            datastore_name=ds_name,
            cookies=cookies,
            file_path=file_path)

        image_service.download.assert_called_once_with(context, image_id)

        fake_rw_handles_ImageReadHandle.assert_called_once_with('fake_iter')

        fake_rw_handles_FileWriteHandle.assert_called_once_with(
            host,
            port,
            dc_path,
            ds_name,
            cookies,
            file_path,
            image_size,
            cacerts=None)

        fake_transfer.assert_called_once_with(
            context,
            timeout_secs,
            fake_ImageReadHandle,
            image_size,
            write_file_handle=fake_FileWriteHandle)

    @mock.patch('oslo_vmware.rw_handles.VmdkWriteHandle')
    @mock.patch.object(image_transfer, '_start_transfer')
    def test_download_stream_optimized_data(self, fake_transfer,
                                            fake_rw_handles_VmdkWriteHandle):

        context = mock.Mock()
        session = mock.Mock()
        read_handle = mock.Mock()
        timeout_secs = 10
        image_size = 1000
        host = '127.0.0.1'
        port = 443
        resource_pool = 'rp-1'
        vm_folder = 'folder-1'
        vm_import_spec = None

        fake_VmdkWriteHandle = mock.Mock()
        fake_VmdkWriteHandle.get_imported_vm = mock.Mock()
        fake_rw_handles_VmdkWriteHandle.return_value = fake_VmdkWriteHandle

        image_transfer.download_stream_optimized_data(
            context,
            timeout_secs,
            read_handle,
            session=session,
            host=host,
            port=port,
            resource_pool=resource_pool,
            vm_folder=vm_folder,
            vm_import_spec=vm_import_spec,
            image_size=image_size)

        fake_rw_handles_VmdkWriteHandle.assert_called_once_with(
            session,
            host,
            port,
            resource_pool,
            vm_folder,
            vm_import_spec,
            image_size)

        fake_transfer.assert_called_once_with(
            context,
            timeout_secs,
            read_handle,
            image_size,
            write_file_handle=fake_VmdkWriteHandle)

        fake_VmdkWriteHandle.get_imported_vm.assert_called_once_with()

    @mock.patch('oslo_vmware.rw_handles.ImageReadHandle')
    @mock.patch.object(image_transfer, 'download_stream_optimized_data')
    def test_download_stream_optimized_image(
            self, fake_download_stream_optimized_data,
            fake_rw_handles_ImageReadHandle):

        context = mock.Mock()
        session = mock.Mock()
        image_id = mock.Mock()
        timeout_secs = 10
        image_size = 1000
        host = '127.0.0.1'
        port = 443
        resource_pool = 'rp-1'
        vm_folder = 'folder-1'
        vm_import_spec = None

        fake_iter = 'fake_iter'
        image_service = mock.Mock()
        image_service.download = mock.Mock()
        image_service.download.return_value = fake_iter

        fake_ImageReadHandle = 'fake_ImageReadHandle'
        fake_rw_handles_ImageReadHandle.return_value = fake_ImageReadHandle

        image_transfer.download_stream_optimized_image(
            context,
            timeout_secs,
            image_service,
            image_id,
            session=session,
            host=host,
            port=port,
            resource_pool=resource_pool,
            vm_folder=vm_folder,
            vm_import_spec=vm_import_spec,
            image_size=image_size)

        image_service.download.assert_called_once_with(context, image_id)

        fake_rw_handles_ImageReadHandle.assert_called_once_with(fake_iter)

        fake_download_stream_optimized_data.assert_called_once_with(
            context,
            timeout_secs,
            fake_ImageReadHandle,
            session=session,
            host=host,
            port=port,
            resource_pool=resource_pool,
            vm_folder=vm_folder,
            vm_import_spec=vm_import_spec,
            image_size=image_size)

    @mock.patch.object(image_transfer, '_start_transfer')
    @mock.patch('oslo_vmware.rw_handles.VmdkReadHandle')
    def test_copy_stream_optimized_disk(
            self, vmdk_read_handle, start_transfer):

        read_handle = mock.sentinel.read_handle
        vmdk_read_handle.return_value = read_handle

        context = mock.sentinel.context
        timeout = mock.sentinel.timeout
        write_handle = mock.Mock(name='/cinder/images/tmpAbcd.vmdk')
        session = mock.sentinel.session
        host = mock.sentinel.host
        port = mock.sentinel.port
        vm = mock.sentinel.vm
        vmdk_file_path = mock.sentinel.vmdk_file_path
        vmdk_size = mock.sentinel.vmdk_size

        image_transfer.copy_stream_optimized_disk(
            context, timeout, write_handle, session=session, host=host,
            port=port, vm=vm, vmdk_file_path=vmdk_file_path,
            vmdk_size=vmdk_size)

        vmdk_read_handle.assert_called_once_with(
            session, host, port, vm, vmdk_file_path, vmdk_size)
        start_transfer.assert_called_once_with(
            context, timeout, read_handle, vmdk_size,
            write_file_handle=write_handle)

    @mock.patch('oslo_vmware.rw_handles.VmdkReadHandle')
    @mock.patch.object(image_transfer, '_start_transfer')
    def test_upload_image(self, fake_transfer, fake_rw_handles_VmdkReadHandle):

        context = mock.Mock()
        image_id = mock.Mock()
        owner_id = mock.Mock()
        session = mock.Mock()
        vm = mock.Mock()
        image_service = mock.Mock()

        timeout_secs = 10
        image_size = 1000
        host = '127.0.0.1'
        port = 443
        file_path = '/fake_path'
        is_public = False
        image_name = 'fake_image'
        image_version = 1

        fake_VmdkReadHandle = 'fake_VmdkReadHandle'
        fake_rw_handles_VmdkReadHandle.return_value = fake_VmdkReadHandle

        image_transfer.upload_image(context,
                                    timeout_secs,
                                    image_service,
                                    image_id,
                                    owner_id,
                                    session=session,
                                    host=host,
                                    port=port,
                                    vm=vm,
                                    vmdk_file_path=file_path,
                                    vmdk_size=image_size,
                                    is_public=is_public,
                                    image_name=image_name,
                                    image_version=image_version)

        fake_rw_handles_VmdkReadHandle.assert_called_once_with(session,
                                                               host,
                                                               port,
                                                               vm,
                                                               file_path,
                                                               image_size)

        image_metadata = {'disk_format': 'vmdk',
                          'is_public': is_public,
                          'name': image_name,
                          'status': 'active',
                          'container_format': 'bare',
                          'size': 0,
                          'properties': {'vmware_image_version': image_version,
                                         'vmware_disktype': 'streamOptimized',
                                         'owner_id': owner_id}}

        fake_transfer.assert_called_once_with(context,
                                              timeout_secs,
                                              fake_VmdkReadHandle,
                                              0,
                                              image_service=image_service,
                                              image_id=image_id,
                                              image_meta=image_metadata)
