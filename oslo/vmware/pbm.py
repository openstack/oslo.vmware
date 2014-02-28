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
VMware PBM client.

PBM is used for policy based placement in VMware datastores.
Refer http://goo.gl/GR2o6U for more details.
"""

import suds
import suds.sax.element as element

from oslo.vmware import vim
from oslo.vmware import vim_util


SERVICE_INSTANCE = 'ServiceInstance'
SERVICE_TYPE = 'PbmServiceInstance'


class PBMClient(vim.Vim):
    """SOAP based PBM client."""

    def __init__(self, pbm_wsdl_loc, protocol='https', host='localhost'):
        """Constructs a PBM client object.

        :param pbm_wsdl_loc: PBM WSDL file location
        :param protocol: http or https
        :param host: server IP address[:port] or host name[:port]
        """
        self._url = vim_util.get_soap_url(protocol, host, 'pbm')
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
