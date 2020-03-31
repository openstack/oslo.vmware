# coding=utf-8
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

"""Unit tests for session management and API invocation classes."""

from datetime import datetime
from unittest import mock

from eventlet import greenthread
from oslo_context import context
import suds

from oslo_vmware import api
from oslo_vmware import exceptions
from oslo_vmware import pbm
from oslo_vmware.tests import base
from oslo_vmware import vim_util


class RetryDecoratorTest(base.TestCase):
    """Tests for retry decorator class."""

    def test_retry(self):
        result = "RESULT"

        @api.RetryDecorator()
        def func(*args, **kwargs):
            return result

        self.assertEqual(result, func())

        def func2(*args, **kwargs):
            return result

        retry = api.RetryDecorator()
        self.assertEqual(result, retry(func2)())
        self.assertTrue(retry._retry_count == 0)

    def test_retry_with_expected_exceptions(self):
        result = "RESULT"
        responses = [exceptions.VimSessionOverLoadException(None),
                     exceptions.VimSessionOverLoadException(None),
                     result]

        def func(*args, **kwargs):
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        sleep_time_incr = 0.01
        retry_count = 2
        retry = api.RetryDecorator(10, sleep_time_incr, 10,
                                   (exceptions.VimSessionOverLoadException,))
        self.assertEqual(result, retry(func)())
        self.assertTrue(retry._retry_count == retry_count)
        self.assertEqual(retry_count * sleep_time_incr, retry._sleep_time)

    def test_retry_with_max_retries(self):
        responses = [exceptions.VimSessionOverLoadException(None),
                     exceptions.VimSessionOverLoadException(None),
                     exceptions.VimSessionOverLoadException(None)]

        def func(*args, **kwargs):
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        retry = api.RetryDecorator(2, 0, 0,
                                   (exceptions.VimSessionOverLoadException,))
        self.assertRaises(exceptions.VimSessionOverLoadException, retry(func))
        self.assertTrue(retry._retry_count == 2)

    def test_retry_with_unexpected_exception(self):

        def func(*args, **kwargs):
            raise exceptions.VimException(None)

        retry = api.RetryDecorator()
        self.assertRaises(exceptions.VimException, retry(func))
        self.assertTrue(retry._retry_count == 0)


class VMwareAPISessionTest(base.TestCase):
    """Tests for VMwareAPISession."""

    SERVER_IP = '10.1.2.3'
    PORT = 443
    USERNAME = 'admin'
    PASSWORD = 'password'  # nosec
    POOL_SIZE = 15

    def setUp(self):
        super(VMwareAPISessionTest, self).setUp()
        patcher = mock.patch('oslo_vmware.vim.Vim')
        self.addCleanup(patcher.stop)
        self.VimMock = patcher.start()
        self.VimMock.side_effect = lambda *args, **kw: mock.MagicMock()
        self.cert_mock = mock.Mock()

    def _create_api_session(self, _create_session, retry_count=10,
                            task_poll_interval=1):
        return api.VMwareAPISession(VMwareAPISessionTest.SERVER_IP,
                                    VMwareAPISessionTest.USERNAME,
                                    VMwareAPISessionTest.PASSWORD,
                                    retry_count,
                                    task_poll_interval,
                                    'https',
                                    _create_session,
                                    port=VMwareAPISessionTest.PORT,
                                    cacert=self.cert_mock,
                                    insecure=False,
                                    pool_size=VMwareAPISessionTest.POOL_SIZE)

    def test_vim(self):
        api_session = self._create_api_session(False)
        api_session.vim
        self.VimMock.assert_called_with(
            protocol=api_session._scheme,
            host=VMwareAPISessionTest.SERVER_IP,
            port=VMwareAPISessionTest.PORT,
            wsdl_url=api_session._vim_wsdl_loc,
            cacert=self.cert_mock,
            insecure=False,
            pool_maxsize=VMwareAPISessionTest.POOL_SIZE,
            connection_timeout=None,
            op_id_prefix='oslo.vmware')

    @mock.patch.object(pbm, 'Pbm')
    def test_pbm(self, pbm_mock):
        api_session = self._create_api_session(True)
        vim_obj = api_session.vim
        cookie = mock.Mock()
        vim_obj.get_http_cookie.return_value = cookie
        api_session._pbm_wsdl_loc = mock.Mock()

        pbm = mock.Mock()
        pbm_mock.return_value = pbm
        api_session._get_session_cookie = mock.Mock(return_value=cookie)

        self.assertEqual(pbm, api_session.pbm)
        pbm.set_soap_cookie.assert_called_once_with(cookie)

    def test_create_session(self):
        session = mock.Mock()
        session.key = "12345"
        api_session = self._create_api_session(False)
        cookie = mock.Mock()
        vim_obj = api_session.vim
        vim_obj.Login.return_value = session
        vim_obj.get_http_cookie.return_value = cookie

        pbm = mock.Mock()
        api_session._pbm = pbm

        api_session._create_session()
        session_manager = vim_obj.service_content.sessionManager
        vim_obj.Login.assert_called_once_with(
            session_manager, userName=VMwareAPISessionTest.USERNAME,
            password=VMwareAPISessionTest.PASSWORD, locale='en')
        self.assertFalse(vim_obj.TerminateSession.called)
        self.assertEqual(session.key, api_session._session_id)
        pbm.set_soap_cookie.assert_called_once_with(cookie)

    def test_create_session_with_existing_inactive_session(self):
        old_session_key = '12345'
        new_session_key = '67890'
        session = mock.Mock()
        session.key = new_session_key
        api_session = self._create_api_session(False)
        api_session._session_id = old_session_key
        api_session._session_username = api_session._server_username
        vim_obj = api_session.vim
        vim_obj.Login.return_value = session
        vim_obj.SessionIsActive.return_value = False

        api_session._create_session()
        session_manager = vim_obj.service_content.sessionManager
        vim_obj.SessionIsActive.assert_called_once_with(
            session_manager, sessionID=old_session_key,
            userName=VMwareAPISessionTest.USERNAME)
        vim_obj.Login.assert_called_once_with(
            session_manager, userName=VMwareAPISessionTest.USERNAME,
            password=VMwareAPISessionTest.PASSWORD, locale='en')
        self.assertEqual(new_session_key, api_session._session_id)

    def test_create_session_with_existing_active_session(self):
        old_session_key = '12345'
        api_session = self._create_api_session(False)
        api_session._session_id = old_session_key
        api_session._session_username = api_session._server_username
        vim_obj = api_session.vim
        vim_obj.SessionIsActive.return_value = True

        api_session._create_session()
        session_manager = vim_obj.service_content.sessionManager
        vim_obj.SessionIsActive.assert_called_once_with(
            session_manager, sessionID=old_session_key,
            userName=VMwareAPISessionTest.USERNAME)
        self.assertFalse(vim_obj.Login.called)
        self.assertEqual(old_session_key, api_session._session_id)

    def test_invoke_api(self):
        api_session = self._create_api_session(True)
        response = mock.Mock()

        def api(*args, **kwargs):
            return response

        module = mock.Mock()
        module.api = api
        ret = api_session.invoke_api(module, 'api')
        self.assertEqual(response, ret)

    def test_logout_with_exception(self):
        session = mock.Mock()
        session.key = "12345"
        api_session = self._create_api_session(False)
        vim_obj = api_session.vim
        vim_obj.Login.return_value = session
        vim_obj.Logout.side_effect = exceptions.VimFaultException([], None)
        api_session._create_session()
        api_session.logout()
        self.assertEqual("12345", api_session._session_id)

    def test_logout_no_session(self):
        api_session = self._create_api_session(False)
        vim_obj = api_session.vim
        api_session.logout()
        self.assertEqual(0, vim_obj.Logout.call_count)

    def test_logout_calls_vim_logout(self):
        session = mock.Mock()
        session.key = "12345"
        api_session = self._create_api_session(False)
        vim_obj = api_session.vim
        vim_obj.Login.return_value = session
        vim_obj.Logout.return_value = None

        api_session._create_session()
        session_manager = vim_obj.service_content.sessionManager
        vim_obj.Login.assert_called_once_with(
            session_manager, userName=VMwareAPISessionTest.USERNAME,
            password=VMwareAPISessionTest.PASSWORD, locale='en')
        api_session.logout()
        vim_obj.Logout.assert_called_once_with(
            session_manager)
        self.assertIsNone(api_session._session_id)

    def test_invoke_api_with_expected_exception(self):
        api_session = self._create_api_session(True)
        api_session._create_session = mock.Mock()
        vim_obj = api_session.vim
        vim_obj.SessionIsActive.return_value = False
        ret = mock.Mock()
        responses = [exceptions.VimConnectionException(None), ret]

        def api(*args, **kwargs):
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        module = mock.Mock()
        module.api = api
        with mock.patch.object(greenthread, 'sleep'):
            self.assertEqual(ret, api_session.invoke_api(module, 'api'))
        api_session._create_session.assert_called_once_with()

    def test_invoke_api_not_recreate_session(self):
        api_session = self._create_api_session(True)
        api_session._create_session = mock.Mock()
        vim_obj = api_session.vim
        vim_obj.SessionIsActive.return_value = True
        ret = mock.Mock()
        responses = [exceptions.VimConnectionException(None), ret]

        def api(*args, **kwargs):
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        module = mock.Mock()
        module.api = api
        with mock.patch.object(greenthread, 'sleep'):
            self.assertEqual(ret, api_session.invoke_api(module, 'api'))
        self.assertFalse(api_session._create_session.called)

    def test_invoke_api_with_vim_fault_exception(self):
        api_session = self._create_api_session(True)

        def api(*args, **kwargs):
            raise exceptions.VimFaultException([], None)

        module = mock.Mock()
        module.api = api
        self.assertRaises(exceptions.VimFaultException,
                          api_session.invoke_api,
                          module,
                          'api')

    def test_invoke_api_with_vim_fault_exception_details(self):
        api_session = self._create_api_session(True)
        fault_string = 'Invalid property.'
        fault_list = [exceptions.INVALID_PROPERTY]
        details = {u'name': suds.sax.text.Text(u'фира')}

        module = mock.Mock()
        module.api.side_effect = exceptions.VimFaultException(fault_list,
                                                              fault_string,
                                                              details=details)
        e = self.assertRaises(exceptions.InvalidPropertyException,
                              api_session.invoke_api,
                              module,
                              'api')
        details_str = u"{'name': 'фира'}"
        expected_str = "%s\nFaults: %s\nDetails: %s" % (fault_string,
                                                        fault_list,
                                                        details_str)
        self.assertEqual(expected_str, str(e))
        self.assertEqual(details, e.details)

    def test_invoke_api_with_empty_response(self):
        api_session = self._create_api_session(True)
        vim_obj = api_session.vim
        vim_obj.SessionIsActive.return_value = True

        def api(*args, **kwargs):
            raise exceptions.VimFaultException(
                [exceptions.NOT_AUTHENTICATED], None)

        module = mock.Mock()
        module.api = api
        ret = api_session.invoke_api(module, 'api')
        self.assertEqual([], ret)
        vim_obj.SessionIsActive.assert_called_once_with(
            vim_obj.service_content.sessionManager,
            sessionID=api_session._session_id,
            userName=api_session._session_username)

    def test_invoke_api_with_stale_session(self):
        api_session = self._create_api_session(True)
        api_session._create_session = mock.Mock()
        vim_obj = api_session.vim
        vim_obj.SessionIsActive.return_value = False
        result = mock.Mock()
        responses = [exceptions.VimFaultException(
            [exceptions.NOT_AUTHENTICATED], None), result]

        def api(*args, **kwargs):
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        module = mock.Mock()
        module.api = api
        with mock.patch.object(greenthread, 'sleep'):
            ret = api_session.invoke_api(module, 'api')
        self.assertEqual(result, ret)
        vim_obj.SessionIsActive.assert_called_once_with(
            vim_obj.service_content.sessionManager,
            sessionID=api_session._session_id,
            userName=api_session._session_username)
        api_session._create_session.assert_called_once_with()

    def test_invoke_api_with_unknown_fault(self):
        api_session = self._create_api_session(True)
        fault_list = ['NotAFile']

        module = mock.Mock()
        module.api.side_effect = exceptions.VimFaultException(fault_list,
                                                              'Not a file.')
        ex = self.assertRaises(exceptions.VimFaultException,
                               api_session.invoke_api,
                               module,
                               'api')
        self.assertEqual(fault_list, ex.fault_list)

    @mock.patch.object(context, 'get_current')
    def test_wait_for_task(self, mock_curr_ctx):
        ctx = mock.Mock()
        mock_curr_ctx.return_value = ctx
        api_session = self._create_api_session(True)
        task_info_list = [('queued', 0), ('running', 40), ('success', 100)]
        task_info_list_size = len(task_info_list)

        def invoke_api_side_effect(module, method, *args, **kwargs):
            (state, progress) = task_info_list.pop(0)
            task_info = mock.Mock()
            task_info.progress = progress
            task_info.queueTime = datetime(2016, 12, 6, 15, 29, 43, 79060)
            task_info.completeTime = datetime(2016, 12, 6, 15, 29, 50, 79060)
            task_info.state = state
            return task_info

        api_session.invoke_api = mock.Mock(side_effect=invoke_api_side_effect)
        task = mock.Mock()
        with mock.patch.object(greenthread, 'sleep'):
            ret = api_session.wait_for_task(task)
            self.assertEqual('success', ret.state)
            self.assertEqual(100, ret.progress)
        api_session.invoke_api.assert_called_with(vim_util,
                                                  'get_object_property',
                                                  api_session.vim, task,
                                                  'info',
                                                  skip_op_id=True)
        self.assertEqual(task_info_list_size,
                         api_session.invoke_api.call_count)
        mock_curr_ctx.assert_called_once()
        self.assertEqual(3, ctx.update_store.call_count)

    @mock.patch.object(context, 'get_current', return_value=None)
    def test_wait_for_task_no_ctx(self, mock_curr_ctx):
        api_session = self._create_api_session(True)
        task_info_list = [('queued', 0), ('running', 40), ('success', 100)]
        task_info_list_size = len(task_info_list)

        def invoke_api_side_effect(module, method, *args, **kwargs):
            (state, progress) = task_info_list.pop(0)
            task_info = mock.Mock()
            task_info.progress = progress
            task_info.queueTime = datetime(2016, 12, 6, 15, 29, 43, 79060)
            task_info.completeTime = datetime(2016, 12, 6, 15, 29, 50, 79060)
            task_info.state = state
            return task_info

        api_session.invoke_api = mock.Mock(side_effect=invoke_api_side_effect)
        task = mock.Mock()
        with mock.patch.object(greenthread, 'sleep'):
            ret = api_session.wait_for_task(task)
            self.assertEqual('success', ret.state)
            self.assertEqual(100, ret.progress)
        api_session.invoke_api.assert_called_with(vim_util,
                                                  'get_object_property',
                                                  api_session.vim, task,
                                                  'info',
                                                  skip_op_id=True)
        self.assertEqual(task_info_list_size,
                         api_session.invoke_api.call_count)
        mock_curr_ctx.assert_called_once()

    @mock.patch.object(context, 'get_current')
    def test_wait_for_task_with_error_state(self, mock_curr_ctx):
        api_session = self._create_api_session(True)
        task_info_list = [('queued', 0), ('running', 40), ('error', -1)]
        task_info_list_size = len(task_info_list)

        def invoke_api_side_effect(module, method, *args, **kwargs):
            (state, progress) = task_info_list.pop(0)
            task_info = mock.Mock()
            task_info.progress = progress
            task_info.state = state
            return task_info

        api_session.invoke_api = mock.Mock(side_effect=invoke_api_side_effect)
        task = mock.Mock()
        with mock.patch.object(greenthread, 'sleep'):
            self.assertRaises(exceptions.VimFaultException,
                              api_session.wait_for_task,
                              task)
        api_session.invoke_api.assert_called_with(vim_util,
                                                  'get_object_property',
                                                  api_session.vim, task,
                                                  'info',
                                                  skip_op_id=True)
        self.assertEqual(task_info_list_size,
                         api_session.invoke_api.call_count)
        mock_curr_ctx.assert_called_once()

    @mock.patch.object(context, 'get_current')
    def test_wait_for_task_with_invoke_api_exception(self, mock_curr_ctx):
        api_session = self._create_api_session(True)
        api_session.invoke_api = mock.Mock(
            side_effect=exceptions.VimException(None))
        task = mock.Mock()
        with mock.patch.object(greenthread, 'sleep'):
            self.assertRaises(exceptions.VimException,
                              api_session.wait_for_task,
                              task)
        api_session.invoke_api.assert_called_once_with(vim_util,
                                                       'get_object_property',
                                                       api_session.vim, task,
                                                       'info',
                                                       skip_op_id=True)
        mock_curr_ctx.assert_called_once()

    def test_wait_for_lease_ready(self):
        api_session = self._create_api_session(True)
        lease_states = ['initializing', 'ready']
        num_states = len(lease_states)

        def invoke_api_side_effect(module, method, *args, **kwargs):
            return lease_states.pop(0)

        api_session.invoke_api = mock.Mock(side_effect=invoke_api_side_effect)
        lease = mock.Mock()
        with mock.patch.object(greenthread, 'sleep'):
            api_session.wait_for_lease_ready(lease)
        api_session.invoke_api.assert_called_with(vim_util,
                                                  'get_object_property',
                                                  api_session.vim, lease,
                                                  'state',
                                                  skip_op_id=True)
        self.assertEqual(num_states, api_session.invoke_api.call_count)

    def test_wait_for_lease_ready_with_error_state(self):
        api_session = self._create_api_session(True)
        responses = ['initializing', 'error', 'error_msg']

        def invoke_api_side_effect(module, method, *args, **kwargs):
            return responses.pop(0)

        api_session.invoke_api = mock.Mock(side_effect=invoke_api_side_effect)
        lease = mock.Mock()
        with mock.patch.object(greenthread, 'sleep'):
            self.assertRaises(exceptions.VimException,
                              api_session.wait_for_lease_ready,
                              lease)
        exp_calls = [mock.call(vim_util, 'get_object_property',
                               api_session.vim, lease, 'state',
                               skip_op_id=True)] * 2
        exp_calls.append(mock.call(vim_util, 'get_object_property',
                                   api_session.vim, lease, 'error'))
        self.assertEqual(exp_calls, api_session.invoke_api.call_args_list)

    def test_wait_for_lease_ready_with_unknown_state(self):
        api_session = self._create_api_session(True)

        def invoke_api_side_effect(module, method, *args, **kwargs):
            return 'unknown'

        api_session.invoke_api = mock.Mock(side_effect=invoke_api_side_effect)
        lease = mock.Mock()
        self.assertRaises(exceptions.VimException,
                          api_session.wait_for_lease_ready,
                          lease)
        api_session.invoke_api.assert_called_once_with(vim_util,
                                                       'get_object_property',
                                                       api_session.vim,
                                                       lease, 'state',
                                                       skip_op_id=True)

    def test_wait_for_lease_ready_with_invoke_api_exception(self):
        api_session = self._create_api_session(True)
        api_session.invoke_api = mock.Mock(
            side_effect=exceptions.VimException(None))
        lease = mock.Mock()
        self.assertRaises(exceptions.VimException,
                          api_session.wait_for_lease_ready,
                          lease)
        api_session.invoke_api.assert_called_once_with(
            vim_util, 'get_object_property', api_session.vim, lease,
            'state', skip_op_id=True)

    def _poll_task_well_known_exceptions(self, fault,
                                         expected_exception):
        api_session = self._create_api_session(False)

        def fake_invoke_api(self, module, method, *args, **kwargs):
            task_info = mock.Mock()
            task_info.progress = -1
            task_info.state = 'error'
            error = mock.Mock()
            error.localizedMessage = "Error message"
            error_fault = mock.Mock()
            error_fault.__class__.__name__ = fault
            error.fault = error_fault
            task_info.error = error
            return task_info

        with (
            mock.patch.object(api_session, 'invoke_api', fake_invoke_api)
        ):
            fake_task = mock.Mock()
            fake_task.value = 'task-1'
            ctx = mock.Mock()
            self.assertRaises(expected_exception,
                              api_session._poll_task,
                              fake_task,
                              ctx)

    def test_poll_task_well_known_exceptions(self):
        for k, v in exceptions._fault_classes_registry.items():
            self._poll_task_well_known_exceptions(k, v)

    def test_poll_task_unknown_exception(self):
        _unknown_exceptions = {
            'NotAFile': exceptions.VimFaultException,
            'RuntimeFault': exceptions.VimFaultException
        }

        for k, v in _unknown_exceptions.items():
            self._poll_task_well_known_exceptions(k, v)

    def test_update_pbm_wsdl_loc(self):
        session = mock.Mock()
        session.key = "12345"
        api_session = self._create_api_session(False)
        self.assertIsNone(api_session._pbm_wsdl_loc)
        api_session.pbm_wsdl_loc_set('fake_wsdl')
        self.assertEqual('fake_wsdl', api_session._pbm_wsdl_loc)
