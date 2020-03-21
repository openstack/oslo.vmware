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

"""
VMware PBM service client and PBM related utility methods

PBM is used for policy based placement in VMware datastores.
Refer http://goo.gl/GR2o6U for more details.
"""

import logging
import os

import urllib.parse as urlparse
import urllib.request as urllib

from oslo_vmware import service
from oslo_vmware import vim_util


SERVICE_TYPE = 'PbmServiceInstance'

LOG = logging.getLogger(__name__)


class Pbm(service.Service):
    """Service class that provides access to the Storage Policy API."""

    def __init__(self, protocol='https', host='localhost', port=443,
                 wsdl_url=None, cacert=None, insecure=True, pool_maxsize=10,
                 connection_timeout=None, op_id_prefix='oslo.vmware'):
        """Constructs a PBM service client object.

        :param protocol: http or https
        :param host: server IP address or host name
        :param port: port for connection
        :param wsdl_url: PBM WSDL url
        :param cacert: Specify a CA bundle file to use in verifying a
                       TLS (https) server certificate.
        :param insecure: Verify HTTPS connections using system certificates,
                         used only if cacert is not specified
        :param pool_maxsize: Maximum number of connections in http
                             connection pool
        :param op_id_prefix: String prefix for the operation ID.
        :param connection_timeout: Maximum time in seconds to wait for peer to
                                   respond.
        """
        base_url = service.Service.build_base_url(protocol, host, port)
        soap_url = base_url + '/pbm'
        super(Pbm, self).__init__(wsdl_url, soap_url, cacert, insecure,
                                  pool_maxsize, connection_timeout,
                                  op_id_prefix)

    def set_soap_cookie(self, cookie):
        """Set the specified vCenter session cookie in the SOAP header

        :param cookie: cookie to set
        """
        self._vc_session_cookie = cookie

    def retrieve_service_content(self):
        ref = vim_util.get_moref(service.SERVICE_INSTANCE, SERVICE_TYPE)
        return self.PbmRetrieveServiceContent(ref)

    def __repr__(self):
        return "PBM Object"

    def __str__(self):
        return "PBM Object"


def get_all_profiles(session):
    """Get all the profiles defined in VC server.

    :returns: PbmProfile data objects
    :raises: VimException, VimFaultException, VimAttributeException,
             VimSessionOverLoadException, VimConnectionException
    """
    LOG.debug("Fetching all the profiles defined in VC server.")

    pbm = session.pbm
    profile_manager = pbm.service_content.profileManager
    res_type = pbm.client.factory.create('ns0:PbmProfileResourceType')
    res_type.resourceType = 'STORAGE'
    profiles = []
    profile_ids = session.invoke_api(pbm,
                                     'PbmQueryProfile',
                                     profile_manager,
                                     resourceType=res_type)
    LOG.debug("Fetched profile IDs: %s.", profile_ids)
    if profile_ids:
        profiles = session.invoke_api(pbm,
                                      'PbmRetrieveContent',
                                      profile_manager,
                                      profileIds=profile_ids)
    return profiles


def get_profile_id_by_name(session, profile_name):
    """Get the profile UUID corresponding to the given profile name.

    :param profile_name: profile name whose UUID needs to be retrieved
    :returns: profile UUID string or None if profile not found
    :raises: VimException, VimFaultException, VimAttributeException,
             VimSessionOverLoadException, VimConnectionException
    """
    LOG.debug("Retrieving profile ID for profile: %s.", profile_name)
    for profile in get_all_profiles(session):
        if profile.name == profile_name:
            profile_id = profile.profileId
            LOG.debug("Retrieved profile ID: %(id)s for profile: %(name)s.",
                      {'id': profile_id,
                       'name': profile_name})
            return profile_id
    return None


def filter_hubs_by_profile(session, hubs, profile_id):
    """Filter and return hubs that match the given profile.

    :param hubs: PbmPlacementHub morefs
    :param profile_id: profile ID
    :returns: subset of hubs that match the given profile
    :raises: VimException, VimFaultException, VimAttributeException,
             VimSessionOverLoadException, VimConnectionException
    """
    LOG.debug("Filtering hubs: %(hubs)s that match profile: %(profile)s.",
              {'hubs': hubs,
               'profile': profile_id})

    pbm = session.pbm
    placement_solver = pbm.service_content.placementSolver
    filtered_hubs = session.invoke_api(pbm,
                                       'PbmQueryMatchingHub',
                                       placement_solver,
                                       hubsToSearch=hubs,
                                       profile=profile_id)
    LOG.debug("Filtered hubs: %s", filtered_hubs)
    return filtered_hubs


def convert_datastores_to_hubs(pbm_client_factory, datastores):
    """Convert given datastore morefs to PbmPlacementHub morefs.

    :param pbm_client_factory: Factory to create PBM API input specs
    :param datastores: list of datastore morefs
    :returns: list of PbmPlacementHub morefs
    """
    hubs = []
    for ds in datastores:
        hub = pbm_client_factory.create('ns0:PbmPlacementHub')
        hub.hubId = ds.value
        hub.hubType = 'Datastore'
        hubs.append(hub)
    return hubs


def filter_datastores_by_hubs(hubs, datastores):
    """Get filtered subset of datastores corresponding to the given hub list.

    :param hubs: list of PbmPlacementHub morefs
    :param datastores: all candidate datastores
    :returns: subset of datastores corresponding to the given hub list
    """
    filtered_dss = []
    hub_ids = [hub.hubId for hub in hubs]
    for ds in datastores:
        if ds.value in hub_ids:
            filtered_dss.append(ds)
    return filtered_dss


def get_pbm_wsdl_location(vc_version):
    """Return PBM WSDL file location corresponding to VC version.

    :param vc_version: a dot-separated version string. For example, "1.2".
    :return: the pbm wsdl file location.
    """
    if not vc_version:
        return
    ver = vc_version.split('.')
    major_minor = ver[0]
    if len(ver) >= 2:
        major_minor = '%s.%s' % (major_minor, ver[1])
    curr_dir = os.path.abspath(os.path.dirname(__file__))
    pbm_service_wsdl = os.path.join(curr_dir, 'wsdl', major_minor,
                                    'pbmService.wsdl')
    if not os.path.exists(pbm_service_wsdl):
        LOG.warning("PBM WSDL file %s not found.", pbm_service_wsdl)
        return
    pbm_wsdl = urlparse.urljoin('file:', urllib.pathname2url(pbm_service_wsdl))
    LOG.debug("Using PBM WSDL location: %s.", pbm_wsdl)
    return pbm_wsdl


def get_profiles(session, vm):
    """Query storage profiles associated with the given vm.

    :param session: VMwareAPISession instance
    :param vm: vm reference
    :return: profile IDs
    """
    pbm = session.pbm
    profile_manager = pbm.service_content.profileManager

    object_ref = pbm.client.factory.create('ns0:PbmServerObjectRef')
    object_ref.key = vm.value
    object_ref.objectType = 'virtualMachine'

    return session.invoke_api(pbm, 'PbmQueryAssociatedProfile',
                              profile_manager, entity=object_ref)


def get_profiles_by_ids(session, profile_ids):
    """Get storage profiles by IDs.

    :param session: VMwareAPISession instance
    :param profile_ids: profile IDs
    :return: profile objects
    """
    profiles = []
    if profile_ids:
        pbm = session.pbm
        profile_manager = pbm.service_content.profileManager
        profiles = session.invoke_api(pbm,
                                      'PbmRetrieveContent',
                                      profile_manager,
                                      profileIds=profile_ids)
    return profiles
