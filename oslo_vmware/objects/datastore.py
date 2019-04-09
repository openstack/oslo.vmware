# Copyright (c) 2014 VMware, Inc.
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
import posixpath
import random
import re

import six.moves.http_client as httplib
import six.moves.urllib.parse as urlparse

from oslo_vmware._i18n import _
from oslo_vmware import constants
from oslo_vmware import exceptions
from oslo_vmware import vim_util

LOG = logging.getLogger(__name__)


def get_datastore_by_ref(session, ds_ref):
    """Returns a datastore object for a given reference.

    :param session: a vmware api session object
    :param ds_ref: managed object reference of a datastore
    :rtype: a datastore object
    """
    lst_properties = ["summary.type",
                      "summary.name",
                      "summary.capacity",
                      "summary.freeSpace",
                      "summary.uncommitted"]

    props = session.invoke_api(
        vim_util,
        "get_object_properties_dict",
        session.vim,
        ds_ref,
        lst_properties)
    # TODO(sabari): Instantiate with datacenter info.
    return Datastore(ds_ref, props["summary.name"],
                     capacity=props.get("summary.capacity"),
                     freespace=props.get("summary.freeSpace"),
                     uncommitted=props.get("summary.uncommitted"),
                     type=props.get("summary.type"))


def get_recommended_datastore(session, sp_spec):
    spr = session.invoke_api(
        session.vim,
        "RecommendDatastores",
        session.vim.service_content.storageResourceManager,
        storageSpec=sp_spec)
    if not hasattr(spr, 'recommendations'):
        LOG.error("Unable to find suitable datastore")
        return
    return spr.recommendations[0].key


def get_recommended_datastore_clone(session,
                                    dsc_ref,
                                    clone_spec,
                                    vm_ref,
                                    folder,
                                    name,
                                    resource_pool=None,
                                    host_ref=None):
    """Returns a key which identifies the most recommended datastore from the
    specified datastore cluster where the specified VM can be cloned to.
    """
    sp_spec = vim_util.storage_placement_spec(session.vim.client.factory,
                                              dsc_ref,
                                              'clone',
                                              clone_spec=clone_spec,
                                              vm_ref=vm_ref,
                                              folder=folder,
                                              clone_name=name,
                                              res_pool_ref=resource_pool,
                                              host_ref=host_ref)
    return get_recommended_datastore(session, sp_spec)


def get_recommended_datastore_create(session,
                                     dsc_ref,
                                     config_spec,
                                     resource_pool,
                                     folder,
                                     host_ref=None):
    """Returns SDRS recommendation key for creating a VM."""
    sp_spec = vim_util.storage_placement_spec(session.vim.client.factory,
                                              dsc_ref,
                                              'create',
                                              config_spec=config_spec,
                                              folder=folder,
                                              res_pool_ref=resource_pool,
                                              host_ref=host_ref)
    return get_recommended_datastore(session, sp_spec)


def get_dsc_ref_and_name(session, dsc_val):
    """Return reference and name of the specified datastore cluster.

    :param ds_val: datastore cluster name or datastore cluster moid
    :return: tuple of dastastore cluster moref and datastore cluster name
    """
    if re.match(r"group-p\d+", dsc_val):
        # the configured value is moid
        dsc_ref = vim_util.get_moref(dsc_val, 'StoragePod')
        try:
            dsc_name = session.invoke_api(vim_util, 'get_object_property',
                                          session.vim, dsc_ref, 'name')
            return dsc_ref, dsc_name
        except exceptions.ManagedObjectNotFoundException:
            # not a moid, try as a datastore cluster name
            pass

    result = session.invoke_api(vim_util, 'get_objects', session.vim,
                                'StoragePod', 100, ['name'])
    with vim_util.WithRetrieval(session.vim, result) as objs:
        for obj in objs:
            if not hasattr(obj, 'propSet'):
                continue
            if obj.propSet[0].val == dsc_val:
                return obj.obj, dsc_val
    return None, None


def sdrs_enabled(session, dsc_ref):
    """Check if Storage DRS is enabled for the given datastore cluster.

    :param session: VMwareAPISession object
    :param dsc_ref: datastore cluster moref
    """
    pod_sdrs_entry = session.invoke_api(vim_util,
                                        'get_object_property',
                                        session.vim,
                                        dsc_ref,
                                        'podStorageDrsEntry')
    return pod_sdrs_entry.storageDrsConfig.podConfig.enabled


class Datastore(object):

    def __init__(self, ref, name, capacity=None, freespace=None,
                 uncommitted=None, type=None, datacenter=None):
        """Datastore object holds ref and name together for convenience.

        :param ref: a vSphere reference to a datastore
        :param name: vSphere unique name for this datastore
        :param capacity: (optional) capacity in bytes of this datastore
        :param freespace: (optional) free space in bytes of datastore
        :param uncommitted: (optional) Total additional storage space
                            in bytes of datastore
        :param type: (optional) datastore type
        :param datacenter: (optional) oslo_vmware Datacenter object
        """
        if name is None:
            raise ValueError(_("Datastore name cannot be None"))
        if ref is None:
            raise ValueError(_("Datastore reference cannot be None"))
        if freespace is not None and capacity is None:
            raise ValueError(_("Invalid capacity"))
        if capacity is not None and freespace is not None:
            if capacity < freespace:
                raise ValueError(_("Capacity is smaller than free space"))

        self.ref = ref
        self.name = name
        self.capacity = capacity
        self.freespace = freespace
        self.uncommitted = uncommitted
        self.type = type
        self.datacenter = datacenter

    def build_path(self, *paths):
        """Constructs and returns a DatastorePath.

        :param paths: list of path components, for constructing a path relative
                      to the root directory of the datastore
        :return: a DatastorePath object
        """
        return DatastorePath(self.name, *paths)

    def build_url(self, scheme, server, rel_path, datacenter_name=None):
        """Constructs and returns a DatastoreURL.

        :param scheme: scheme of the URL (http, https).
        :param server: hostname or ip
        :param rel_path: relative path of the file on the datastore
        :param datacenter_name: (optional) datacenter name
        :return: a DatastoreURL object
        """
        if self.datacenter is None and datacenter_name is None:
            raise ValueError(_("datacenter must be set to build url"))
        if datacenter_name is None:
            datacenter_name = self.datacenter.name
        return DatastoreURL(scheme, server, rel_path, datacenter_name,
                            self.name)

    def __str__(self):
        return '[%s]' % self.name

    def get_summary(self, session):
        """Get datastore summary.

        :param datastore: Reference to the datastore
        :return: 'summary' property of the datastore
        """
        return session.invoke_api(vim_util, 'get_object_property',
                                  session.vim, self.ref, 'summary')

    def get_connected_hosts(self, session):
        """Get a list of usable (accessible, mounted, read-writable) hosts where
        the datastore is mounted.

        :param: session: session
        :return: list of HostSystem managed object references
        """
        hosts = []
        summary = self.get_summary(session)
        if not summary.accessible:
            return hosts
        host_mounts = session.invoke_api(vim_util, 'get_object_property',
                                         session.vim, self.ref, 'host')
        if not hasattr(host_mounts, 'DatastoreHostMount'):
            return hosts
        for host_mount in host_mounts.DatastoreHostMount:
            if self.is_datastore_mount_usable(host_mount.mountInfo):
                hosts.append(host_mount.key)
        connectables = []
        if hosts:
            host_runtimes = session.invoke_api(
                vim_util,
                'get_properties_for_a_collection_of_objects',
                session.vim, 'HostSystem', hosts, ['runtime'])
            for host_object in host_runtimes.objects:
                host_props = vim_util.propset_dict(host_object.propSet)
                host_runtime = host_props.get('runtime')
                if hasattr(host_runtime, 'inMaintenanceMode') and (
                        not host_runtime.inMaintenanceMode):
                    connectables.append(host_object.obj)
        return connectables

    @staticmethod
    def is_datastore_mount_usable(mount_info):
        """Check if a datastore is usable as per the given mount info.

        The datastore is considered to be usable for a host only if it is
        writable, mounted and accessible.

        :param mount_info: HostMountInfo data object
        :return: True if datastore is usable
        """
        writable = mount_info.accessMode == 'readWrite'
        mounted = getattr(mount_info, 'mounted', True)
        accessible = getattr(mount_info, 'accessible', False)

        return writable and mounted and accessible

    @staticmethod
    def choose_host(hosts):
        if not hosts:
            return None

        i = random.SystemRandom().randrange(0, len(hosts))
        return hosts[i]


class DatastorePath(object):

    """Class for representing a directory or file path in a vSphere datatore.

    This provides various helper methods to access components and useful
    variants of the datastore path.

    Example usage:

    DatastorePath("datastore1", "_base/foo", "foo.vmdk") creates an
    object that describes the "[datastore1] _base/foo/foo.vmdk" datastore
    file path to a virtual disk.

    Note:

    - Datastore path representations always uses forward slash as separator
      (hence the use of the posixpath module).
    - Datastore names are enclosed in square brackets.
    - Path part of datastore path is relative to the root directory
      of the datastore, and is always separated from the [ds_name] part with
      a single space.
    """

    def __init__(self, datastore_name, *paths):
        if datastore_name is None or datastore_name == '':
            raise ValueError(_("Datastore name cannot be empty"))
        self._datastore_name = datastore_name
        self._rel_path = ''
        if paths:
            if None in paths:
                raise ValueError(_("Path component cannot be None"))
            self._rel_path = posixpath.join(*paths)

    def __str__(self):
        """Full datastore path to the file or directory."""
        if self._rel_path != '':
            return "[%s] %s" % (self._datastore_name, self.rel_path)
        return "[%s]" % self._datastore_name

    @property
    def datastore(self):
        return self._datastore_name

    @property
    def parent(self):
        return DatastorePath(self.datastore, posixpath.dirname(self._rel_path))

    @property
    def basename(self):
        return posixpath.basename(self._rel_path)

    @property
    def dirname(self):
        return posixpath.dirname(self._rel_path)

    @property
    def rel_path(self):
        return self._rel_path

    def join(self, *paths):
        """Join one or more path components intelligently into a datastore path.

        If any component is an absolute path, all previous components are
        thrown away, and joining continues. The return value is the
        concatenation of the paths with exactly one slash ('/') inserted
        between components, unless p is empty.

        :return: A datastore path
        """
        if paths:
            if None in paths:
                raise ValueError(_("Path component cannot be None"))
            return DatastorePath(self.datastore, self._rel_path, *paths)
        return self

    def __eq__(self, other):
        return (isinstance(other, DatastorePath) and
                self._datastore_name == other._datastore_name and
                self._rel_path == other._rel_path)

    @classmethod
    def parse(cls, datastore_path):
        """Constructs a DatastorePath object given a datastore path string."""
        if not datastore_path:
            raise ValueError(_("Datastore path cannot be empty"))

        spl = datastore_path.split('[', 1)[1].split(']', 1)
        path = ""
        if len(spl) == 1:
            datastore_name = spl[0]
        else:
            datastore_name, path = spl
        return cls(datastore_name, path.strip())


class DatastoreURL(object):

    """Class for representing a URL to HTTP access a file in a datastore.

    This provides various helper methods to access components and useful
    variants of the datastore URL.
    """

    def __init__(self, scheme, server, path, datacenter_path, datastore_name):
        self._scheme = scheme
        self._server = server
        self._path = path
        self._datacenter_path = datacenter_path
        self._datastore_name = datastore_name
        params = {'dcPath': self._datacenter_path,
                  'dsName': self._datastore_name}
        self._query = urlparse.urlencode(params)

    @classmethod
    def urlparse(cls, url):
        scheme, server, path, params, query, fragment = urlparse.urlparse(url)
        if not query:
            path = path.split('?')
            query = path[1]
            path = path[0]
        params = urlparse.parse_qs(query)
        dc_path = params.get('dcPath')
        if dc_path is not None and len(dc_path) > 0:
            datacenter_path = dc_path[0]
        ds_name = params.get('dsName')
        if ds_name is not None and len(ds_name) > 0:
            datastore_name = ds_name[0]
        path = path[len('/folder'):]
        return cls(scheme, server, path, datacenter_path, datastore_name)

    @property
    def path(self):
        return self._path.strip('/')

    @property
    def datacenter_path(self):
        return self._datacenter_path

    @property
    def datastore_name(self):
        return self._datastore_name

    def __str__(self):
        return '%s://%s/folder/%s?%s' % (self._scheme, self._server,
                                         self.path, self._query)

    def connect(self, method, content_length, cookie):
        try:
            if self._scheme == 'http':
                conn = httplib.HTTPConnection(self._server)
            elif self._scheme == 'https':
                # TODO(browne): This needs to be changed to use python requests
                conn = httplib.HTTPSConnection(self._server)  # nosec
            else:
                excep_msg = _("Invalid scheme: %s.") % self._scheme
                LOG.error(excep_msg)
                raise ValueError(excep_msg)
            conn.putrequest(method, '/folder/%s?%s' % (self.path, self._query))
            conn.putheader('User-Agent', constants.USER_AGENT)
            conn.putheader('Content-Length', content_length)
            conn.putheader('Cookie', cookie)
            conn.endheaders()
            LOG.debug("Created HTTP connection to transfer the file with "
                      "URL = %s.", str(self))
            return conn
        except (httplib.InvalidURL, httplib.CannotSendRequest,
                httplib.CannotSendHeader) as excep:
            excep_msg = _("Error occurred while creating HTTP connection "
                          "to write to file with URL = %s.") % str(self)
        LOG.exception(excep_msg)
        raise exceptions.VimConnectionException(excep_msg, excep)

    def get_transfer_ticket(self, session, method):
        client_factory = session.vim.client.factory
        spec = vim_util.get_http_service_request_spec(client_factory, method,
                                                      str(self))
        ticket = session.invoke_api(
            session.vim,
            'AcquireGenericServiceTicket',
            session.vim.service_content.sessionManager,
            spec=spec)
        return '%s="%s"' % (constants.CGI_COOKIE_KEY, ticket.id)
