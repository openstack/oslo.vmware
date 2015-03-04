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

from oslo_vmware.network.nsx.nsxv.api import api as nsxv_api
from oslo_vmware.network.nsx.nsxv.objects import loadbalancer as nsxv_lb
from tests import base


class NsxvLoadbalancerTestCase(base.TestCase):

    EDGE_OBJ_JSON = (
        '{"accelerationEnabled":false,"applicationProfile":[{'
        '"applicationProfileId":"applicationProfile-1","insertXForwardedFor":'
        'false,"name":"MDSrvProxy","persistence":{"cookieMode":"insert",'
        '"cookieName":"JSESSIONID","expire":"30","method":"cookie"},'
        '"serverSslEnabled":false,"sslPassthrough":false,"template":"HTTP"}],'
        '"applicationRule":[],"enableServiceInsertion":false,"enabled":true,'
        '"featureType":"loadbalancer_4.0","logging":{"enable":false,'
        '"logLevel":"info"},"monitor":[{"interval":10,"maxRetries":3,"method":'
        '"GET","monitorId":"monitor-1","name":"MDSrvMon","timeout":15,"type":'
        '"http","url":"/"}],"pool":[{"algorithm":"round-robin",'
        '"applicationRuleId":[],"member":[{"condition":"enabled","ipAddress":'
        '"192.168.0.39","maxConn":0,"memberId":"member-1","minConn":0,'
        '"monitorPort":8775,"name":"Member-1","port":8775,"weight":1}],'
        '"monitorId":["monitor-1"],"name":"MDSrvPool","poolId":"pool-1",'
        '"transparent":false}],"version":6,"virtualServer":[{'
        '"accelerationEnabled":false,"applicationProfileId":'
        '"applicationProfile-1","applicationRuleId":[],"connectionLimit":0,'
        '"defaultPoolId":"pool-1","enableServiceInsertion":false,'
        '"enabled":true,"ipAddress":"169.254.0.3","name":"MdSrv",'
        '"port":"8775","protocol":"http","virtualServerId":'
        '"virtualServer-1"}]}')

    OUT_OBJ_JSON = (
        '{"accelerationEnabled": false, "applicationProfile": [{'
        '"applicationProfileId": "applicationProfile-1", '
        '"insertXForwardedFor": false, "name": "MDSrvProxy", "persistence": '
        '{"expire": "30", "method": "cookie"}, "serverSslEnabled": false, '
        '"sslPassthrough": false, "template": "HTTP"}],'
        ' "enableServiceInsertion": false, "enabled": true, "featureType": '
        '"loadbalancer_4.0", "monitor": [{"interval": 10, "maxRetries": 3, '
        '"method": "GET", "monitorId": "monitor-1", "name": "MDSrvMon", '
        '"timeout": 15, "type": "http", "url": "/"}], "pool": [{"algorithm":'
        ' "round-robin", "member": [{"condition": "enabled", "ipAddress": '
        '"192.168.0.39", "maxConn": 0, "memberId": "member-1", "minConn": 0, '
        '"monitorPort": 8775, "name": "Member-1", "port": 8775, "weight": 1}],'
        ' "monitorId": ["monitor-1"], "name": "MDSrvPool", "poolId": "pool-1",'
        ' "transparent": false}], "virtualServer": [{"accelerationEnabled": '
        'false, "applicationProfileId": "applicationProfile-1", '
        '"connectionLimit": 0, "defaultPoolId": "pool-1", '
        '"enableServiceInsertion": false, "enabled": true, "ipAddress": '
        '"169.254.0.3", "name": "MdSrv", "port": "8775", "protocol": '
        '"http", "virtualServerId": "virtualServer-1"}]}')

    LB_URI = '/api/4.0/edges/%s/loadbalancer/config?async=true'
    EDGE_1 = 'edge-x'
    EDGE_2 = 'edge-y'

    def setUp(self):
        super(NsxvLoadbalancerTestCase, self).setUp()
        self._lb = nsxv_lb.NsxvLoadbalancer()
        self._nsxv = nsxv_api.NsxvApi(None, None, None, None)

    def test_edge_loadbalancer(self):
        h = None
        v = json.loads(self.EDGE_OBJ_JSON)

        with mock.patch.object(self._nsxv, 'do_request',
                               return_value=(h, v)) as mock_do_request:
            # Retrieve Edge LB
            lb = nsxv_lb.NsxvLoadbalancer.get_loadbalancer(
                self._nsxv, self.EDGE_1)

            # Repost Edge LB
            lb.submit_to_backend(self._nsxv, self.EDGE_2)

            mock_do_request.assert_called_with(
                nsxv_api.HTTP_PUT,
                self.LB_URI % self.EDGE_2,
                self.OUT_OBJ_JSON,
                format='json',
                encode=False)
