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

import posixpath

import six.moves.urllib.parse as urlparse

from oslo.vmware._i18n import _
from oslo.vmware import vim_util


class Datastore(object):

    def __init__(self, ref, name, capacity=None, freespace=None):
        """Datastore object holds ref and name together for convenience.

        :param ref: a vSphere reference to a datastore
        :param name: vSphere unique name for this datastore
        :param capacity: (optional) capacity in bytes of this datastore
        :param freespace: (optional) free space in bytes of datastore
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

        self._ref = ref
        self._name = name
        self._capacity = capacity
        self._freespace = freespace

    @property
    def ref(self):
        return self._ref

    @property
    def name(self):
        return self._name

    @property
    def capacity(self):
        return self._capacity

    @property
    def freespace(self):
        return self._freespace

    def build_path(self, *paths):
        """Constructs and returns a DatastorePath.

        :param paths: list of path components, for constructing a path relative
                      to the root directory of the datastore
        :return: a DatastorePath object
        """
        return DatastorePath(self._name, *paths)

    def __str__(self):
        return '[%s]' % self._name

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
        return hosts

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
        params = {'dcPath': self._datacenter_path,
                  'dsName': self._datastore_name}
        query = urlparse.urlencode(params)
        return '%s://%s/folder/%s?%s' % (self._scheme, self._server,
                                         self.path, query)
