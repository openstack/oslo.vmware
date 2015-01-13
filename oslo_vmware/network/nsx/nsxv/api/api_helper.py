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

import base64

import eventlet
from oslo_serialization import jsonutils
import six

from oslo_vmware.network.nsx.nsxv.common import exceptions


httplib2 = eventlet.import_patched('httplib2')


def _xmldump(obj):
    """Sort of imporved xml creation method.

    This converts the dict to xml with following assumptions:
    keys starting with _(underscore) are to be used as attributes and not
    elements keys starting with @ are to there so that dict can be made.
    The keys are not part of any xml schema.
    """

    config = ""
    attr = ""
    if isinstance(obj, dict):
        for key, value in six.iteritems(obj):
            if (key.startswith('_')):
                attr += ' %s="%s"' % (key[1:], value)
            else:
                a, x = _xmldump(value)
                if (key.startswith('@')):
                    cfg = "%s" % (x)
                else:
                    cfg = "<%s%s>%s</%s>" % (key, a, x, key)

                config += cfg
    elif isinstance(obj, list):
        for value in obj:
            a, x = _xmldump(value)
            attr += a
            config += x
    else:
        config = obj

    return attr, config


def xmldumps(obj):
    attr, xml = _xmldump(obj)
    return xml


class NsxvApiHelper(object):
    errors = {
        303: exceptions.ResourceRedirect,
        400: exceptions.RequestBad,
        403: exceptions.Forbidden,
        404: exceptions.ResourceNotFound,
        409: exceptions.ServiceConflict,
        415: exceptions.MediaTypeUnsupport,
        503: exceptions.ServiceUnavailable
    }

    def __init__(self, address, user, password, format='json'):
        self.authToken = base64.b64encode(
            str.encode("%s:%s" % (user, password))).decode('ascii')
        self.user = user
        self.passwd = password
        self.address = address
        self.format = format
        if format == 'json':
            self.encode = jsonutils.dumps
        else:
            self.encode = xmldumps

    def _http_request(self, uri, method, body, headers):
        http = httplib2.Http()
        http.disable_ssl_certificate_validation = True
        return http.request(uri, method, body=body, headers=headers)

    def request(self, method, uri, params=None, headers=None,
                encodeparams=True):
        uri = self.address + uri
        if headers is None:
            headers = {}

        headers['Content-Type'] = 'application/' + self.format
        headers['Accept'] = 'application/' + self.format,
        headers['Authorization'] = 'Basic ' + self.authToken

        if encodeparams is True:
            body = self.encode(params) if params else None
        else:
            body = params if params else None
        header, response = self._http_request(uri, method,
                                              body=body, headers=headers)
        status = int(header['status'])
        if 200 <= status < 300:
            return header, response
        if status in self.errors:
            cls = self.errors[status]
        else:
            cls = exceptions.NsxvApiException
        raise cls(uri=uri, status=status, header=header, response=response)
