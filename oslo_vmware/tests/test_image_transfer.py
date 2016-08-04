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

import mock
import six

from oslo_vmware import exceptions
from oslo_vmware import image_transfer
from oslo_vmware.tests import base


class ImageTransferUtilityTest(base.TestCase):
    """Tests for image_transfer utility methods."""

    def test_start_transfer(self):
        data = b'image-data-here'
        read_handle = six.BytesIO(data)
        write_handle = mock.Mock()
        image_transfer._start_transfer(read_handle, write_handle, None)
        write_handle.write.assert_called_once_with(data)

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
            fake_ImageReadHandle,
            fake_FileWriteHandle,
            timeout_secs)

    @mock.patch('oslo_vmware.rw_handles.FileWriteHandle')
    @mock.patch.object(image_transfer, '_start_transfer')
    def test_download_file(self, start_transfer, file_write_handle_cls):
        write_handle = mock.sentinel.write_handle
        file_write_handle_cls.return_value = write_handle

        read_handle = mock.sentinel.read_handle
        host = mock.sentinel.host
        port = mock.sentinel.port
        dc_name = mock.sentinel.dc_name
        ds_name = mock.sentinel.ds_name
        cookies = mock.sentinel.cookies
        upload_file_path = mock.sentinel.upload_file_path
        file_size = mock.sentinel.file_size
        cacerts = mock.sentinel.cacerts
        timeout_secs = mock.sentinel.timeout_secs
        image_transfer.download_file(
            read_handle, host, port, dc_name, ds_name, cookies,
            upload_file_path, file_size, cacerts, timeout_secs)

        file_write_handle_cls.assert_called_once_with(
            host, port, dc_name, ds_name, cookies, upload_file_path,
            file_size, cacerts=cacerts)
        start_transfer.assert_called_once_with(
            read_handle, write_handle, timeout_secs)

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
            image_size,
            'PUT')

        fake_transfer.assert_called_once_with(read_handle,
                                              fake_VmdkWriteHandle,
                                              timeout_secs)

        fake_VmdkWriteHandle.get_imported_vm.assert_called_once_with()

    @mock.patch('tarfile.open')
    @mock.patch('oslo_vmware.image_util.get_vmdk_name_from_ovf')
    def test_get_vmdk_handle(self, get_vmdk_name_from_ovf, tar_open):

        ovf_info = mock.Mock()
        ovf_info.name = 'test.ovf'
        vmdk_info = mock.Mock()
        vmdk_info.name = 'test.vmdk'
        tar = mock.Mock()
        tar.__iter__ = mock.Mock(return_value=iter([ovf_info, vmdk_info]))
        tar.__enter__ = mock.Mock(return_value=tar)
        tar.__exit__ = mock.Mock(return_value=None)
        tar_open.return_value = tar

        ovf_handle = mock.Mock()
        get_vmdk_name_from_ovf.return_value = 'test.vmdk'
        vmdk_handle = mock.Mock()
        tar.extractfile.side_effect = [ovf_handle, vmdk_handle]

        ova_handle = mock.sentinel.ova_handle
        ret = image_transfer._get_vmdk_handle(ova_handle)

        self.assertEqual(vmdk_handle, ret)
        tar_open.assert_called_once_with(mode="r|", fileobj=ova_handle)
        self.assertEqual([mock.call(ovf_info), mock.call(vmdk_info)],
                         tar.extractfile.call_args_list)
        get_vmdk_name_from_ovf.assert_called_once_with(ovf_handle)

    @mock.patch('tarfile.open')
    def test_get_vmdk_handle_with_invalid_ova(self, tar_open):

        tar = mock.Mock()
        tar.__iter__ = mock.Mock(return_value=iter([]))
        tar.__enter__ = mock.Mock(return_value=tar)
        tar.__exit__ = mock.Mock(return_value=None)
        tar_open.return_value = tar

        ova_handle = mock.sentinel.ova_handle
        ret = image_transfer._get_vmdk_handle(ova_handle)

        self.assertIsNone(ret)
        tar_open.assert_called_once_with(mode="r|", fileobj=ova_handle)
        self.assertFalse(tar.extractfile.called)

    @mock.patch('oslo_vmware.rw_handles.ImageReadHandle')
    @mock.patch.object(image_transfer, 'download_stream_optimized_data')
    @mock.patch.object(image_transfer, '_get_vmdk_handle')
    def _test_download_stream_optimized_image(
            self,
            get_vmdk_handle,
            download_stream_optimized_data,
            image_read_handle,
            container=None,
            invalid_ova=False):

        image_service = mock.Mock()
        if container:
            image_service.show.return_value = {'container_format': container}
        read_iter = mock.sentinel.read_iter
        image_service.download.return_value = read_iter
        read_handle = mock.sentinel.read_handle
        image_read_handle.return_value = read_handle

        if container == 'ova':
            if invalid_ova:
                get_vmdk_handle.return_value = None
            else:
                vmdk_handle = mock.sentinel.vmdk_handle
                get_vmdk_handle.return_value = vmdk_handle

        imported_vm = mock.sentinel.imported_vm
        download_stream_optimized_data.return_value = imported_vm

        context = mock.sentinel.context
        timeout_secs = mock.sentinel.timeout_secs
        image_id = mock.sentinel.image_id
        session = mock.sentinel.session
        image_size = mock.sentinel.image_size
        host = mock.sentinel.host
        port = mock.sentinel.port
        resource_pool = mock.sentinel.port
        vm_folder = mock.sentinel.vm_folder
        vm_import_spec = mock.sentinel.vm_import_spec

        if container == 'ova' and invalid_ova:
            self.assertRaises(exceptions.ImageTransferException,
                              image_transfer.download_stream_optimized_image,
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
        else:
            ret = image_transfer.download_stream_optimized_image(
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

            self.assertEqual(imported_vm, ret)
            image_service.show.assert_called_once_with(context, image_id)
            image_service.download.assert_called_once_with(context, image_id)
            image_read_handle.assert_called_once_with(read_iter)
            if container == 'ova':
                get_vmdk_handle.assert_called_once_with(read_handle)
                exp_read_handle = vmdk_handle
            else:
                exp_read_handle = read_handle
            download_stream_optimized_data.assert_called_once_with(
                context,
                timeout_secs,
                exp_read_handle,
                session=session,
                host=host,
                port=port,
                resource_pool=resource_pool,
                vm_folder=vm_folder,
                vm_import_spec=vm_import_spec,
                image_size=image_size)

    def test_download_stream_optimized_image(self):
        self._test_download_stream_optimized_image()

    def test_download_stream_optimized_image_ova(self):
        self._test_download_stream_optimized_image(container='ova')

    def test_download_stream_optimized_image_invalid_ova(self):
        self._test_download_stream_optimized_image(container='ova',
                                                   invalid_ova=True)

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
        start_transfer.assert_called_once_with(read_handle, write_handle,
                                               timeout)

    @mock.patch('oslo_vmware.rw_handles.VmdkReadHandle')
    @mock.patch.object(image_transfer, '_start_transfer')
    def test_upload_image(self, fake_transfer, fake_rw_handles_VmdkReadHandle):

        context = mock.sentinel.context
        image_id = mock.sentinel.image_id
        owner_id = mock.sentinel.owner_id
        session = mock.sentinel.session
        vm = mock.sentinel.vm
        image_service = mock.Mock()

        timeout_secs = 10
        image_size = 1000
        host = '127.0.0.1'
        port = 443
        file_path = '/fake_path'

        # TODO(vbala) Remove this after we delete the keyword argument
        # 'is_public' from all client code.
        is_public = False

        image_name = 'fake_image'
        image_version = 1

        fake_VmdkReadHandle = mock.Mock()
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

        ver_str = six.text_type(image_version)
        image_metadata = {'disk_format': 'vmdk',
                          'name': image_name,
                          'properties': {'vmware_image_version': ver_str,
                                         'vmware_disktype': 'streamOptimized',
                                         'owner_id': owner_id}}

        image_service.update.assert_called_once_with(context,
                                                     image_id,
                                                     image_metadata,
                                                     data=fake_VmdkReadHandle)
