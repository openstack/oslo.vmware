# Copyright (c) 2018 VMware, Inc.
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

"""Unit tests for VMware DVS utility module."""

import collections
from unittest import mock

from oslo_vmware import dvs_util
from oslo_vmware.tests import base
from oslo_vmware import vim_util

ObjectContent = collections.namedtuple('ObjectContent', ['obj', 'propSet'])
DynamicProperty = collections.namedtuple('Property', ['name', 'val'])
Moref = collections.namedtuple('Moref', ['name', 'type'])


class DvsUtilTest(base.TestCase):
    """Test class for utility methods in dvs_util."""

    def test_get_dvs_moref(self):
        moref = dvs_util.get_dvs_moref('dvs-123')
        self.assertEqual('dvs-123', vim_util.get_moref_value(moref))
        self.assertEqual('VmwareDistributedVirtualSwitch',
                         vim_util.get_moref_type(moref))

    def test_get_vlan_spec(self):
        session = mock.Mock()
        spec = dvs_util.get_vlan_spec(session, 7)
        self.assertEqual(7, spec.vlanId)

    def test_get_trunk_vlan_spec(self):
        session = mock.Mock()
        spec = dvs_util.get_trunk_vlan_spec(session, start=1, end=2)
        self.assertEqual(1, spec.vlanId.start)
        self.assertEqual(2, spec.vlanId.end)

    def test_get_port_group_spec(self):
        session = mock.Mock()
        spec = dvs_util.get_port_group_spec(session, 'pg', 7)
        self.assertEqual('pg', spec.name)
        self.assertEqual('ephemeral', spec.type)
        self.assertEqual(7, spec.defaultPortConfig.vlan.vlanId)

    def test_get_port_group_spec_trunk(self):
        session = mock.Mock()
        spec = dvs_util.get_port_group_spec(session, 'pg', None,
                                            trunk_mode=True)
        self.assertEqual('pg', spec.name)
        self.assertEqual('ephemeral', spec.type)
        self.assertEqual(0, spec.defaultPortConfig.vlan.start)
        self.assertEqual(4094, spec.defaultPortConfig.vlan.end)

    @mock.patch.object(dvs_util, 'get_port_group_spec')
    def test_add_port_group(self, mock_spec):
        session = mock.Mock()
        dvs_moref = dvs_util.get_dvs_moref('dvs-123')
        spec = dvs_util.get_port_group_spec(session, 'pg', 7)
        mock_spec.return_value = spec
        pg_moref = vim_util.get_moref('dvportgroup-7',
                                      'DistributedVirtualPortgroup')

        def wait_for_task_side_effect(task):
            task_info = mock.Mock()
            task_info.result = pg_moref
            return task_info

        session.wait_for_task.side_effect = wait_for_task_side_effect
        pg = dvs_util.add_port_group(session, dvs_moref, 'pg',
                                     vlan_id=7)
        self.assertEqual(pg, pg_moref)
        session.invoke_api.assert_called_once_with(
            session.vim, 'CreateDVPortgroup_Task', dvs_moref,
            spec=spec)

    @mock.patch.object(dvs_util, 'get_port_group_spec')
    def test_add_port_group_trunk(self, mock_spec):
        session = mock.Mock()
        dvs_moref = dvs_util.get_dvs_moref('dvs-123')
        spec = dvs_util.get_port_group_spec(session, 'pg', None,
                                            trunk_mode=True)
        mock_spec.return_value = spec
        dvs_util.add_port_group(session, dvs_moref, 'pg',
                                trunk_mode=True)
        session.invoke_api.assert_called_once_with(
            session.vim, 'CreateDVPortgroup_Task', dvs_moref,
            spec=spec)

    def test_get_portgroups_empty(self):
        session = mock.Mock()
        dvs_moref = dvs_util.get_dvs_moref('dvs-123')
        session.invoke_api.return_value = []
        pgs = dvs_util.get_portgroups(session, dvs_moref)
        self.assertEqual([], pgs)

    def test_get_portgroups(self):
        session = mock.Mock()
        dvs_moref = dvs_util.get_dvs_moref('dvs-123')
        pg_moref = vim_util.get_moref('dvportgroup-7',
                                      'DistributedVirtualPortgroup')

        def session_invoke_api_side_effect(module, method, *args, **kwargs):
            if module == vim_util and method == 'get_object_properties':
                if ['portgroup'] in args:
                    propSet = [DynamicProperty(name='portgroup',
                                               val=[[pg_moref]])]
                    return [ObjectContent(obj=dvs_moref,
                                          propSet=propSet)]
                if ['name'] in args:
                    propSet = [DynamicProperty(name='name',
                                               val='pg-name')]
                    return [ObjectContent(obj=pg_moref,
                                          propSet=propSet)]

        session.invoke_api.side_effect = session_invoke_api_side_effect
        session._call_method.return_value = []
        pgs = dvs_util.get_portgroups(session, dvs_moref)
        result = [('pg-name', pg_moref)]
        self.assertEqual(result, pgs)

    def test_delete_port_group(self):
        session = mock.Mock()
        dvs_util.delete_port_group(session, 'pg-moref')
        session.invoke_api.assert_called_once_with(
            session.vim, 'Destroy_Task', 'pg-moref')
