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
VMware PBM client and PBM related utility methods

PBM is used for policy based placement in VMware datastores.
Refer http://goo.gl/GR2o6U for more details.
"""

import logging
import suds
import suds.sax.element as element

from oslo.vmware import vim
from oslo.vmware import vim_util


SERVICE_INSTANCE = 'ServiceInstance'
SERVICE_TYPE = 'PbmServiceInstance'

LOG = logging.getLogger(__name__)


class PBMClient(vim.Vim):
    """SOAP based PBM client."""

    def __init__(self, pbm_wsdl_loc, protocol='https', host='localhost',
                 port=443):
        """Constructs a PBM client object.

        :param pbm_wsdl_loc: PBM WSDL file location
        :param protocol: http or https
        :param host: server IP address or host name
        :param port: port for connection
        """
        self._url = vim_util.get_soap_url(protocol, host, port, 'pbm')
        self._pbm_client = suds.client.Client(pbm_wsdl_loc, location=self._url)
        self._pbm_service_content = None

    def set_cookie(self, cookie):
        """Set the authenticated VIM session's cookie in the SOAP client.

        :param cookie: cookie to set
        """
        elem = element.Element('vcSessionCookie').setText(cookie)
        self._pbm_client.set_options(soapheaders=elem)

    @property
    def client(self):
        return self._pbm_client

    @property
    def service_content(self):
        if not self._pbm_service_content:
            si_moref = vim_util.get_moref(SERVICE_INSTANCE, SERVICE_TYPE)
            self._pbm_service_content = (
                self._pbm_client.service.PbmRetrieveServiceContent(si_moref))
        return self._pbm_service_content


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
