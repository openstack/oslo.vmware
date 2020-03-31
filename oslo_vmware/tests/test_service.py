# Copyright (c) 2014-2020 VMware, Inc.
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

import http.client as httplib
import io
from unittest import mock

import ddt
import requests
import suds

from oslo_vmware import exceptions
from oslo_vmware import service
from oslo_vmware.tests import base
from oslo_vmware import vim_util


@ddt.ddt
class ServiceMessagePluginTest(base.TestCase):
    """Test class for ServiceMessagePlugin."""

    def setUp(self):
        super(ServiceMessagePluginTest, self).setUp()
        self.plugin = service.ServiceMessagePlugin()

    @ddt.data(('value', 'foo', 'string'), ('removeKey', '1', 'int'),
              ('removeKey', 'foo', 'string'))
    @ddt.unpack
    def test_add_attribute_for_value(self, name, text, expected_xsd_type):
        node = mock.Mock()
        node.name = name
        node.text = text
        self.plugin.add_attribute_for_value(node)
        node.set.assert_called_once_with('xsi:type',
                                         'xsd:%s' % expected_xsd_type)

    def test_marshalled(self):
        context = mock.Mock()
        self.plugin.prune = mock.Mock()
        self.plugin.marshalled(context)
        self.plugin.prune.assert_called_once_with(context.envelope)
        context.envelope.walk.assert_called_once_with(
            self.plugin.add_attribute_for_value)


@ddt.ddt
class ServiceTest(base.TestCase):

    def setUp(self):
        super(ServiceTest, self).setUp()
        patcher = mock.patch('suds.client.Client')
        self.addCleanup(patcher.stop)
        self.SudsClientMock = patcher.start()

    def test_retrieve_properties_ex_fault_checker_with_empty_response(self):
        ex = self.assertRaises(
            exceptions.VimFaultException,
            service.Service._retrieve_properties_ex_fault_checker,
            None)
        self.assertEqual([exceptions.NOT_AUTHENTICATED],
                         ex.fault_list)

    def test_retrieve_properties_ex_fault_checker(self):
        fault_list = ['FileFault', 'VimFault']
        missing_set = []
        for fault in fault_list:
            missing_elem = mock.Mock()
            missing_elem.fault.fault.__class__.__name__ = fault
            missing_set.append(missing_elem)
        obj_cont = mock.Mock()
        obj_cont.missingSet = missing_set
        response = mock.Mock()
        response.objects = [obj_cont]

        ex = self.assertRaises(
            exceptions.VimFaultException,
            service.Service._retrieve_properties_ex_fault_checker,
            response)
        self.assertEqual(fault_list, ex.fault_list)

    def test_request_handler(self):
        managed_object = 'VirtualMachine'
        resp = mock.Mock()

        def side_effect(mo, **kwargs):
            self.assertEqual(managed_object, mo._type)
            self.assertEqual(managed_object, mo.value)
            return resp

        svc_obj = service.Service()
        attr_name = 'powerOn'
        service_mock = svc_obj.client.service
        setattr(service_mock, attr_name, side_effect)
        ret = svc_obj.powerOn(managed_object)
        self.assertEqual(resp, ret)

    def test_request_handler_with_retrieve_properties_ex_fault(self):
        managed_object = 'Datacenter'

        def side_effect(mo, **kwargs):
            self.assertEqual(managed_object, mo._type)
            self.assertEqual(managed_object, mo.value)
            return None

        svc_obj = service.Service()
        attr_name = 'retrievePropertiesEx'
        service_mock = svc_obj.client.service
        setattr(service_mock, attr_name, side_effect)
        self.assertRaises(exceptions.VimFaultException,
                          svc_obj.retrievePropertiesEx,
                          managed_object)

    def test_request_handler_with_web_fault(self):
        managed_object = 'VirtualMachine'
        fault_list = ['Fault']

        doc = mock.Mock()

        def side_effect(mo, **kwargs):
            self.assertEqual(managed_object, mo._type)
            self.assertEqual(managed_object, mo.value)
            fault = mock.Mock(faultstring="MyFault")

            fault_children = mock.Mock()
            fault_children.name = "name"
            fault_children.getText.return_value = "value"
            child = mock.Mock()
            child.get.return_value = fault_list[0]
            child.getChildren.return_value = [fault_children]
            detail = mock.Mock()
            detail.getChildren.return_value = [child]
            doc.childAtPath.return_value = detail
            raise suds.WebFault(fault, doc)

        svc_obj = service.Service()
        service_mock = svc_obj.client.service
        setattr(service_mock, 'powerOn', side_effect)

        ex = self.assertRaises(exceptions.VimFaultException, svc_obj.powerOn,
                               managed_object)

        self.assertEqual(fault_list, ex.fault_list)
        self.assertEqual({'name': 'value'}, ex.details)
        self.assertEqual("MyFault", ex.msg)
        doc.childAtPath.assert_called_once_with('/detail')

    def test_request_handler_with_empty_web_fault_doc(self):

        def side_effect(mo, **kwargs):
            fault = mock.Mock(faultstring="MyFault")
            raise suds.WebFault(fault, None)

        svc_obj = service.Service()
        service_mock = svc_obj.client.service
        setattr(service_mock, 'powerOn', side_effect)

        ex = self.assertRaises(exceptions.VimFaultException,
                               svc_obj.powerOn,
                               'VirtualMachine')
        self.assertEqual([], ex.fault_list)
        self.assertEqual({}, ex.details)
        self.assertEqual("MyFault", ex.msg)

    def test_request_handler_with_vc51_web_fault(self):
        managed_object = 'VirtualMachine'
        fault_list = ['Fault']

        doc = mock.Mock()

        def side_effect(mo, **kwargs):
            self.assertEqual(managed_object, mo._type)
            self.assertEqual(managed_object, mo.value)
            fault = mock.Mock(faultstring="MyFault")

            fault_children = mock.Mock()
            fault_children.name = "name"
            fault_children.getText.return_value = "value"
            child = mock.Mock()
            child.get.return_value = fault_list[0]
            child.getChildren.return_value = [fault_children]
            detail = mock.Mock()
            detail.getChildren.return_value = [child]
            doc.childAtPath.side_effect = [None, detail]
            raise suds.WebFault(fault, doc)

        svc_obj = service.Service()
        service_mock = svc_obj.client.service
        setattr(service_mock, 'powerOn', side_effect)

        ex = self.assertRaises(exceptions.VimFaultException, svc_obj.powerOn,
                               managed_object)

        self.assertEqual(fault_list, ex.fault_list)
        self.assertEqual({'name': 'value'}, ex.details)
        self.assertEqual("MyFault", ex.msg)
        exp_calls = [mock.call('/detail'),
                     mock.call('/Envelope/Body/Fault/detail')]
        self.assertEqual(exp_calls, doc.childAtPath.call_args_list)

    @ddt.data('vim25:SecurityError', 'vim25:NotAuthenticated')
    def test_request_handler_with_pbm_session_error(self, fault_name):
        managed_object = 'ProfileManager'
        doc = mock.Mock()

        def side_effect(mo, **kwargs):
            self.assertEqual(managed_object, mo._type)
            self.assertEqual(managed_object, mo.value)
            fault = mock.Mock(faultstring="MyFault")

            fault_children = mock.Mock()
            fault_children.name = "name"
            fault_children.getText.return_value = "value"
            child = mock.Mock()
            child.get.return_value = fault_name
            child.getChildren.return_value = [fault_children]
            detail = mock.Mock()
            detail.getChildren.return_value = [child]
            doc.childAtPath.return_value = detail
            raise suds.WebFault(fault, doc)

        svc_obj = service.Service()
        service_mock = svc_obj.client.service
        setattr(service_mock, 'get_profile_id_by_name', side_effect)

        ex = self.assertRaises(exceptions.VimFaultException,
                               svc_obj.get_profile_id_by_name,
                               managed_object)

        self.assertEqual([exceptions.NOT_AUTHENTICATED], ex.fault_list)
        self.assertEqual({'name': 'value'}, ex.details)
        self.assertEqual("MyFault", ex.msg)
        doc.childAtPath.assert_called_once_with('/detail')

    def test_request_handler_with_attribute_error(self):
        managed_object = 'VirtualMachine'
        svc_obj = service.Service()
        # no powerOn method in Service
        service_mock = mock.Mock(spec=service.Service)
        svc_obj.client.service = service_mock
        self.assertRaises(exceptions.VimAttributeException,
                          svc_obj.powerOn,
                          managed_object)

    def test_request_handler_with_http_cannot_send_error(self):
        managed_object = 'VirtualMachine'

        def side_effect(mo, **kwargs):
            self.assertEqual(managed_object, mo._type)
            self.assertEqual(managed_object, mo.value)
            raise httplib.CannotSendRequest()

        svc_obj = service.Service()
        attr_name = 'powerOn'
        service_mock = svc_obj.client.service
        setattr(service_mock, attr_name, side_effect)
        self.assertRaises(exceptions.VimSessionOverLoadException,
                          svc_obj.powerOn,
                          managed_object)

    def test_request_handler_with_http_response_not_ready_error(self):
        managed_object = 'VirtualMachine'

        def side_effect(mo, **kwargs):
            self.assertEqual(managed_object, mo._type)
            self.assertEqual(managed_object, mo.value)
            raise httplib.ResponseNotReady()

        svc_obj = service.Service()
        attr_name = 'powerOn'
        service_mock = svc_obj.client.service
        setattr(service_mock, attr_name, side_effect)
        self.assertRaises(exceptions.VimSessionOverLoadException,
                          svc_obj.powerOn,
                          managed_object)

    def test_request_handler_with_http_cannot_send_header_error(self):
        managed_object = 'VirtualMachine'

        def side_effect(mo, **kwargs):
            self.assertEqual(managed_object, mo._type)
            self.assertEqual(managed_object, mo.value)
            raise httplib.CannotSendHeader()

        svc_obj = service.Service()
        attr_name = 'powerOn'
        service_mock = svc_obj.client.service
        setattr(service_mock, attr_name, side_effect)
        self.assertRaises(exceptions.VimSessionOverLoadException,
                          svc_obj.powerOn,
                          managed_object)

    def test_request_handler_with_connection_error(self):
        managed_object = 'VirtualMachine'

        def side_effect(mo, **kwargs):
            self.assertEqual(managed_object, mo._type)
            self.assertEqual(managed_object, mo.value)
            raise requests.ConnectionError()

        svc_obj = service.Service()
        attr_name = 'powerOn'
        service_mock = svc_obj.client.service
        setattr(service_mock, attr_name, side_effect)
        self.assertRaises(exceptions.VimConnectionException,
                          svc_obj.powerOn,
                          managed_object)

    def test_request_handler_with_http_error(self):
        managed_object = 'VirtualMachine'

        def side_effect(mo, **kwargs):
            self.assertEqual(managed_object, mo._type)
            self.assertEqual(managed_object, mo.value)
            raise requests.HTTPError()

        svc_obj = service.Service()
        attr_name = 'powerOn'
        service_mock = svc_obj.client.service
        setattr(service_mock, attr_name, side_effect)
        self.assertRaises(exceptions.VimConnectionException,
                          svc_obj.powerOn,
                          managed_object)

    @mock.patch.object(vim_util, 'get_moref', return_value=None)
    def test_request_handler_no_value(self, mock_moref):
        managed_object = 'VirtualMachine'
        svc_obj = service.Service()
        ret = svc_obj.UnregisterVM(managed_object)
        self.assertIsNone(ret)

    def _test_request_handler_with_exception(self, message, exception):
        managed_object = 'VirtualMachine'

        def side_effect(mo, **kwargs):
            self.assertEqual(managed_object, mo._type)
            self.assertEqual(managed_object, mo.value)
            raise Exception(message)

        svc_obj = service.Service()
        attr_name = 'powerOn'
        service_mock = svc_obj.client.service
        setattr(service_mock, attr_name, side_effect)
        self.assertRaises(exception, svc_obj.powerOn, managed_object)

    def test_request_handler_with_address_in_use_error(self):
        self._test_request_handler_with_exception(
            service.ADDRESS_IN_USE_ERROR,
            exceptions.VimSessionOverLoadException)

    def test_request_handler_with_conn_abort_error(self):
        self._test_request_handler_with_exception(
            service.CONN_ABORT_ERROR, exceptions.VimSessionOverLoadException)

    def test_request_handler_with_resp_not_xml_error(self):
        self._test_request_handler_with_exception(
            service.RESP_NOT_XML_ERROR, exceptions.VimSessionOverLoadException)

    def test_request_handler_with_generic_error(self):
        self._test_request_handler_with_exception(
            'GENERIC_ERROR', exceptions.VimException)

    def test_get_session_cookie(self):
        svc_obj = service.Service()
        cookie_value = 'xyz'
        cookie = mock.Mock()
        cookie.name = 'vmware_soap_session'
        cookie.value = cookie_value
        svc_obj.client.options.transport.cookiejar = [cookie]
        self.assertEqual(cookie_value, svc_obj.get_http_cookie())

    def test_get_session_cookie_with_no_cookie(self):
        svc_obj = service.Service()
        cookie = mock.Mock()
        cookie.name = 'cookie'
        cookie.value = 'xyz'
        svc_obj.client.options.transport.cookiejar = [cookie]
        self.assertIsNone(svc_obj.get_http_cookie())

    def test_set_soap_headers(self):
        def fake_set_options(*args, **kwargs):
            headers = kwargs['soapheaders']
            self.assertEqual(1, len(headers))
            txt = headers[0].getText()
            self.assertEqual('fira-12345', txt)

        svc_obj = service.Service()
        svc_obj.client.options.soapheaders = None
        setattr(svc_obj.client, 'set_options', fake_set_options)
        svc_obj._set_soap_headers('fira-12345')

    def test_soap_headers_pbm(self):
        def fake_set_options(*args, **kwargs):
            headers = kwargs['soapheaders']
            self.assertEqual(2, len(headers))
            self.assertEqual('vc-session-cookie', headers[0].getText())
            self.assertEqual('fira-12345', headers[1].getText())

        svc_obj = service.Service()
        svc_obj._vc_session_cookie = 'vc-session-cookie'
        setattr(svc_obj.client, 'set_options', fake_set_options)
        svc_obj._set_soap_headers('fira-12345')


class MemoryCacheTest(base.TestCase):
    """Test class for MemoryCache."""

    def test_get_set(self):
        cache = service.MemoryCache()
        cache.put('key1', 'value1')
        cache.put('key2', 'value2')
        self.assertEqual('value1', cache.get('key1'))
        self.assertEqual('value2', cache.get('key2'))
        self.assertIsNone(cache.get('key3'))

    @mock.patch('suds.reader.DefinitionsReader.open')
    @mock.patch('suds.reader.DocumentReader.download', create=True)
    def test_shared_cache(self, mock_reader, mock_open):
        cache1 = service.Service().client.options.cache
        cache2 = service.Service().client.options.cache
        self.assertIs(cache1, cache2)

    @mock.patch('oslo_utils.timeutils.utcnow_ts')
    def test_cache_timeout(self, mock_utcnow_ts):
        mock_utcnow_ts.side_effect = [100, 125, 150, 175, 195, 200, 225]

        cache = service.MemoryCache()
        cache.put('key1', 'value1', 10)
        cache.put('key2', 'value2', 75)
        cache.put('key3', 'value3', 100)

        self.assertIsNone(cache.get('key1'))
        self.assertEqual('value2', cache.get('key2'))
        self.assertIsNone(cache.get('key2'))
        self.assertEqual('value3', cache.get('key3'))


class RequestsTransportTest(base.TestCase):
    """Tests for RequestsTransport."""

    def test_open(self):
        transport = service.RequestsTransport()

        data = b"Hello World"
        resp = mock.Mock(content=data)
        transport.session.get = mock.Mock(return_value=resp)

        request = mock.Mock(url=mock.sentinel.url)
        self.assertEqual(data,
                         transport.open(request).getvalue())
        transport.session.get.assert_called_once_with(mock.sentinel.url,
                                                      verify=transport.verify)

    def test_send(self):
        transport = service.RequestsTransport()

        resp = mock.Mock(status_code=mock.sentinel.status_code,
                         headers=mock.sentinel.headers,
                         content=mock.sentinel.content)
        transport.session.post = mock.Mock(return_value=resp)

        request = mock.Mock(url=mock.sentinel.url,
                            message=mock.sentinel.message,
                            headers=mock.sentinel.req_headers)
        reply = transport.send(request)

        self.assertEqual(mock.sentinel.status_code, reply.code)
        self.assertEqual(mock.sentinel.headers, reply.headers)
        self.assertEqual(mock.sentinel.content, reply.message)

    def test_set_conn_pool_size(self):
        transport = service.RequestsTransport(pool_maxsize=100)
        local_file_adapter = transport.session.adapters['file:///']
        self.assertEqual(100, local_file_adapter._pool_connections)
        self.assertEqual(100, local_file_adapter._pool_maxsize)
        https_adapter = transport.session.adapters['https://']
        self.assertEqual(100, https_adapter._pool_connections)
        self.assertEqual(100, https_adapter._pool_maxsize)

    @mock.patch('os.path.getsize')
    def test_send_with_local_file_url(self, get_size_mock):
        transport = service.RequestsTransport()

        url = 'file:///foo'
        request = requests.PreparedRequest()
        request.url = url

        data = b"Hello World"
        get_size_mock.return_value = len(data)

        def read_mock():
            return data

        builtin_open = 'builtins.open'
        open_mock = mock.MagicMock(name='file_handle',
                                   spec=open)
        file_spec = list(set(dir(io.TextIOWrapper)).union(
            set(dir(io.BytesIO))))

        file_handle = mock.MagicMock(spec=file_spec)
        file_handle.write.return_value = None
        file_handle.__enter__.return_value = file_handle
        file_handle.read.side_effect = read_mock
        open_mock.return_value = file_handle

        with mock.patch(builtin_open, open_mock, create=True):
            resp = transport.session.send(request)
            self.assertEqual(data, resp.content)

    def test_send_with_connection_timeout(self):
        transport = service.RequestsTransport(connection_timeout=120)

        request = mock.Mock(url=mock.sentinel.url,
                            message=mock.sentinel.message,
                            headers=mock.sentinel.req_headers)
        with mock.patch.object(transport.session, "post") as mock_post:
            transport.send(request)
            mock_post.assert_called_once_with(
                mock.sentinel.url,
                data=mock.sentinel.message,
                headers=mock.sentinel.req_headers,
                timeout=120,
                verify=transport.verify)


class SudsLogFilterTest(base.TestCase):
    """Tests for SudsLogFilter."""

    def setUp(self):
        super(SudsLogFilterTest, self).setUp()
        self.log_filter = service.SudsLogFilter()

        self.login = mock.Mock(spec=suds.sax.element.Element)
        self.username = suds.sax.element.Element('username').setText('admin')
        self.password = suds.sax.element.Element('password').setText(
            'password')
        self.session_id = suds.sax.element.Element('session_id').setText(
            'abcdef')

        def login_child_at_path_mock(path):
            if path == 'userName':
                return self.username
            if path == 'password':
                return self.password
            if path == 'sessionID':
                return self.session_id

        self.login.childAtPath.side_effect = login_child_at_path_mock

    def test_filter_with_no_child_at_path(self):
        message = mock.Mock(spec=object)
        record = mock.Mock(msg=message)
        self.assertTrue(self.log_filter.filter(record))

    def test_filter_with_login_failure(self):
        message = mock.Mock(spec=suds.sax.element.Element)

        def child_at_path_mock(path):
            if path == '/Envelope/Body/Login':
                return self.login

        message.childAtPath.side_effect = child_at_path_mock
        record = mock.Mock(msg=message)

        self.assertTrue(self.log_filter.filter(record))
        self.assertEqual('***', self.username.getText())
        self.assertEqual('***', self.password.getText())
        self.assertEqual('bcdef', self.session_id.getText())

    def test_filter_with_session_is_active_failure(self):
        message = mock.Mock(spec=suds.sax.element.Element)

        def child_at_path_mock(path):
            if path == '/Envelope/Body/SessionIsActive':
                return self.login

        message.childAtPath.side_effect = child_at_path_mock
        record = mock.Mock(msg=message)

        self.assertTrue(self.log_filter.filter(record))
        self.assertEqual('***', self.username.getText())
        self.assertEqual('***', self.password.getText())
        self.assertEqual('bcdef', self.session_id.getText())

    def test_filter_with_unknown_failure(self):
        message = mock.Mock(spec=suds.sax.element.Element)

        def child_at_path_mock(path):
            return None

        message.childAtPath.side_effect = child_at_path_mock
        record = mock.Mock(msg=message)

        self.assertTrue(self.log_filter.filter(record))
        self.assertEqual('admin', self.username.getText())
        self.assertEqual('password', self.password.getText())
        self.assertEqual('abcdef', self.session_id.getText())
