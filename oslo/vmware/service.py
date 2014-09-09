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
Common classes that provide access to vSphere services.
"""

import httplib
import logging
import urllib2

import netaddr
import six
import suds

from oslo.vmware._i18n import _
from oslo.vmware import exceptions
from oslo.vmware import vim_util


ADDRESS_IN_USE_ERROR = 'Address already in use'
CONN_ABORT_ERROR = 'Software caused connection abort'
RESP_NOT_XML_ERROR = 'Response is "text/html", not "text/xml"'

SERVICE_INSTANCE = 'ServiceInstance'

LOG = logging.getLogger(__name__)


class ServiceMessagePlugin(suds.plugin.MessagePlugin):
    """Suds plug-in handling some special cases while calling VI SDK."""

    def add_attribute_for_value(self, node):
        """Helper to handle AnyType.

        Suds does not handle AnyType properly. But VI SDK requires type
        attribute to be set when AnyType is used.

        :param node: XML value node
        """
        if node.name == 'value':
            node.set('xsi:type', 'xsd:string')

    def marshalled(self, context):
        """Modifies the envelope document before it is sent.

        This method provides the plug-in with the opportunity to prune empty
        nodes and fix nodes before sending it to the server.

        :param context: send context
        """
        # Suds builds the entire request object based on the WSDL schema.
        # VI SDK throws server errors if optional SOAP nodes are sent
        # without values; e.g., <test/> as opposed to <test>test</test>.
        context.envelope.prune()
        context.envelope.walk(self.add_attribute_for_value)


class Service(object):
    """Base class containing common functionality for invoking vSphere
    services
    """

    def __init__(self, wsdl_url=None, soap_url=None):
        self.wsdl_url = wsdl_url
        self.soap_url = soap_url
        LOG.debug("Creating suds client with soap_url='%s' and wsdl_url='%s'",
                  self.soap_url, self.wsdl_url)
        self.client = suds.client.Client(self.wsdl_url,
                                         location=self.soap_url,
                                         plugins=[ServiceMessagePlugin()],
                                         cache=suds.cache.NoCache())
        self._service_content = None

    @staticmethod
    def build_base_url(protocol, host, port):
        proto_str = '%s://' % protocol
        host_str = '[%s]' % host if netaddr.valid_ipv6(host) else host
        port_str = '' if port is None else ':%d' % port
        return proto_str + host_str + port_str

    @staticmethod
    def _retrieve_properties_ex_fault_checker(response):
        """Checks the RetrievePropertiesEx API response for errors.

        Certain faults are sent in the SOAP body as a property of missingSet.
        This method raises VimFaultException when a fault is found in the
        response.

        :param response: response from RetrievePropertiesEx API call
        :raises: VimFaultException
        """
        fault_list = []
        details = {}
        if not response:
            # This is the case when the session has timed out. ESX SOAP
            # server sends an empty RetrievePropertiesExResponse. Normally
            # missingSet in the response objects has the specifics about
            # the error, but that's not the case with a timed out idle
            # session. It is as bad as a terminated session for we cannot
            # use the session. Therefore setting fault to NotAuthenticated
            # fault.
            LOG.debug("RetrievePropertiesEx API response is empty; setting "
                      "fault to %s.",
                      exceptions.NOT_AUTHENTICATED)
            fault_list = [exceptions.NOT_AUTHENTICATED]
        else:
            for obj_cont in response.objects:
                if hasattr(obj_cont, 'missingSet'):
                    for missing_elem in obj_cont.missingSet:
                        f_type = missing_elem.fault.fault
                        f_name = f_type.__class__.__name__
                        fault_list.append(f_name)
                        if f_name == exceptions.NO_PERMISSION:
                            details['object'] = f_type.object.value
                            details['privilegeId'] = f_type.privilegeId

        if fault_list:
            fault_string = _("Error occurred while calling "
                             "RetrievePropertiesEx.")
            raise exceptions.VimFaultException(fault_list,
                                               fault_string,
                                               details=details)

    @property
    def service_content(self):
        if self._service_content is None:
            self._service_content = self.retrieve_service_content()
        return self._service_content

    def get_http_cookie(self):
        """Return the vCenter session cookie."""
        cookies = self.client.options.transport.cookiejar
        for cookie in cookies:
            if cookie.name.lower() == 'vmware_soap_session':
                return cookie.value

    def __getattr__(self, attr_name):
        """Returns the method to invoke API identified by param attr_name."""

        def request_handler(managed_object, **kwargs):
            """Handler for vSphere API calls.

            Invokes the API and parses the response for fault checking and
            other errors.

            :param managed_object: managed object reference argument of the
                                   API call
            :param kwargs: keyword arguments of the API call
            :returns: response of the API call
            :raises: VimException, VimFaultException, VimAttributeException,
                     VimSessionOverLoadException, VimConnectionException
            """
            try:
                if isinstance(managed_object, str):
                    # For strings, use string value for value and type
                    # of the managed object.
                    managed_object = vim_util.get_moref(managed_object,
                                                        managed_object)
                if managed_object is None:
                    return
                request = getattr(self.client.service, attr_name)
                response = request(managed_object, **kwargs)
                if (attr_name.lower() == 'retrievepropertiesex'):
                    Service._retrieve_properties_ex_fault_checker(response)
                return response
            except exceptions.VimFaultException:
                # Catch the VimFaultException that is raised by the fault
                # check of the SOAP response.
                raise

            except suds.WebFault as excep:
                doc = excep.document
                fault_string = doc.childAtPath("/Envelope/Body/Fault/"
                                               "faultstring").getText()
                detail = doc.childAtPath('/Envelope/Body/Fault/detail')
                fault_list = []
                details = {}
                if detail:
                    for fault in detail.getChildren():
                        fault_list.append(fault.get("type"))
                        for child in fault.getChildren():
                            details[child.name] = child.getText()
                raise exceptions.VimFaultException(fault_list, fault_string,
                                                   excep, details)

            except AttributeError as excep:
                raise exceptions.VimAttributeException(
                    _("No such SOAP method %s.") % attr_name, excep)

            except (httplib.CannotSendRequest,
                    httplib.ResponseNotReady,
                    httplib.CannotSendHeader) as excep:
                raise exceptions.VimSessionOverLoadException(
                    _("httplib error in %s.") % attr_name, excep)

            except (urllib2.URLError, urllib2.HTTPError) as excep:
                raise exceptions.VimConnectionException(
                    _("urllib2 error in %s.") % attr_name, excep)

            except Exception as excep:
                # TODO(vbala) should catch specific exceptions and raise
                # appropriate VimExceptions.

                # Socket errors which need special handling; some of these
                # might be caused by server API call overload.
                if (six.text_type(excep).find(ADDRESS_IN_USE_ERROR) != -1 or
                        six.text_type(excep).find(CONN_ABORT_ERROR)) != -1:
                    raise exceptions.VimSessionOverLoadException(
                        _("Socket error in %s.") % attr_name, excep)
                # Type error which needs special handling; it might be caused
                # by server API call overload.
                elif six.text_type(excep).find(RESP_NOT_XML_ERROR) != -1:
                    raise exceptions.VimSessionOverLoadException(
                        _("Type error in %s.") % attr_name, excep)
                else:
                    raise exceptions.VimException(
                        _("Exception in %s.") % attr_name, excep)
        return request_handler

    def __repr__(self):
        return "vSphere object"

    def __str__(self):
        return "vSphere object"
