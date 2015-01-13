# Copyright 2015 VMware, Inc
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
import time
import xml.etree.ElementTree as et

from oslo_serialization import jsonutils

from oslo_vmware._i18n import _LI
from oslo_vmware.network.nsx.nsxv.api import api_helper
from oslo_vmware.network.nsx.nsxv.common import exceptions


LOG = logging.getLogger(__name__)

HTTP_GET = "GET"
HTTP_POST = "POST"
HTTP_DELETE = "DELETE"
HTTP_PUT = "PUT"
URI_PREFIX = "/api/4.0/edges"

# FwaaS constants
FIREWALL_SERVICE = "firewall/config"
FIREWALL_RULE_RESOURCE = "rules"

# NSXv Constants
FIREWALL_PREFIX = '/api/4.0/firewall/globalroot-0/config'
SECURITYGROUP_PREFIX = '/api/2.0/services/securitygroup'
VDN_PREFIX = '/api/2.0/vdn'
SERVICES_PREFIX = '/api/2.0/services'

# LbaaS Constants
LOADBALANCER_SERVICE = "loadbalancer/config"
VIP_RESOURCE = "virtualservers"
POOL_RESOURCE = "pools"
MONITOR_RESOURCE = "monitors"
APP_PROFILE_RESOURCE = "applicationprofiles"
APP_RULE_RESOURCE = "applicationrules"

# IPsec VPNaaS Constants
IPSEC_VPN_SERVICE = 'ipsec/config'

# Dhcp constants
DHCP_SERVICE = "dhcp/config"
DHCP_BINDING_RESOURCE = "bindings"


class NsxvApi(object):

    def __init__(self, address, user, password, retries=2):
        self.address = address
        self.user = user
        self.password = password
        self.retries = retries
        self.jsonapi_client = api_helper.NsxvApiHelper(address, user,
                                                       password, 'json')
        self.xmlapi_client = api_helper.NsxvApiHelper(address, user,
                                                      password, 'xml')

    def _client_request(self, client, method, uri, params, headers,
                        encode_params):
        retries = max(self.retries, 1)
        delay = 0.5
        for attempt in range(1, retries + 1):
            if attempt != 1:
                time.sleep(delay)
                delay = min(2 * delay, 60)
            try:
                return client(method, uri, params, headers, encode_params)
            except exceptions.ServiceConflict as e:
                if attempt == retries:
                    raise e
            LOG.info(_LI('NSXv: conflict on request. Trying again.'))

    def do_request(self, method, uri, params=None, format='json', **kwargs):
        LOG.debug("NsxvApi('%(method)s', '%(uri)s', '%(body)s')", {
                  'method': method,
                  'uri': uri,
                  'body': params})
        headers = kwargs.get('headers')
        encode_params = kwargs.get('encode', True)
        if format == 'json':
            _client = self.jsonapi_client.request
        else:
            _client = self.xmlapi_client.request
        header, content = self._client_request(_client, method, uri, params,
                                               headers, encode_params)
        if content == '':
            return header, {}
        if kwargs.get('decode', True):
            content = jsonutils.loads(content)
        return header, content

    def deploy_edge(self, request):
        uri = URI_PREFIX + "?async=true"
        return self.do_request(HTTP_POST, uri, request, decode=False)

    def update_edge(self, edge_id, request):
        uri = "%s/%s?async=true" % (URI_PREFIX, edge_id)
        return self.do_request(HTTP_PUT, uri, request, decode=False)

    def get_edge_id(self, job_id):
        uri = URI_PREFIX + "/jobs/%s" % job_id
        return self.do_request(HTTP_GET, uri, decode=True)

    def get_edge_jobs(self, edge_id):
        uri = URI_PREFIX + "/%s/jobs" % edge_id
        return self.do_request(HTTP_GET, uri, decode=True)

    def get_edge_deploy_status(self, edge_id):
        uri = URI_PREFIX + "/%s/status?getlatest=false" % edge_id
        return self.do_request(HTTP_GET, uri, decode="True")

    def delete_edge(self, edge_id):
        uri = "%s/%s" % (URI_PREFIX, edge_id)
        return self.do_request(HTTP_DELETE, uri)

    def add_vdr_internal_interface(self, edge_id, interface):
        uri = "%s/%s/interfaces?action=patch&async=true" % (URI_PREFIX,
                                                            edge_id)
        return self.do_request(HTTP_POST, uri, interface, decode=True)

    def update_vdr_internal_interface(
            self, edge_id, interface_index, interface):
        uri = "%s/%s/interfaces/%s?async=true" % (URI_PREFIX, edge_id,
                                                  interface_index)
        return self.do_request(HTTP_PUT, uri, interface, decode=True)

    def delete_vdr_internal_interface(self, edge_id, interface_index):
        uri = "%s/%s/interfaces/%d?async=true" % (URI_PREFIX, edge_id,
                                                  interface_index)
        return self.do_request(HTTP_DELETE, uri, decode=True)

    def get_interfaces(self, edge_id):
        uri = "%s/%s/vnics" % (URI_PREFIX, edge_id)
        return self.do_request(HTTP_GET, uri, decode=True)

    def update_interface(self, edge_id, vnic):
        uri = "%s/%s/vnics/%d?async=true" % (URI_PREFIX, edge_id,
                                             vnic['index'])
        return self.do_request(HTTP_PUT, uri, vnic, decode=True)

    def delete_interface(self, edge_id, vnic_index):
        uri = "%s/%s/vnics/%d?async=true" % (URI_PREFIX, edge_id, vnic_index)
        return self.do_request(HTTP_DELETE, uri, decode=True)

    def get_nat_config(self, edge_id):
        uri = "%s/%s/nat/config" % (URI_PREFIX, edge_id)
        return self.do_request(HTTP_GET, uri, decode=True)

    def update_nat_config(self, edge_id, nat):
        uri = "%s/%s/nat/config?async=true" % (URI_PREFIX, edge_id)
        return self.do_request(HTTP_PUT, uri, nat, decode=True)

    def delete_nat_rule(self, edge_id, rule_id):
        uri = "%s/%s/nat/config/rules/%s" % (URI_PREFIX, edge_id, rule_id)
        return self.do_request(HTTP_DELETE, uri, decode=True)

    def get_edge_status(self, edge_id):
        uri = "%s/%s/status?getlatest=false" % (URI_PREFIX, edge_id)
        return self.do_request(HTTP_GET, uri, decode=True)

    def get_edges(self):
        uri = URI_PREFIX
        return self.do_request(HTTP_GET, uri, decode=True)

    def get_edge_interfaces(self, edge_id):
        uri = "%s/%s/interfaces" % (URI_PREFIX, edge_id)
        return self.do_request(HTTP_GET, uri, decode=True)

    def update_routes(self, edge_id, routes):
        uri = "%s/%s/routing/config/static?async=true" % (URI_PREFIX, edge_id)
        return self.do_request(HTTP_PUT, uri, routes)

    def create_lswitch(self, lsconfig):
        uri = "/api/ws.v1/lswitch"
        return self.do_request(HTTP_POST, uri, lsconfig, decode=True)

    def delete_lswitch(self, lswitch_id):
        uri = "/api/ws.v1/lswitch/%s" % lswitch_id
        return self.do_request(HTTP_DELETE, uri)

    def get_loadbalancer_config(self, edge_id):
        uri = self._build_uri_path(edge_id, LOADBALANCER_SERVICE)
        return self.do_request(HTTP_GET, uri, decode=True)

    def enable_service_loadbalancer(self, edge_id, config):
        uri = self._build_uri_path(edge_id, LOADBALANCER_SERVICE)
        return self.do_request(HTTP_PUT, uri, config)

    def update_firewall(self, edge_id, fw_req):
        uri = self._build_uri_path(
            edge_id, FIREWALL_SERVICE)
        uri += '?async=true'
        return self.do_request(HTTP_PUT, uri, fw_req)

    def delete_firewall(self, edge_id):
        uri = self._build_uri_path(
            edge_id, FIREWALL_SERVICE, None)
        uri += '?async=true'
        return self.do_request(HTTP_DELETE, uri)

    def update_firewall_rule(self, edge_id, vcns_rule_id, fwr_req):
        uri = self._build_uri_path(
            edge_id, FIREWALL_SERVICE,
            FIREWALL_RULE_RESOURCE,
            vcns_rule_id)
        return self.do_request(HTTP_PUT, uri, fwr_req)

    def delete_firewall_rule(self, edge_id, vcns_rule_id):
        uri = self._build_uri_path(
            edge_id, FIREWALL_SERVICE,
            FIREWALL_RULE_RESOURCE,
            vcns_rule_id)
        return self.do_request(HTTP_DELETE, uri)

    def add_firewall_rule_above(self, edge_id, ref_vcns_rule_id, fwr_req):
        uri = self._build_uri_path(
            edge_id, FIREWALL_SERVICE,
            FIREWALL_RULE_RESOURCE)
        uri += "?aboveRuleId=" + ref_vcns_rule_id
        return self.do_request(HTTP_POST, uri, fwr_req)

    def add_firewall_rule(self, edge_id, fwr_req):
        uri = self._build_uri_path(
            edge_id, FIREWALL_SERVICE,
            FIREWALL_RULE_RESOURCE)
        return self.do_request(HTTP_POST, uri, fwr_req)

    def get_firewall(self, edge_id):
        uri = self._build_uri_path(edge_id, FIREWALL_SERVICE)
        return self.do_request(HTTP_GET, uri, decode=True)

    def get_firewall_rule(self, edge_id, vcns_rule_id):
        uri = self._build_uri_path(
            edge_id, FIREWALL_SERVICE,
            FIREWALL_RULE_RESOURCE,
            vcns_rule_id)
        return self.do_request(HTTP_GET, uri, decode=True)

    #
    # Edge LBAAS call helper
    #
    def create_vip(self, edge_id, vip_new):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            VIP_RESOURCE)
        return self.do_request(HTTP_POST, uri, vip_new)

    def get_vip(self, edge_id, vip_vseid):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            VIP_RESOURCE, vip_vseid)
        return self.do_request(HTTP_GET, uri, decode=True)

    def update_vip(self, edge_id, vip_vseid, vip_new):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            VIP_RESOURCE, vip_vseid)
        return self.do_request(HTTP_PUT, uri, vip_new)

    def delete_vip(self, edge_id, vip_vseid):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            VIP_RESOURCE, vip_vseid)
        return self.do_request(HTTP_DELETE, uri)

    def create_pool(self, edge_id, pool_new):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            POOL_RESOURCE)
        return self.do_request(HTTP_POST, uri, pool_new)

    def get_pool(self, edge_id, pool_vseid):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            POOL_RESOURCE, pool_vseid)
        return self.do_request(HTTP_GET, uri, decode=True)

    def update_pool(self, edge_id, pool_vseid, pool_new):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            POOL_RESOURCE, pool_vseid)
        return self.do_request(HTTP_PUT, uri, pool_new)

    def delete_pool(self, edge_id, pool_vseid):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            POOL_RESOURCE, pool_vseid)
        return self.do_request(HTTP_DELETE, uri)

    def create_health_monitor(self, edge_id, monitor_new):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            MONITOR_RESOURCE)
        return self.do_request(HTTP_POST, uri, monitor_new)

    def get_health_monitor(self, edge_id, monitor_vseid):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            MONITOR_RESOURCE, monitor_vseid)
        return self.do_request(HTTP_GET, uri, decode=True)

    def update_health_monitor(self, edge_id, monitor_vseid, monitor_new):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            MONITOR_RESOURCE,
            monitor_vseid)
        return self.do_request(HTTP_PUT, uri, monitor_new)

    def delete_health_monitor(self, edge_id, monitor_vseid):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            MONITOR_RESOURCE,
            monitor_vseid)
        return self.do_request(HTTP_DELETE, uri)

    def create_app_profile(self, edge_id, app_profile):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            APP_PROFILE_RESOURCE)
        return self.do_request(HTTP_POST, uri, app_profile)

    def update_app_profile(self, edge_id, app_profileid, app_profile):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            APP_PROFILE_RESOURCE, app_profileid)
        return self.do_request(HTTP_PUT, uri, app_profile)

    def delete_app_profile(self, edge_id, app_profileid):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            APP_PROFILE_RESOURCE,
            app_profileid)
        return self.do_request(HTTP_DELETE, uri)

    def create_app_rule(self, edge_id, app_rule):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            APP_RULE_RESOURCE)
        return self.do_request(HTTP_POST, uri, app_rule)

    def update_app_rule(self, edge_id, app_ruleid, app_rule):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            APP_RULE_RESOURCE, app_ruleid)
        return self.do_request(HTTP_PUT, uri, app_rule)

    def delete_app_rule(self, edge_id, app_ruleid):
        uri = self._build_uri_path(
            edge_id, LOADBALANCER_SERVICE,
            APP_RULE_RESOURCE,
            app_ruleid)
        return self.do_request(HTTP_DELETE, uri)

    def update_ipsec_config(self, edge_id, ipsec_config):
        uri = self._build_uri_path(edge_id, IPSEC_VPN_SERVICE)
        return self.do_request(HTTP_PUT, uri, ipsec_config)

    def delete_ipsec_config(self, edge_id):
        uri = self._build_uri_path(edge_id, IPSEC_VPN_SERVICE)
        return self.do_request(HTTP_DELETE, uri)

    def get_ipsec_config(self, edge_id):
        uri = self._build_uri_path(edge_id, IPSEC_VPN_SERVICE)
        return self.do_request(HTTP_GET, uri)

    def create_virtual_wire(self, vdn_scope_id, request):
        """Creates a VXLAN virtual wire

        The method will return the virtual wire ID.
        """
        uri = '/api/2.0/vdn/scopes/%s/virtualwires' % vdn_scope_id
        return self.do_request(HTTP_POST, uri, request, format='xml',
                               decode=False)

    def delete_virtual_wire(self, virtualwire_id):
        """Deletes a virtual wire."""
        uri = '/api/2.0/vdn/virtualwires/%s' % virtualwire_id
        return self.do_request(HTTP_DELETE, uri, format='xml')

    def create_port_group(self, dvs_id, request):
        """Creates a port group on a DVS

        The method will return the port group ID.
        """
        uri = '/api/2.0/xvs/switches/%s/networks' % dvs_id
        return self.do_request(HTTP_POST, uri, request, format='xml',
                               decode=False)

    def delete_port_group(self, dvs_id, portgroup_id):
        """Deletes a portgroup."""
        uri = '/api/2.0/xvs/switches/%s/networks/%s' % (dvs_id,
                                                        portgroup_id)
        return self.do_request(HTTP_DELETE, uri, format='xml', decode=False)

    def query_interface(self, edge_id, vnic_index):
        uri = "%s/%s/vnics/%d" % (URI_PREFIX, edge_id, vnic_index)
        return self.do_request(HTTP_GET, uri, decode=True)

    def reconfigure_dhcp_service(self, edge_id, request_config):
        """Reconfigure dhcp static bindings in the created Edge."""
        uri = "/api/4.0/edges/%s/dhcp/config?async=true" % edge_id

        return self.do_request(HTTP_PUT, uri, request_config)

    def query_dhcp_configuration(self, edge_id):
        """Query DHCP configuration from the specific edge."""
        uri = "/api/4.0/edges/%s/dhcp/config" % edge_id
        return self.do_request(HTTP_GET, uri)

    def create_dhcp_binding(self, edge_id, request_config):
        """Append one dhcp static binding on the edge."""
        uri = self._build_uri_path(edge_id,
                                   DHCP_SERVICE, DHCP_BINDING_RESOURCE,
                                   is_async=True)
        return self.do_request(HTTP_POST, uri, request_config, decode=False)

    def delete_dhcp_binding(self, edge_id, binding_id):
        """Delete one dhcp static binding on the edge."""
        uri = self._build_uri_path(edge_id,
                                   DHCP_SERVICE, DHCP_BINDING_RESOURCE,
                                   binding_id, is_async=True)
        return self.do_request(HTTP_DELETE, uri, decode=False)

    def create_security_group(self, request):
        """Creates a security group container in nsx.

        The method will return the security group ID.
        """
        uri = '%s/globalroot-0' % SECURITYGROUP_PREFIX
        return self.do_request(HTTP_POST, uri, request, format='xml',
                               decode=False)

    def delete_security_group(self, securitygroup_id):
        """Deletes a security group container."""
        uri = '%s/%s?force=true' % (SECURITYGROUP_PREFIX, securitygroup_id)
        return self.do_request(HTTP_DELETE, uri, format='xml', decode=False)

    def create_section(self, type, request):
        """Creates a layer 3 or layer 2 section in nsx rule table.

        The method will return the uri to newly created section.
        """
        if type == 'ip':
            sec_type = 'layer3sections'
        else:
            sec_type = 'layer2sections'
        uri = '%s/%s?autoSaveDraft=false' % (FIREWALL_PREFIX, sec_type)
        return self.do_request(HTTP_POST, uri, request, format='xml',
                               decode=False, encode=False)

    def update_section(self, section_uri, request, h):
        """Replaces a section in nsx rule table."""
        uri = '%s?autoSaveDraft=false' % section_uri
        headers = self._get_section_header(section_uri, h)
        return self.do_request(HTTP_PUT, uri, request, format='xml',
                               decode=False, encode=False, headers=headers)

    def delete_section(self, section_uri):
        """Deletes a section in nsx rule table."""
        uri = '%s?autoSaveDraft=false' % section_uri
        return self.do_request(HTTP_DELETE, uri, format='xml', decode=False)

    def get_section(self, section_uri):
        return self.do_request(HTTP_GET, section_uri, format='xml',
                               decode=False)

    def get_section_id(self, section_name):
        """Retrieve the id of a section from nsx."""
        uri = FIREWALL_PREFIX
        h, section_list = self.do_request(HTTP_GET, uri, decode=False,
                                          format='xml')
        root = et.fromstring(section_list)

        for elem in root.findall('.//*'):
            if elem.tag == 'section' and elem.attrib['name'] == section_name:
                return elem.attrib['id']

    def update_section_by_id(self, id, type, request):
        """Update a section while building its uri from the id."""
        if type == 'ip':
            sec_type = 'layer3sections'
        else:
            sec_type = 'layer2sections'
        section_uri = '%s/%s/%s' % (FIREWALL_PREFIX, sec_type, id)
        self.update_section(section_uri, request, h=None)

    def _get_section_header(self, section_uri, h=None):
        if h is None:
            h, c = self.do_request(HTTP_GET, section_uri, format='xml',
                                   decode=False)
        etag = h['etag']
        headers = {'If-Match': etag}
        return headers

    def remove_rule_from_section(self, section_uri, rule_id):
        """Deletes a rule from nsx section table."""
        uri = '%s/rules/%s?autoSaveDraft=false' % (section_uri, rule_id)
        headers = self._get_section_header(section_uri)
        return self.do_request(HTTP_DELETE, uri, format='xml',
                               headers=headers)

    def add_member_to_security_group(self, security_group_id, member_id):
        """Adds a vnic member to nsx security group."""
        uri = '%s/%s/members/%s' % (SECURITYGROUP_PREFIX,
                                    security_group_id, member_id)
        return self.do_request(HTTP_PUT, uri, format='xml', decode=False)

    def remove_member_from_security_group(self, security_group_id,
                                          member_id):
        """Removes a vnic member from nsx security group."""
        uri = '%s/%s/members/%s' % (SECURITYGROUP_PREFIX,
                                    security_group_id, member_id)
        return self.do_request(HTTP_DELETE, uri, format='xml', decode=False)

    def _build_uri_path(self, edge_id,
                        service,
                        resource=None,
                        resource_id=None,
                        parent_resource_id=None,
                        fields=None,
                        relations=None,
                        filters=None,
                        types=None,
                        is_attachment=False,
                        is_async=False):
        uri_prefix = "%s/%s/%s" % (URI_PREFIX, edge_id, service)
        if resource:
            res_path = resource + (resource_id and "/%s" % resource_id or '')
            uri_path = "%s/%s" % (uri_prefix, res_path)
        else:
            uri_path = uri_prefix
        if is_async:
            return uri_path + "?async=true"
        else:
            return uri_path

    def _scopingobjects_lookup(self, type_name, object_id):
        uri = '%s/usermgmt/scopingobjects' % SERVICES_PREFIX
        h, so_list = self.do_request(HTTP_GET, uri, decode=False,
                                     format='xml')

        root = et.fromstring(so_list)

        for elem in root.findall('.//*'):
            if(elem.tag == 'object'
               and elem.find('objectTypeName').text == type_name
               and elem.find('objectId').text == object_id):

                return True

        return False

    def validate_datacenter_moid(self, object_id):
        return self._scopingobjects_lookup('Datacenter', object_id)

    def validate_network(self, object_id):
        return (self._scopingobjects_lookup('Network', object_id) or
                self._scopingobjects_lookup('DistributedVirtualPortgroup',
                                            object_id) or
                self._scopingobjects_lookup('VirtualWire', object_id))

    def validate_vdn_scope(self, object_id):
        uri = '%s/scopes' % VDN_PREFIX
        h, scope_list = self.do_request(HTTP_GET, uri, decode=False,
                                        format='xml')

        root = et.fromstring(scope_list)
        for elem in root.findall('.//*'):
            if elem.tag == 'objectId' and elem.text == object_id:
                return True

        return False

    def validate_dvs(self, object_id):
        uri = '%s/switches' % VDN_PREFIX
        h, dvs_list = self.do_request(HTTP_GET, uri, decode=False,
                                      format='xml')

        root = et.fromstring(dvs_list)
        for elem in root.findall('.//*'):
            if elem.tag == 'objectId' and elem.text == object_id:
                return True

        return False
