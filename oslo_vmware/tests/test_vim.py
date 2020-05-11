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

"""Unit tests for classes to invoke VMware VI SOAP calls."""

import copy
from unittest import mock

from oslo_i18n import fixture as i18n_fixture
import suds

from oslo_vmware import exceptions
from oslo_vmware.tests import base
from oslo_vmware import vim


class VimTest(base.TestCase):
    """Test class for Vim."""

    def setUp(self):
        super(VimTest, self).setUp()
        patcher = mock.patch('oslo_vmware.service.CompatibilitySudsClient')
        self.addCleanup(patcher.stop)
        self.SudsClientMock = patcher.start()
        self.useFixture(i18n_fixture.ToggleLazy(True))

    @mock.patch.object(vim.Vim, '__getattr__', autospec=True)
    def test_service_content(self, getattr_mock):
        getattr_ret = mock.Mock()
        getattr_mock.side_effect = lambda *args: getattr_ret
        vim_obj = vim.Vim()
        vim_obj.service_content
        getattr_mock.assert_called_once_with(vim_obj, 'RetrieveServiceContent')
        getattr_ret.assert_called_once_with('ServiceInstance')
        self.assertEqual(self.SudsClientMock.return_value, vim_obj.client)
        self.assertEqual(getattr_ret.return_value, vim_obj.service_content)

    def test_configure_non_default_host_port(self):
        vim_obj = vim.Vim('https', 'www.test.com', 12345)
        self.assertEqual('https://www.test.com:12345/sdk/vimService.wsdl',
                         vim_obj.wsdl_url)
        self.assertEqual('https://www.test.com:12345/sdk',
                         vim_obj.soap_url)

    def test_configure_ipv6(self):
        vim_obj = vim.Vim('https', '::1')
        self.assertEqual('https://[::1]/sdk/vimService.wsdl',
                         vim_obj.wsdl_url)
        self.assertEqual('https://[::1]/sdk',
                         vim_obj.soap_url)

    def test_configure_ipv6_and_non_default_host_port(self):
        vim_obj = vim.Vim('https', '::1', 12345)
        self.assertEqual('https://[::1]:12345/sdk/vimService.wsdl',
                         vim_obj.wsdl_url)
        self.assertEqual('https://[::1]:12345/sdk',
                         vim_obj.soap_url)

    def test_configure_with_wsdl_url_override(self):
        vim_obj = vim.Vim('https', 'www.example.com',
                          wsdl_url='https://test.com/sdk/vimService.wsdl')
        self.assertEqual('https://test.com/sdk/vimService.wsdl',
                         vim_obj.wsdl_url)
        self.assertEqual('https://www.example.com/sdk', vim_obj.soap_url)


class VMwareSudsTest(base.TestCase):
    def setUp(self):
        super(VMwareSudsTest, self).setUp()

        def new_client_init(self, url, **kwargs):
            return

        mock.patch.object(suds.client.Client,
                          '__init__', new=new_client_init).start()
        self.addCleanup(mock.patch.stopall)
        self.vim = self._vim_create()

    def _mock_getattr(self, attr_name):
        class fake_service_content(object):
            def __init__(self):
                self.ServiceContent = {}
                self.ServiceContent.fake = 'fake'

        self.assertEqual("RetrieveServiceContent", attr_name)
        return lambda obj, **kwargs: fake_service_content()

    def _vim_create(self):
        with mock.patch.object(vim.Vim, '__getattr__', self._mock_getattr):
            return vim.Vim()

    def test_exception_with_deepcopy(self):
        self.assertIsNotNone(self.vim)
        self.assertRaises(exceptions.VimAttributeException,
                          copy.deepcopy, self.vim)
