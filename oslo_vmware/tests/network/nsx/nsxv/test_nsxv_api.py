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

import json

import mock

from oslo_vmware.network.nsx.nsxv.api import api
from oslo_vmware.network.nsx.nsxv.api import api_helper
from oslo_vmware.network.nsx.nsxv.common import exceptions
from tests import base


class NsxvApiTestCase(base.TestCase):

    def setUp(self):
        super(NsxvApiTestCase, self).setUp()
        self.nsxv_api = api.NsxvApi('http://10.0.0.1', 'testuser', 'testpwd',
                                    retries=2)

    def _test_helper(self, nsxv_api, http_method, uri, data, h, v,
                     retval, decode, headers, *args):
        with mock.patch.object(api_helper.NsxvApiHelper, 'request',
                               return_value=(h, v)) as mock_request:

            h1, v1 = nsxv_api(*args)
            mock_request.assert_has_calls([
                mock.call().request(http_method, uri,
                                    data, headers, decode)])

            self.assertEqual(h, h1)
            if retval is not None:
                self.assertEqual(retval, v1)
            else:
                self.assertEqual(v, v1)

    def test_deploy_edge(self):
        h = {'status': '200', 'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = [{'test1': 'test123'}]
        self._test_helper(
            self.nsxv_api.deploy_edge,
            'POST',
            '/api/4.0/edges?async=true',
            json.loads(v),
            h, v, None, True, None, *args)

    def test_update_edge(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.update_edge,
            'PUT',
            '/api/4.0/edges/edge-x?async=true',
            json.loads(v),
            h, v, None, True, None, *args)

    def test_get_edge_id(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['jobdata-15779']
        self._test_helper(
            self.nsxv_api.get_edge_id,
            'GET',
            '/api/4.0/edges/jobs/jobdata-15779',
            None, h, v, json.loads(v), True, None, *args)

    def test_get_edge_jobs(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x']
        self._test_helper(
            self.nsxv_api.get_edge_jobs,
            'GET',
            '/api/4.0/edges/edge-x/jobs',
            None, h, v, json.loads(v), True, None, *args)

    def test_get_edge_deploy_status(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x']
        self._test_helper(
            self.nsxv_api.get_edge_deploy_status,
            'GET',
            '/api/4.0/edges/edge-x/status?getlatest=false',
            None, h, v, json.loads(v), True, None, *args)

    def test_delete_edge(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x']
        self._test_helper(
            self.nsxv_api.delete_edge,
            'DELETE',
            '/api/4.0/edges/edge-x',
            None, h, v, json.loads(v), True, None, *args)

    def test_add_vdr_internal_interface(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 1]
        self._test_helper(
            self.nsxv_api.add_vdr_internal_interface,
            'POST',
            '/api/4.0/edges/edge-x/interfaces?action=patch&async=true',
            1, h, v, json.loads(v), True, None, *args)

    def test_update_vdr_internal_interface(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 1, json.loads(v)]
        self._test_helper(
            self.nsxv_api.update_vdr_internal_interface,
            'PUT',
            '/api/4.0/edges/edge-x/interfaces/1?async=true',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_delete_vdr_internal_interface(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 1]
        self._test_helper(
            self.nsxv_api.delete_vdr_internal_interface,
            'DELETE',
            '/api/4.0/edges/edge-x/interfaces/1?async=true',
            None, h, v, json.loads(v), True, None, *args)

    def test_get_interfaces(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x']
        self._test_helper(
            self.nsxv_api.get_interfaces,
            'GET',
            '/api/4.0/edges/edge-x/vnics',
            None, h, v, json.loads(v), True, None, *args)

    def test_update_interface(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"index": 1, "test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.update_interface,
            'PUT',
            '/api/4.0/edges/edge-x/vnics/1?async=true',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_delete_interface(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"index": 1, "test1": "test123"}'

        args = ['edge-x', 1]
        self._test_helper(
            self.nsxv_api.delete_interface,
            'DELETE',
            '/api/4.0/edges/edge-x/vnics/1?async=true',
            None, h, v, json.loads(v), True, None, *args)

    def test_get_nat_config(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x']
        self._test_helper(
            self.nsxv_api.get_nat_config,
            'GET',
            '/api/4.0/edges/edge-x/nat/config',
            None, h, v, json.loads(v), True, None, *args)

    def test_update_nat_config(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.update_nat_config,
            'PUT',
            '/api/4.0/edges/edge-x/nat/config?async=true',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_delete_nat_rule(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 1]
        self._test_helper(
            self.nsxv_api.delete_nat_rule,
            'DELETE',
            '/api/4.0/edges/edge-x/nat/config/rules/1',
            None, h, v, json.loads(v), True, None, *args)

    def test_get_edge_status(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x']
        self._test_helper(
            self.nsxv_api.get_edge_status,
            'GET',
            '/api/4.0/edges/edge-x/status?getlatest=false',
            None, h, v, json.loads(v), True, None, *args)

    def test_get_edges(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = []
        self._test_helper(
            self.nsxv_api.get_edges,
            'GET',
            '/api/4.0/edges',
            None, h, v, json.loads(v), True, None, *args)

    def test_get_edge_interfaces(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x']
        self._test_helper(
            self.nsxv_api.get_edge_interfaces,
            'GET',
            '/api/4.0/edges/edge-x/interfaces',
            None, h, v, json.loads(v), True, None, *args)

    def test_update_routes(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.update_routes,
            'PUT',
            '/api/4.0/edges/edge-x/routing/config/static?async=true',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_create_lswitch(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = [json.loads(v)]
        self._test_helper(
            self.nsxv_api.create_lswitch,
            'POST',
            '/api/ws.v1/lswitch',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_delete_lswitch(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = [123]
        self._test_helper(
            self.nsxv_api.delete_lswitch,
            'DELETE',
            '/api/ws.v1/lswitch/123',
            None, h, v, json.loads(v), True, None, *args)

    def test_get_loadbalancer_config(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x']
        self._test_helper(
            self.nsxv_api.get_loadbalancer_config,
            'GET',
            '/api/4.0/edges/edge-x/loadbalancer/config',
            None, h, v, json.loads(v), True, None, *args)

    def test_enable_service_loadbalancer(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.enable_service_loadbalancer,
            'PUT',
            '/api/4.0/edges/edge-x/loadbalancer/config',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_update_firewall(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.update_firewall,
            'PUT',
            '/api/4.0/edges/edge-x/firewall/config?async=true',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_delete_firewall(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x']
        self._test_helper(
            self.nsxv_api.delete_firewall,
            'DELETE',
            '/api/4.0/edges/edge-x/firewall/config?async=true',
            None, h, v, json.loads(v), True, None, *args)

    def test_update_firewall_rule(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', '123', json.loads(v)]
        self._test_helper(
            self.nsxv_api.update_firewall_rule,
            'PUT',
            '/api/4.0/edges/edge-x/firewall/config/rules/123',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_delete_firewall_rule(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', '123']
        self._test_helper(
            self.nsxv_api.delete_firewall_rule,
            'DELETE',
            '/api/4.0/edges/edge-x/firewall/config/rules/123',
            None, h, v, json.loads(v), True, None, *args)

    def test_add_firewall_rule_above(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', '123', json.loads(v)]
        self._test_helper(
            self.nsxv_api.add_firewall_rule_above,
            'POST',
            '/api/4.0/edges/edge-x/firewall/config/rules?aboveRuleId=123',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_add_firewall_rule(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.add_firewall_rule,
            'POST',
            '/api/4.0/edges/edge-x/firewall/config/rules',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_get_firewall(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x']
        self._test_helper(
            self.nsxv_api.get_firewall,
            'GET',
            '/api/4.0/edges/edge-x/firewall/config',
            None, h, v, json.loads(v), True, None, *args)

    def test_get_firewall_rule(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 123]
        self._test_helper(
            self.nsxv_api.get_firewall_rule,
            'GET',
            '/api/4.0/edges/edge-x/firewall/config/rules/123',
            None, h, v, json.loads(v), True, None, *args)

    def test_create_vip(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.create_vip,
            'POST',
            '/api/4.0/edges/edge-x/loadbalancer/config/virtualservers',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_get_vip(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 123]
        self._test_helper(
            self.nsxv_api.get_vip,
            'GET',
            '/api/4.0/edges/edge-x/loadbalancer/config/virtualservers/123',
            None, h, v, json.loads(v), True, None, *args)

    def test_update_vip(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 123, json.loads(v)]
        self._test_helper(
            self.nsxv_api.update_vip,
            'PUT',
            '/api/4.0/edges/edge-x/loadbalancer/config/virtualservers/123',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_delete_vip(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 123]
        self._test_helper(
            self.nsxv_api.delete_vip,
            'DELETE',
            '/api/4.0/edges/edge-x/loadbalancer/config/virtualservers/123',
            None, h, v, json.loads(v), True, None, *args)

    def test_create_pool(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.create_pool,
            'POST',
            '/api/4.0/edges/edge-x/loadbalancer/config/pools',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_get_pool(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 123]
        self._test_helper(
            self.nsxv_api.get_pool,
            'GET',
            '/api/4.0/edges/edge-x/loadbalancer/config/pools/123',
            None, h, v, json.loads(v), True, None, *args)

    def test_update_pool(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 123, json.loads(v)]
        self._test_helper(
            self.nsxv_api.update_pool,
            'PUT',
            '/api/4.0/edges/edge-x/loadbalancer/config/pools/123',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_delete_pool(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 123]
        self._test_helper(
            self.nsxv_api.delete_pool,
            'DELETE',
            '/api/4.0/edges/edge-x/loadbalancer/config/pools/123',
            None, h, v, json.loads(v), True, None, *args)

    def test_create_health_monitor(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.create_health_monitor,
            'POST',
            '/api/4.0/edges/edge-x/loadbalancer/config/monitors',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_get_health_monitor(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 123]
        self._test_helper(
            self.nsxv_api.get_health_monitor,
            'GET',
            '/api/4.0/edges/edge-x/loadbalancer/config/monitors/123',
            None, h, v, json.loads(v), True, None, *args)

    def test_update_health_monitor(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 123, json.loads(v)]
        self._test_helper(
            self.nsxv_api.update_health_monitor,
            'PUT',
            '/api/4.0/edges/edge-x/loadbalancer/config/monitors/123',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_delete_health_monitor(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 123]
        self._test_helper(
            self.nsxv_api.delete_health_monitor,
            'DELETE',
            '/api/4.0/edges/edge-x/loadbalancer/config/monitors/123',
            None, h, v, json.loads(v), True, None, *args)

    def test_create_app_profile(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.create_app_profile,
            'POST',
            '/api/4.0/edges/edge-x/loadbalancer/config/applicationprofiles',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_update_app_profile(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 1, json.loads(v)]
        self._test_helper(
            self.nsxv_api.update_app_profile,
            'PUT',
            '/api/4.0/edges/edge-x/loadbalancer/config/applicationprofiles/1',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_delete_app_profile(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 1]
        self._test_helper(
            self.nsxv_api.delete_app_profile,
            'DELETE',
            '/api/4.0/edges/edge-x/loadbalancer/config/applicationprofiles/1',
            None, h, v, json.loads(v), True, None, *args)

    def test_create_app_rule(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.create_app_rule,
            'POST',
            '/api/4.0/edges/edge-x/loadbalancer/config/applicationrules',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_update_app_rule(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 123, json.loads(v)]
        self._test_helper(
            self.nsxv_api.update_app_rule,
            'PUT',
            '/api/4.0/edges/edge-x/loadbalancer/config/applicationrules/123',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_delete_app_rule(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 123]
        self._test_helper(
            self.nsxv_api.delete_app_rule,
            'DELETE',
            '/api/4.0/edges/edge-x/loadbalancer/config/applicationrules/123',
            None, h, v, json.loads(v), True, None, *args)

    def test_update_ipsec_config(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.update_ipsec_config,
            'PUT',
            '/api/4.0/edges/edge-x/ipsec/config',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_delete_ipsec_config(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x']
        self._test_helper(
            self.nsxv_api.delete_ipsec_config,
            'DELETE',
            '/api/4.0/edges/edge-x/ipsec/config',
            None, h, v, json.loads(v), True, None, *args)

    def test_get_ipsec_config(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x']
        self._test_helper(
            self.nsxv_api.get_ipsec_config,
            'GET',
            '/api/4.0/edges/edge-x/ipsec/config',
            None, h, v, json.loads(v), True, None, *args)

    def test_create_virtual_wire(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/xml'}
        v = '<test1>test123</test1>'

        args = ['vdn-scope-x', {'test1': 'test123'}]
        self._test_helper(
            self.nsxv_api.create_virtual_wire,
            'POST',
            '/api/2.0/vdn/scopes/vdn-scope-x/virtualwires',
            {'test1': 'test123'}, h, v, None, True, None, *args)

    def test_delete_virtual_wire(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/xml'}

        args = [123]
        self._test_helper(
            self.nsxv_api.delete_virtual_wire,
            'DELETE',
            '/api/2.0/vdn/virtualwires/123',
            None, h, '', {}, True, None, *args)

    def test_create_port_group(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/xml'}
        v = '<test1>test123</test1>'

        args = [123, {'test1': 'test123'}]
        self._test_helper(
            self.nsxv_api.create_port_group,
            'POST',
            '/api/2.0/xvs/switches/123/networks',
            {'test1': 'test123'}, h, v, None, True, None, *args)

    def test_delete_port_group(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}

        args = [123, 456]
        self._test_helper(
            self.nsxv_api.delete_port_group,
            'DELETE',
            '/api/2.0/xvs/switches/123/networks/456',
            None, h, '', {}, True, None, *args)

    def test_query_interface(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', 123]
        self._test_helper(
            self.nsxv_api.query_interface,
            'GET',
            '/api/4.0/edges/edge-x/vnics/123',
            None, h, v, json.loads(v), True, None, *args)

    def test_reconfigure_dhcp_service(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.reconfigure_dhcp_service,
            'PUT',
            '/api/4.0/edges/edge-x/dhcp/config?async=true',
            json.loads(v), h, v, json.loads(v), True, None, *args)

    def test_query_dhcp_configuration(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x']
        self._test_helper(
            self.nsxv_api.query_dhcp_configuration,
            'GET',
            '/api/4.0/edges/edge-x/dhcp/config',
            None, h, v, json.loads(v), True, None, *args)

    def test_create_dhcp_binding(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}
        v = '{"test1": "test123"}'

        args = ['edge-x', json.loads(v)]
        self._test_helper(
            self.nsxv_api.create_dhcp_binding,
            'POST',
            '/api/4.0/edges/edge-x/dhcp/config/bindings?async=true',
            json.loads(v), h, None, None, True, None, *args)

    def test_delete_dhcp_binding(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}

        args = ['edge-x', 456]
        self._test_helper(
            self.nsxv_api.delete_dhcp_binding,
            'DELETE',
            '/api/4.0/edges/edge-x/dhcp/config/bindings/456?async=true',
            None, h, '', {}, True, None, *args)

    def test_create_security_group(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/xml'}
        v = '<test1>test123</test1>'

        args = [{'test1': 'test123'}]
        self._test_helper(
            self.nsxv_api.create_security_group,
            'POST',
            '/api/2.0/services/securitygroup/globalroot-0',
            {'test1': 'test123'}, h, v, None, True, None, *args)

    def test_delete_security_group(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/json'}

        args = [123]
        self._test_helper(
            self.nsxv_api.delete_security_group,
            'DELETE',
            '/api/2.0/services/securitygroup/123?force=true',
            None, h, '', {}, True, None, *args)

    def test_create_section_ip(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/xml'}
        v = '<test1>test123</test1>'

        args = ['ip', {'test1': 'test123'}]
        self._test_helper(
            self.nsxv_api.create_section,
            'POST',
            '/api/4.0/firewall/globalroot-0/'
            'config/layer3sections?autoSaveDraft=false',
            {'test1': 'test123'}, h, v, None, False, None, *args)

    def test_create_section_eth(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/xml'}
        v = '<test1>test123</test1>'

        args = ['eth', {'test1': 'test123'}]
        self._test_helper(
            self.nsxv_api.create_section,
            'POST',
            '/api/4.0/firewall/globalroot-0/'
            'config/layer2sections?autoSaveDraft=false',
            {'test1': 'test123'}, h, v, None, False, None, *args)

    def test_update_section(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/xml'}
        v = '<test1>test123</test1>'

        args = ['/api/4.0/firewall/globalroot-0/config/layer3sections/123',
                {'test1': 'test123'}, {'etag': '1234'}]
        self._test_helper(
            self.nsxv_api.update_section,
            'PUT',
            '/api/4.0/firewall/globalroot-0/config/'
            'layer3sections/123?autoSaveDraft=false',
            {'test1': 'test123'}, h, v, None, False, {'If-Match': '1234'},
            *args)

    def test_delete_section(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/xml'}

        args = ['/api/4.0/firewall/globalroot-0/config/layer3sections/123s']
        self._test_helper(
            self.nsxv_api.delete_section,
            'DELETE',
            '/api/4.0/firewall/globalroot-0/config/'
            'layer3sections/123s?autoSaveDraft=false',
            None, h, '', {}, True, None, *args)

    def test_get_section(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/xml'}
        v = '<test1>test123</test1>'

        args = ['/api/4.0/firewall/globalroot-0/config/layer3sections/123']
        self._test_helper(
            self.nsxv_api.get_section,
            'GET',
            '/api/4.0/firewall/globalroot-0/config/layer3sections/123',
            None, h, v, v, True, None, *args)

    def test_get_section_id(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/xml'}
        v = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<sections>'
             '<section id="4" name="test4"></section>'
             '<section id="5" name="test5"></section>'
             '<section id="6" name="test6"></section>'
             '</sections>')

        with mock.patch.object(api_helper.NsxvApiHelper, 'request',
                               return_value=(h, v)) as mock_request:

            ret = self.nsxv_api.get_section_id('test5')
            mock_request.assert_has_calls([
                mock.call().request(
                    'GET',
                    '/api/4.0/firewall/globalroot-0/config',
                    None, None, True)])

            self.assertEqual(ret, '5')

        with mock.patch.object(api_helper.NsxvApiHelper, 'request',
                               return_value=(h, v)) as mock_request:

            ret = self.nsxv_api.get_section_id('test4')
            mock_request.assert_has_calls([
                mock.call().request(
                    'GET',
                    '/api/4.0/firewall/globalroot-0/config',
                    None, None, True)])

            self.assertEqual(ret, '4')

    def _fake_request_for_test_update_section_by_id(
            self, method, uri, params=None, headers=None, encodeparams=True):
        # If this is the call from _get_section_header() act accordingly
        v = '{"test1": "test123"}'

        if(method == 'GET'
           and uri == ('/api/4.0/firewall/globalroot-0/config/'
                       'layer3sections/test4')
           and params is None and headers is None and encodeparams):
            return {'status': '200',
                    'connection': 'keep-alive',
                    'content-type': 'application/json',
                    'etag': '1234'}, ''
        # That is the call from update_section_by_id()
        elif(method == 'PUT'
             and uri == ('/api/4.0/firewall/globalroot-0/config/'
                         'layer3sections/test4?autoSaveDraft=false')
             and headers == {'If-Match': '1234'}
             and params == json.loads(v)):
            return {'status': '200',
                    'connection': 'keep-alive',
                    'content-type': 'application/json'}, ''
        else:
            self.fail()

    def test_update_section_by_id(self):
        v = '{"test1": "test123"}'

        with mock.patch.object(
                api_helper.NsxvApiHelper, 'request',
                self._fake_request_for_test_update_section_by_id):
            ret = self.nsxv_api.update_section_by_id(
                'test4', 'ip', json.loads(v))
            self.assertEqual(ret, None)

    def _fake_request_for_test_remove_rule_from_section(
            self, method, uri, params=None, headers=None, encodeparams=True):
        # If this is the call from _get_section_header() act accordingly

        if(method == 'GET'
           and uri == ('/api/4.0/firewall/globalroot-0/config/'
                       'layer3sections/123')
           and params is None and headers is None and encodeparams):
            return {'status': '200',
                    'connection': 'keep-alive',
                    'content-type': 'application/json',
                    'etag': '1234'}, ''
        # That is the call from remove_rule_from_section()
        elif(method == 'DELETE'
             and uri == ('/api/4.0/firewall/globalroot-0/config/layer3sections'
                         '/123/rules/1234?autoSaveDraft=false')
             and headers == {'If-Match': '1234'}
             and params is None):
            return {'status': '200',
                    'connection': 'keep-alive',
                    'content-type': 'application/json'}, ''
        else:
            self.fail()

    def test_remove_rule_from_section(self):
        with mock.patch.object(
                api_helper.NsxvApiHelper, 'request',
                self._fake_request_for_test_remove_rule_from_section):
            h, v = self.nsxv_api.remove_rule_from_section(
                '/api/4.0/firewall/globalroot-0/config/layer3sections/123',
                '1234')
            self.assertEqual(h, {'status': '200',
                                 'connection': 'keep-alive',
                                 'content-type': 'application/json'})
            self.assertEqual(v, {})

    def test_add_member_to_security_group(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/xml'}
        v = '<test1>test123</test1>'

        args = ['123', '456']
        self._test_helper(
            self.nsxv_api.add_member_to_security_group,
            'PUT',
            '/api/2.0/services/securitygroup/123/members/456',
            None, h, v, None, True, None, *args)

    def test_remove_member_from_security_group(self):
        h = {'status': '200',
             'connection': 'keep-alive',
             'content-type': 'application/xml'}

        args = ['123', '456']
        self._test_helper(
            self.nsxv_api.remove_member_from_security_group,
            'DELETE',
            '/api/2.0/services/securitygroup/123/members/456',
            None, h, None, None, True, None, *args)


class NsxvApiRetryTestCase(base.TestCase):

    def setUp(self):
        super(NsxvApiRetryTestCase, self).setUp()
        self.nsxv_api = api.NsxvApi('http://10.0.0.1', 'testuser', 'testpwd',
                                    retries=2)

    def _fake_request_1_retry(
            self, method, uri, params=None, headers=None, encodeparams=True):
        """Throw exception on 1st call, succeed on second attempt."""
        if(method == 'POST'
           and uri == '/api/4.0/edges?async=true'
           and params == {'test1': 'test123'}
           and headers is None and encodeparams):
            if self._ctr == 1:
                self._ctr += 1
                raise exceptions.ServiceConflict
            elif self._ctr == 2:
                return {'status': '200',
                        'connection': 'keep-alive',
                        'content-type': 'application/json'}, ''
        else:
            self.fail()

    def test_deploy_edge_1_retry(self):
        self._ctr = 1

        with mock.patch.object(
                api_helper.NsxvApiHelper, 'request',
                self._fake_request_1_retry):
            h, v = self.nsxv_api.deploy_edge({'test1': 'test123'})
            self.assertEqual(h, {'status': '200',
                                 'connection': 'keep-alive',
                                 'content-type': 'application/json'})
            self.assertEqual(v, {})

    def _fake_request_2_retries(
            self, method, uri, params=None, headers=None, encodeparams=True):
        """Always fail, just valiadate header params."""
        if(method == 'POST'
           and uri == '/api/4.0/edges?async=true'
           and params == {'test1': 'test123'}
           and headers is None and encodeparams):
            raise exceptions.ServiceConflict
        else:
            self.fail()

    def test_deploy_edge_2_retries_fail(self):
        self._ctr = 1

        with mock.patch.object(
                api_helper.NsxvApiHelper, 'request',
                self._fake_request_2_retries):
            self.assertRaises(exceptions.ServiceConflict,
                              self.nsxv_api.deploy_edge, {'test1': 'test123'})


class NsxvConfigValidationTestCase(base.TestCase):

    SWITCHES_XML = (
        '<?xml version="1.0" encoding="UTF-8"?><vdsContexts><vdsContext>'
        '<switch><objectId>dvs-15</objectId></switch></vdsContext>'
        '</vdsContexts>')

    SCOPINGOBJECTS_XML = (
        '<?xml version="1.0" encoding="UTF-8"?><scopingObjects><object>'
        '<objectId>datacenter-2</objectId><objectTypeName>Datacenter'
        '</objectTypeName></object><object><objectId>network-23</objectId>'
        '<objectTypeName>Network</objectTypeName></object><object><objectId>'
        'network-12</objectId><objectTypeName>Network</objectTypeName>'
        '</object></scopingObjects>')

    VDNSCOPES_XML = (
        '<?xml version="1.0" encoding="UTF-8"?><vdnScopes><vdnScope>'
        '<objectId>vdnscope-1</objectId></vdnScope></vdnScopes>')

    @mock.patch.object(api_helper, 'NsxvApiHelper')
    def setUp(self, _mock_client):
        super(NsxvConfigValidationTestCase, self).setUp()
        self._nsxv_api = api.NsxvApi(None, None, None)

    def test_validate_dvs_success(self):
        h = None
        v = self.SWITCHES_XML

        with mock.patch.object(self._nsxv_api, 'do_request',
                               return_value=(h, v)):
            self.assertTrue(self._nsxv_api.validate_dvs('dvs-15'))

    def test_validate_dvs_fail(self):
        h = None
        v = self.SWITCHES_XML

        with mock.patch.object(self._nsxv_api, 'do_request',
                               return_value=(h, v)):
            self.assertFalse(self._nsxv_api.validate_dvs('dvs-14'))

    def test_validate_datacenter_moid_success(self):
        h = None
        v = self.SCOPINGOBJECTS_XML

        with mock.patch.object(self._nsxv_api, 'do_request',
                               return_value=(h, v)):
            self.assertTrue(self._nsxv_api.validate_datacenter_moid(
                'datacenter-2'))

    def test_validate_datacenter_moid_fail(self):
        h = None
        v = self.SCOPINGOBJECTS_XML

        with mock.patch.object(self._nsxv_api, 'do_request',
                               return_value=(h, v)):
            self.assertFalse(self._nsxv_api.validate_datacenter_moid(
                'network-23'))

    def test_validate_network_success(self):
        h = None
        v = self.SCOPINGOBJECTS_XML

        with mock.patch.object(self._nsxv_api, 'do_request',
                               return_value=(h, v)):
            self.assertTrue(self._nsxv_api.validate_network(
                'network-23'))

    def test_validate_network_fail(self):
        h = None
        v = self.SCOPINGOBJECTS_XML

        with mock.patch.object(self._nsxv_api, 'do_request',
                               return_value=(h, v)):
            self.assertFalse(self._nsxv_api.validate_network(
                'network-24'))

    def test_validate_vdn_scope_success(self):
        h = None
        v = self.VDNSCOPES_XML

        with mock.patch.object(self._nsxv_api, 'do_request',
                               return_value=(h, v)):
            self.assertTrue(self._nsxv_api.validate_vdn_scope(
                'vdnscope-1'))

    def test_validate_vdn_scope_fail(self):
        h = None
        v = self.VDNSCOPES_XML

        with mock.patch.object(self._nsxv_api, 'do_request',
                               return_value=(h, v)):
            self.assertFalse(self._nsxv_api.validate_vdn_scope(
                'vdnscope-2'))
