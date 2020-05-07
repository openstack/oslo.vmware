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

import logging

from oslo_vmware import vim_util


LOG = logging.getLogger(__name__)


def get_dvs_moref(value):
    """Get managed DVS object reference.

    :param value: value of the DVS managed object
    :returns: managed object reference with given value and type
              'VmwareDistributedVirtualSwitch'
    """

    return vim_util.get_moref(value, 'VmwareDistributedVirtualSwitch')


def get_vlan_spec(session, vlan_id):
    """Gets portgroup vlan spec.

    :param session: vCenter soap session
    :param vlan_id: the vlan_id for the port
    :returns: The configuration when a single vlan_id is used for a port
    """
    # Create the spec for the vlan tag
    client_factory = session.vim.client.factory
    spec_ns = 'ns0:VmwareDistributedVirtualSwitchVlanIdSpec'
    vl_spec = client_factory.create(spec_ns)
    vl_spec.vlanId = vlan_id
    vl_spec.inherited = '0'
    return vl_spec


def get_trunk_vlan_spec(session, start=0, end=4094):
    """Gets portgroup trunk vlan spec.

    :param session: vCenter soap session
    :param start: the starting id
    :param end: then end id
    :returns: The configuration when a port uses trunk mode. This allows
              a guest to manage the vlan id.
    """
    client_factory = session.vim.client.factory
    spec_ns = 'ns0:VmwareDistributedVirtualSwitchTrunkVlanSpec'
    vlan_id = client_factory.create('ns0:NumericRange')
    vlan_id.start = start
    vlan_id.end = end
    vl_spec = client_factory.create(spec_ns)
    vl_spec.vlanId = vlan_id
    vl_spec.inherited = '0'
    return vl_spec


def get_port_group_spec(session, name, vlan_id, trunk_mode=False):
    """Gets the port group spec for a distributed port group

    :param session: vCenter soap session
    :param name: the name of the port group
    :param vlan_id: vlan_id for the port
    :param trunk_mode: indicates if the port will have trunk mode or use
                       specific tag above
    :returns: The configuration for a port group.
    """
    client_factory = session.vim.client.factory
    pg_spec = client_factory.create('ns0:DVPortgroupConfigSpec')
    pg_spec.name = name
    pg_spec.type = 'ephemeral'
    config = client_factory.create('ns0:VMwareDVSPortSetting')
    if trunk_mode:
        config.vlan = get_trunk_vlan_spec(session)
    elif vlan_id:
        config.vlan = get_vlan_spec(session, vlan_id)
    pg_spec.defaultPortConfig = config
    return pg_spec


def add_port_group(session, dvs_moref, name, vlan_id=None,
                   trunk_mode=False):
    """Add a new port group to the dvs_moref

    :param session: vCenter soap session
    :param dvs_moref: managed DVS object reference
    :param name: the name of the port group
    :param vlan_id: vlan_id for the port
    :param trunk_mode: indicates if the port will have trunk mode or use
                       specific tag above
    :returns: The new portgroup moref
    """
    pg_spec = get_port_group_spec(session, name, vlan_id,
                                  trunk_mode=trunk_mode)
    task = session.invoke_api(session.vim,
                              'CreateDVPortgroup_Task',
                              dvs_moref,
                              spec=pg_spec)
    task_info = session.wait_for_task(task)
    LOG.info("%(name)s create on %(dvs)s with %(value)s.",
             {'name': name,
              'dvs': vim_util.get_moref_value(dvs_moref),
              'value': task_info.result.value})
    return task_info.result


def get_portgroups(session, dvs_moref):
    """Gets all configured portgroups on the dvs_moref

    :param session: vCenter soap session
    :param dvs_moref: managed DVS object reference
    :returns: List of tuples that have the following format:
              (portgroup name, port group moref)
    """
    pgs = []
    port_groups = session.invoke_api(vim_util,
                                     'get_object_properties',
                                     session.vim,
                                     dvs_moref,
                                     ['portgroup'])
    while port_groups:
        if len(port_groups) and hasattr(port_groups[0], 'propSet'):
            for prop in port_groups[0].propSet:
                for val in prop.val[0]:
                    props = session.invoke_api(vim_util,
                                               'get_object_properties',
                                               session.vim,
                                               val, ['name'])
                    if len(props) and hasattr(props[0], 'propSet'):
                        for prop in props[0].propSet:
                            pgs.append((prop.val, val))
        port_groups = session._call_method(vim_util, 'continue_retrieval',
                                           port_groups)
    return pgs


def delete_port_group(session, portgroup_moref):
    """Delete a specific port group

    :param session: vCenter soap session
    :param portgroup_moref: managed portgroup object reference
    """
    task = session.invoke_api(session.vim,
                              'Destroy_Task',
                              portgroup_moref)
    session.wait_for_task(task)
