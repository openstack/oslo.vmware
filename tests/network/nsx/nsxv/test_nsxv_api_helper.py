# Copyright 2015 VMware, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

import mock

from oslo_vmware.network.nsx.nsxv.api import api_helper
from oslo_vmware.network.nsx.nsxv.common import exceptions
from tests import base


class NsxvApiHelperTestCase(base.TestCase):

    def setUp(self):
        super(NsxvApiHelperTestCase, self).setUp()

    def test_get_success(self):
        helper = api_helper.NsxvApiHelper(
            'http://10.0.0.1',
            'testuser',
            'testpass')

        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'text/html; charset=utf-8'}
        v = '<html></html>'

        with mock.patch.object(helper, '_http_request',
                               return_value=(h, v)) as mock_request:
            helper.request('GET', '/test/index.html')

            mock_request.assert_has_calls([
                mock.call().request(
                    'http://10.0.0.1/test/index.html', 'GET', body=None,
                    headers={'Content-Type': 'application/json',
                             'Authorization':
                                 'Basic dGVzdHVzZXI6dGVzdHBhc3M=',
                             'Accept': ('application/json',)})])

    def test_get_fail(self):
        helper = api_helper.NsxvApiHelper(
            'http://10.0.0.1',
            'testuser',
            'testpass')

        h = {'status': '404',
             'connection': 'keep-alive',
             'content-type': 'text/html; charset=utf-8'}
        v = '<html></html>'

        with mock.patch.object(helper, '_http_request',
                               return_value=(h, v)):

            self.assertRaises(
                exceptions.ResourceNotFound,
                helper.request, 'GET', '/test/index.html')

    def test_put_json(self):
        helper = api_helper.NsxvApiHelper(
            'http://10.0.0.1',
            'testuser',
            'testpass',
            'json')

        h = {'status': '201',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '<html></html>'
        obj = {'test1': 'testing123'}
        with mock.patch.object(helper, '_http_request',
                               return_value=(h, v)) as mock_request:
            helper.request('PUT', '/test/index.html', obj)

            mock_request.assert_has_calls([
                mock.call().request(
                    'http://10.0.0.1/test/index.html', 'PUT',
                    body='{"test1": "testing123"}',
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': 'Basic dGVzdHVzZXI6dGVzdHBhc3M=',
                        'Accept': ('application/json',)})])

    def test_put_xml(self):
        helper = api_helper.NsxvApiHelper(
            'http://10.0.0.1',
            'testuser',
            'testpass',
            'xml')

        h = {'status': '201',
             'connection': 'keep-alive',
             'content-type': 'application/xml'}
        v = '<html></html>'
        obj = {'test1': 'testing123'}
        with mock.patch.object(helper, '_http_request',
                               return_value=(h, v)) as mock_request:
            helper.request('PUT', '/test/index.html', obj)

            mock_request.assert_has_calls([
                mock.call().request(
                    'http://10.0.0.1/test/index.html', 'PUT',
                    body='<test1>testing123</test1>',
                    headers={
                        'Content-Type': 'application/xml',
                        'Authorization': 'Basic dGVzdHVzZXI6dGVzdHBhc3M=',
                        'Accept': ('application/xml',)})])
