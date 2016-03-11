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
Unit tests for read and write handles for image transfer.
"""

import ssl

import mock
import six

from oslo_vmware import exceptions
from oslo_vmware import rw_handles
from oslo_vmware.tests import base
from oslo_vmware import vim_util


class FileHandleTest(base.TestCase):
    """Tests for FileHandle."""

    def test_close(self):
        file_handle = mock.Mock()
        vmw_http_file = rw_handles.FileHandle(file_handle)
        vmw_http_file.close()
        file_handle.close.assert_called_once_with()

    def test_find_vmdk_url(self):
        device_url_0 = mock.Mock()
        device_url_0.disk = False
        device_url_1 = mock.Mock()
        device_url_1.disk = True
        device_url_1.url = 'https://*/ds1/vm1.vmdk'
        device_url_1.sslThumbprint = '11:22:33:44:55'
        lease_info = mock.Mock()
        lease_info.deviceUrl = [device_url_0, device_url_1]
        host = '10.1.2.3'
        port = 443
        exp_url = 'https://%s:%d/ds1/vm1.vmdk' % (host, port)
        vmw_http_file = rw_handles.FileHandle(None)
        url, thumbprint = vmw_http_file._find_vmdk_url(lease_info, host, port)
        self.assertEqual(exp_url, url)
        self.assertEqual('11:22:33:44:55', thumbprint)

    @mock.patch('urllib3.connection.HTTPConnection')
    def test_create_connection_http(self, http_conn):
        conn = mock.Mock()
        http_conn.return_value = conn

        handle = rw_handles.FileHandle(None)
        ret = handle._create_connection('http://localhost/foo?q=bar', 'GET')

        self.assertEqual(conn, ret)
        conn.putrequest.assert_called_once_with('GET', '/foo?q=bar')

    @mock.patch('urllib3.connection.HTTPSConnection')
    def test_create_connection_https(self, https_conn):
        conn = mock.Mock()
        https_conn.return_value = conn

        handle = rw_handles.FileHandle(None)
        ret = handle._create_connection('https://localhost/foo?q=bar', 'GET')

        self.assertEqual(conn, ret)
        conn.set_cert.assert_called_once_with(
            ca_certs=None, cert_reqs=ssl.CERT_NONE, assert_fingerprint=None)
        conn.putrequest.assert_called_once_with('GET', '/foo?q=bar')

    @mock.patch('urllib3.connection.HTTPSConnection')
    def test_create_connection_https_with_cacerts(self, https_conn):
        conn = mock.Mock()
        https_conn.return_value = conn

        handle = rw_handles.FileHandle(None)
        ret = handle._create_connection('https://localhost/foo?q=bar', 'GET',
                                        cacerts=True)

        self.assertEqual(conn, ret)
        conn.set_cert.assert_called_once_with(
            ca_certs=None, cert_reqs=ssl.CERT_REQUIRED,
            assert_fingerprint=None)

    @mock.patch('urllib3.connection.HTTPSConnection')
    def test_create_connection_https_with_ssl_thumbprint(self, https_conn):
        conn = mock.Mock()
        https_conn.return_value = conn

        handle = rw_handles.FileHandle(None)
        cacerts = mock.sentinel.cacerts
        thumbprint = mock.sentinel.thumbprint
        ret = handle._create_connection('https://localhost/foo?q=bar', 'GET',
                                        cacerts=cacerts,
                                        ssl_thumbprint=thumbprint)

        self.assertEqual(conn, ret)
        conn.set_cert.assert_called_once_with(
            ca_certs=cacerts, cert_reqs=None, assert_fingerprint=thumbprint)


class FileWriteHandleTest(base.TestCase):
    """Tests for FileWriteHandle."""

    def setUp(self):
        super(FileWriteHandleTest, self).setUp()

        vim_cookie = mock.Mock()
        vim_cookie.name = 'name'
        vim_cookie.value = 'value'

        self._conn = mock.Mock()
        patcher = mock.patch(
            'urllib3.connection.HTTPConnection')
        self.addCleanup(patcher.stop)
        HTTPConnectionMock = patcher.start()
        HTTPConnectionMock.return_value = self._conn

        self.vmw_http_write_file = rw_handles.FileWriteHandle(
            '10.1.2.3', 443, 'dc-0', 'ds-0', [vim_cookie], '1.vmdk', 100,
            'http')

    def test_write(self):
        self.vmw_http_write_file.write(None)
        self._conn.send.assert_called_once_with(None)

    def test_close(self):
        self.vmw_http_write_file.close()
        self._conn.getresponse.assert_called_once_with()
        self._conn.close.assert_called_once_with()


class VmdkWriteHandleTest(base.TestCase):
    """Tests for VmdkWriteHandle."""

    def setUp(self):
        super(VmdkWriteHandleTest, self).setUp()
        self._conn = mock.Mock()
        patcher = mock.patch(
            'urllib3.connection.HTTPConnection')
        self.addCleanup(patcher.stop)
        HTTPConnectionMock = patcher.start()
        HTTPConnectionMock.return_value = self._conn

    def _create_mock_session(self, disk=True, progress=-1):
        device_url = mock.Mock()
        device_url.disk = disk
        device_url.url = 'http://*/ds/disk1.vmdk'
        lease_info = mock.Mock()
        lease_info.deviceUrl = [device_url]
        session = mock.Mock()

        def session_invoke_api_side_effect(module, method, *args, **kwargs):
            if module == session.vim:
                if method == 'ImportVApp':
                    return mock.Mock()
                elif method == 'HttpNfcLeaseProgress':
                    self.assertEqual(progress, kwargs['percent'])
                    return
            return lease_info

        session.invoke_api.side_effect = session_invoke_api_side_effect
        vim_cookie = mock.Mock()
        vim_cookie.name = 'name'
        vim_cookie.value = 'value'
        session.vim.client.options.transport.cookiejar = [vim_cookie]
        return session

    def test_init_failure(self):
        session = self._create_mock_session(False)
        self.assertRaises(exceptions.VimException,
                          rw_handles.VmdkWriteHandle,
                          session,
                          '10.1.2.3',
                          443,
                          'rp-1',
                          'folder-1',
                          None,
                          100)

    def test_write(self):
        session = self._create_mock_session()
        handle = rw_handles.VmdkWriteHandle(session, '10.1.2.3', 443,
                                            'rp-1', 'folder-1', None,
                                            100)
        data = [1] * 10
        handle.write(data)
        self.assertEqual(len(data), handle._bytes_written)
        self._conn.putrequest.assert_called_once_with('PUT', '/ds/disk1.vmdk')
        self._conn.send.assert_called_once_with(data)

    def test_write_post(self):
        session = self._create_mock_session()
        handle = rw_handles.VmdkWriteHandle(session, '10.1.2.3', 443,
                                            'rp-1', 'folder-1', None,
                                            100, http_method='POST')
        data = [1] * 10
        handle.write(data)
        self.assertEqual(len(data), handle._bytes_written)
        self._conn.putrequest.assert_called_once_with('POST', '/ds/disk1.vmdk')
        self._conn.send.assert_called_once_with(data)

    def test_update_progress(self):
        vmdk_size = 100
        data_size = 10
        session = self._create_mock_session(True, 10)
        handle = rw_handles.VmdkWriteHandle(session, '10.1.2.3', 443,
                                            'rp-1', 'folder-1', None,
                                            vmdk_size)
        handle.write([1] * data_size)
        handle.update_progress()

    def test_update_progress_with_error(self):
        session = self._create_mock_session(True, 10)
        handle = rw_handles.VmdkWriteHandle(session, '10.1.2.3', 443,
                                            'rp-1', 'folder-1', None,
                                            100)
        session.invoke_api.side_effect = exceptions.VimException(None)
        self.assertRaises(exceptions.VimException, handle.update_progress)

    def test_close(self):
        session = self._create_mock_session()
        handle = rw_handles.VmdkWriteHandle(session, '10.1.2.3', 443,
                                            'rp-1', 'folder-1', None,
                                            100)

        def session_invoke_api_side_effect(module, method, *args, **kwargs):
            if module == vim_util and method == 'get_object_property':
                return 'ready'
            self.assertEqual(session.vim, module)
            self.assertEqual('HttpNfcLeaseComplete', method)

        session.invoke_api = mock.Mock(
            side_effect=session_invoke_api_side_effect)
        handle.close()
        self.assertEqual(2, session.invoke_api.call_count)


class VmdkReadHandleTest(base.TestCase):
    """Tests for VmdkReadHandle."""

    def setUp(self):
        super(VmdkReadHandleTest, self).setUp()
        self._resp = mock.Mock()
        self._resp.read.return_value = 'fake-data'
        self._conn = mock.Mock()
        self._conn.getresponse.return_value = self._resp
        patcher = mock.patch(
            'urllib3.connection.HTTPConnection')
        self.addCleanup(patcher.stop)
        HTTPConnectionMock = patcher.start()
        HTTPConnectionMock.return_value = self._conn

    def _create_mock_session(self, disk=True, progress=-1):
        device_url = mock.Mock()
        device_url.disk = disk
        device_url.url = 'http://*/ds/disk1.vmdk'
        lease_info = mock.Mock()
        lease_info.deviceUrl = [device_url]
        session = mock.Mock()

        def session_invoke_api_side_effect(module, method, *args, **kwargs):
            if module == session.vim:
                if method == 'ExportVm':
                    return mock.Mock()
                elif method == 'HttpNfcLeaseProgress':
                    self.assertEqual(progress, kwargs['percent'])
                    return
            return lease_info

        session.invoke_api.side_effect = session_invoke_api_side_effect
        vim_cookie = mock.Mock()
        vim_cookie.name = 'name'
        vim_cookie.value = 'value'
        session.vim.client.options.transport.cookiejar = [vim_cookie]
        return session

    def test_init_failure(self):
        session = self._create_mock_session(False)
        self.assertRaises(exceptions.VimException,
                          rw_handles.VmdkReadHandle,
                          session,
                          '10.1.2.3',
                          443,
                          'vm-1',
                          '[ds] disk1.vmdk',
                          100)

    def test_read(self):
        chunk_size = rw_handles.READ_CHUNKSIZE
        session = self._create_mock_session()
        handle = rw_handles.VmdkReadHandle(session, '10.1.2.3', 443,
                                           'vm-1', '[ds] disk1.vmdk',
                                           chunk_size * 10)
        data = handle.read(chunk_size)
        self.assertEqual('fake-data', data)

    def test_update_progress(self):
        chunk_size = len('fake-data')
        vmdk_size = chunk_size * 10
        session = self._create_mock_session(True, 10)
        handle = rw_handles.VmdkReadHandle(session, '10.1.2.3', 443,
                                           'vm-1', '[ds] disk1.vmdk',
                                           vmdk_size)
        data = handle.read(chunk_size)
        handle.update_progress()
        self.assertEqual('fake-data', data)

    def test_update_progress_with_error(self):
        session = self._create_mock_session(True, 10)
        handle = rw_handles.VmdkReadHandle(session, '10.1.2.3', 443,
                                           'vm-1', '[ds] disk1.vmdk',
                                           100)
        session.invoke_api.side_effect = exceptions.VimException(None)
        self.assertRaises(exceptions.VimException, handle.update_progress)

    def test_close(self):
        session = self._create_mock_session()
        handle = rw_handles.VmdkReadHandle(session, '10.1.2.3', 443,
                                           'vm-1', '[ds] disk1.vmdk',
                                           100)

        def session_invoke_api_side_effect(module, method, *args, **kwargs):
            if module == vim_util and method == 'get_object_property':
                return 'ready'
            self.assertEqual(session.vim, module)
            self.assertEqual('HttpNfcLeaseComplete', method)

        session.invoke_api = mock.Mock(
            side_effect=session_invoke_api_side_effect)
        handle.close()
        self.assertEqual(2, session.invoke_api.call_count)

    def test_close_with_error(self):
        session = self._create_mock_session()
        handle = rw_handles.VmdkReadHandle(session, '10.1.2.3', 443,
                                           'vm-1', '[ds] disk1.vmdk',
                                           100)
        session.invoke_api.side_effect = exceptions.VimException(None)

        self.assertRaises(exceptions.VimException, handle.close)
        self._resp.close.assert_called_once_with()


class ImageReadHandleTest(base.TestCase):
    """Tests for ImageReadHandle."""

    def test_read(self):
        max_items = 10
        item = [1] * 10

        class ImageReadIterator(six.Iterator):

            def __init__(self):
                self.num_items = 0

            def __iter__(self):
                return self

            def __next__(self):
                if (self.num_items < max_items):
                    self.num_items += 1
                    return item
                raise StopIteration

            next = __next__

        handle = rw_handles.ImageReadHandle(ImageReadIterator())
        for _ in range(0, max_items):
            self.assertEqual(item, handle.read(10))
        self.assertFalse(handle.read(10))
