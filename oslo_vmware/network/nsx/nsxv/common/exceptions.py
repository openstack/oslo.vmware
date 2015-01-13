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

from oslo_utils import excutils

from oslo_vmware._i18n import _


class NsxvException(Exception):
    """Base Neutron Exception.

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = _("An unknown exception occurred.")

    def __init__(self, **kwargs):
        try:
            super(NsxvException, self).__init__(self.message % kwargs)
            self.msg = self.message % kwargs
        except Exception:
            with excutils.save_and_reraise_exception() as ctxt:
                if not self.use_fatal_exceptions():
                    ctxt.reraise = False
                    # at least get the core message out if something happened
                    super(NsxvException, self).__init__(self.message)

    def __unicode__(self):
        return unicode(self.msg)

    def use_fatal_exceptions(self):
        return False


class NsxvGeneralException(NsxvException):
    def __init__(self, message):
        self.message = message
        super(NsxvGeneralException, self).__init__()


class NsxvBadRequest(NsxvException):
    message = _('Bad %(resource)s request: %(msg)s')


class NsxvNotFound(NsxvException):
    message = _('%(resource)s not found: %(msg)s')


class NsxvApiException(NsxvException):
    message = _("An unknown exception %(status)s occurred: %(response)s.")

    def __init__(self, **kwargs):
        super(NsxvApiException, self).__init__(**kwargs)

        self.status = kwargs.get('status')
        self.header = kwargs.get('header')
        self.response = kwargs.get('response')


class ResourceRedirect(NsxvApiException):
    message = _("Resource %(uri)s has been redirected")


class RequestBad(NsxvApiException):
    message = _("Request %(uri)s is Bad, response %(response)s")


class Forbidden(NsxvApiException):
    message = _("Forbidden: %(uri)s")


class ResourceNotFound(NsxvApiException):
    message = _("Resource %(uri)s not found")


class MediaTypeUnsupport(NsxvApiException):
    message = _("Media Type %(uri)s is not supported")


class ServiceUnavailable(NsxvApiException):
    message = _("Service Unavailable: %(uri)s")


class ServiceConflict(NsxvApiException):
    message = _("Concurrent object access error: %(uri)s")
