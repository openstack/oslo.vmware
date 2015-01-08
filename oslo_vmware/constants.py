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
Shared constants across the VMware ecosystem.
"""

# Datacenter path for HTTP access to datastores if the target server is an ESX/
# ESXi system: http://goo.gl/B5Htr8 for more information.
ESX_DATACENTER_PATH = 'ha-datacenter'

# User Agent for HTTP requests between OpenStack and vCenter.
USER_AGENT = 'OpenStack-ESX-Adapter'

# Key of the cookie header when using a SOAP session.
SOAP_COOKIE_KEY = 'vmware_soap_session'

# Key of the cookie header when using a CGI session.
CGI_COOKIE_KEY = 'vmware_cgi_ticket'
