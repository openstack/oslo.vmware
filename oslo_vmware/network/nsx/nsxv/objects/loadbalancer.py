# Copyright 2015 VMware, Inc.
# All Rights Reserved
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
#

import logging

from oslo_vmware.network.nsx.nsxv.objects import edge_cfg_obj


LOG = logging.getLogger(__name__)


class NsxvLoadbalancer(edge_cfg_obj.NsxvEdgeCfgObj):

    SERVICE_NAME = 'loadbalancer'

    def __init__(
            self,
            enabled=True,
            enable_service_insertion=False,
            acceleration_enabled=False):
        super(NsxvLoadbalancer, self).__init__()
        self.payload = {
            'enabled': enabled,
            'enableServiceInsertion': enable_service_insertion,
            'accelerationEnabled': acceleration_enabled}
        self.virtual_servers = {}

    def get_service_name(self):
        return self.SERVICE_NAME

    def add_virtual_server(self, virtual_server):
        self.virtual_servers[virtual_server.payload['name']] = virtual_server

    def del_virtual_server(self, name):
        self.virtual_servers.pop(name, None)

    def serializable_payload(self):
        virt_servers = []
        app_profiles = []
        app_rules = []
        pools = []
        monitors = []

        virt_id = 1
        app_prof_id = 1
        app_rule_id = 1
        pool_id = 1
        monitor_id = 1
        member_id = 1

        for virtual_server in self.virtual_servers.values():
            s_virt = virtual_server.payload.copy()
            s_virt['virtualServerId'] = 'virtualServer-%d' % virt_id
            virt_id += 1

            # Setup app profile
            s_app_prof = virtual_server.app_profile.payload.copy()
            s_app_prof['applicationProfileId'] = ('applicationProfile-%d' %
                                                  app_prof_id)
            app_profiles.append(s_app_prof)
            app_prof_id += 1

            # Bind virtual server to app profile
            s_virt['applicationProfileId'] = s_app_prof['applicationProfileId']

            # Setup app rules
            if virtual_server.app_rules.values():
                s_virt['applicationRuleId'] = []
                for app_rule in virtual_server.app_rules.values():
                    s_app_rule = app_rule.payload.copy()
                    s_app_rule['applicationRuleId'] = ('applicationRule-%d' %
                                                       app_rule_id)
                    app_rule_id += 1

                    # Add to LB object, bind to virtual server
                    app_rules.append(s_app_rule)
                    s_virt['applicationRuleId'].append(
                        s_app_rule['applicationRuleId'])

            # Setup pools
            s_pool = virtual_server.default_pool.payload.copy()
            s_pool['poolId'] = 'pool-%d' % pool_id
            pool_id += 1
            pools.append(s_pool)

            # Add pool members
            s_pool['member'] = []
            for member in virtual_server.default_pool.members.values():
                s_m = member.payload.copy()
                s_m['memberId'] = 'member-%d' % member_id
                member_id += 1
                s_pool['member'].append(s_m)

            # Bind pool to virtual server
            s_virt['defaultPoolId'] = s_pool['poolId']

            s_pool['monitorId'] = []
            # Add monitors
            for monitor in virtual_server.default_pool.monitors.values():
                s_mon = monitor.payload.copy()
                s_mon['monitorId'] = 'monitor-%d' % monitor_id
                monitor_id += 1

                s_pool['monitorId'].append(s_mon['monitorId'])

                monitors.append(s_mon)

            virt_servers.append(s_virt)

        payload = self.payload.copy()
        payload['applicationProfile'] = app_profiles
        if app_rules:
            payload['applicationRule'] = app_rules
        payload['monitor'] = monitors
        payload['pool'] = pools
        payload['virtualServer'] = virt_servers
        payload['featureType'] = 'loadbalancer_4.0'

        return payload

    @staticmethod
    def get_loadbalancer(nsxv_api, edge_id):
        edge_lb = edge_cfg_obj.NsxvEdgeCfgObj.get_object(
            nsxv_api,
            edge_id,
            NsxvLoadbalancer.SERVICE_NAME)

        lb_obj = NsxvLoadbalancer(
            edge_lb['enabled'],
            edge_lb['enableServiceInsertion'],
            edge_lb['accelerationEnabled'])

        # Construct loadbalancer objects
        for virt_srvr in edge_lb['virtualServer']:
            v_s = NsxvLBVirtualServer(
                virt_srvr['name'],
                virt_srvr['ipAddress'],
                virt_srvr['port'],
                virt_srvr['protocol'],
                virt_srvr['enabled'],
                virt_srvr['accelerationEnabled'],
                virt_srvr['connectionLimit'])

            # Find application profile objects, attach to virtual server
            for app_prof in edge_lb['applicationProfile']:
                if (virt_srvr['applicationProfileId']
                        == app_prof['applicationProfileId']):
                    a_p = NsxvLBAppProfile(
                        app_prof['name'],
                        app_prof['serverSslEnabled'],
                        app_prof['sslPassthrough'],
                        app_prof['template'],
                        app_prof['insertXForwardedFor'])

                    if app_prof['persistence']:
                        a_p.set_persistence(
                            True,
                            app_prof['persistence']['method'],
                            app_prof['persistence'].get('cookieName'),
                            app_prof['persistence'].get('cookieMode'),
                            app_prof['persistence'].get('expire'))

                    v_s.set_app_profile(a_p)

            # Find default pool, attach to virtual server
            for pool in edge_lb['pool']:
                if virt_srvr['defaultPoolId'] == pool['poolId']:
                    p = NsxvLBPool(
                        pool['name'],
                        pool['algorithm'],
                        pool['transparent'])

                    # Add pool members to pool
                    for member in pool['member']:
                        m = NsxvLBPoolMember(
                            member['name'],
                            member['ipAddress'],
                            member['port'],
                            member['monitorPort'],
                            member['condition'],
                            member['weight'],
                            member['minConn'],
                            member['maxConn'])

                        p.add_member(m)

                    # Add monitors to pool
                    for mon in edge_lb['monitor']:
                        if mon['monitorId'] in pool['monitorId']:
                            m = NsxvLBMonitor(
                                mon['name'],
                                mon['interval'],
                                mon['maxRetries'],
                                mon['method'],
                                mon['timeout'],
                                mon['type'],
                                mon['url'])

                            p.add_monitor(m)

                    v_s.set_default_pool(p)

            # Add application rules to virtual server
            for rule in edge_lb['applicationRule']:
                if rule['applicationRuleId'] in virt_srvr['applicationRuleId']:
                    r = NsxvLBAppRule(
                        rule['name'],
                        rule['script'])

                    v_s.add_app_rule(r)

            lb_obj.add_virtual_server(v_s)

        return lb_obj


class NsxvLBAppProfile():
    def __init__(
            self,
            name,
            server_ssl_enabled=False,
            ssl_pass_through=False,
            template='TCP',
            insert_xff=False,
            persist=False,
            persist_method='cookie',
            persist_cookie_name='JSESSIONID',
            persist_cookie_mode='insert',
            persist_expire=30):
        self.payload = {
            'name': name,
            'serverSslEnabled': server_ssl_enabled,
            'sslPassthrough': ssl_pass_through,
            'template': template,
            'insertXForwardedFor': insert_xff}

        if persist:
            self.payload['persistence'] = {
                'method': persist_method,
                'expire': persist_expire
            }
            if persist_cookie_mode == 'cookie':
                self.payload['persistence']['cookieMode'] = persist_cookie_mode
                self.payload['persistence']['cookieName'] = persist_cookie_name

    def set_persistence(
            self,
            persist=False,
            persist_method='cookie',
            persist_cookie_name='JSESSIONID',
            persist_cookie_mode='insert',
            persist_expire=30):

        if persist:
            self.payload['persistence'] = {
                'method': persist_method,
                'expire': persist_expire
            }
            if persist_cookie_mode == 'cookie':
                self.payload['persistence']['cookieMode'] = persist_cookie_mode
                self.payload['persistence']['cookieName'] = persist_cookie_name

        else:
            self.payload.pop('persistence', None)


class NsxvLBAppRule(object):
    def __init__(self, name, script):
        self.payload = {
            'name': name,
            'script': script}


class NsxvLBVirtualServer(object):
    def __init__(
            self,
            name,
            ip_address,
            port=80,
            protocol='HTTP',
            enabled=True,
            acceleration_enabled=False,
            connection_limit=0,
            enable_service_insertion=False):
        self.payload = {
            'name': name,
            'ipAddress': ip_address,
            'port': port,
            'protocol': protocol,
            'enabled': enabled,
            'accelerationEnabled': acceleration_enabled,
            'connectionLimit': connection_limit,
            'enableServiceInsertion': enable_service_insertion}

        self.app_rules = {}
        self.app_profile = None
        self.default_pool = None

    def add_app_rule(self, app_rule):
        self.app_rules[app_rule.payload['name']] = app_rule

    def del_app_rule(self, name):
        self.app_rules.pop(name, None)

    def set_default_pool(self, pool):
        self.default_pool = pool

    def set_app_profile(self, app_profile):
        self.app_profile = app_profile


class NsxvLBMonitor(object):
    def __init__(
            self,
            name,
            interval=10,
            max_retries=3,
            method='GET',
            timeout=15,
            mon_type='http',
            url='/'):
        self.payload = {
            'name': name,
            'interval': interval,
            'maxRetries': max_retries,
            'method': method,
            'timeout': timeout,
            'type': mon_type,
            'url': url}


class NsxvLBPoolMember(object):
    def __init__(
            self,
            name,
            ip_address,
            port,
            monitor_port=None,
            condition='enabled',
            weight=1,
            min_conn=0,
            max_conn=0):

        self.payload = {
            'name': name,
            'ipAddress': ip_address,
            'port': port,
            'monitorPort': monitor_port,
            'condition': condition,
            'weight': weight,
            'minConn': min_conn,
            'maxConn': max_conn}


class NsxvLBPool(object):
    def __init__(
            self,
            name,
            algorithm='round-robin',
            transparent=False):
        self.payload = {
            'name': name,
            'algorithm': algorithm,
            'transparent': transparent}

        self.members = {}
        self.monitors = {}

    def add_member(self, member):
        self.members[member.payload['name']] = member

    def del_member(self, name):
        self.members.pop(name, None)

    def add_monitor(self, monitor):
        self.monitors[monitor.payload['name']] = monitor

    def del_monitor(self, name):
        self.monitors.pop(name, None)
