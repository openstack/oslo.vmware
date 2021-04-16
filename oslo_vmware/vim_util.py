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
The VMware API utility module.
"""

import logging

from oslo_utils import timeutils
from suds import sudsobject

LOG = logging.getLogger(__name__)


def get_moref(value, type_):
    """Get managed object reference.

    :param value: value of the managed object
    :param type_: type of the managed object
    :returns: managed object reference with given value and type
    """
    moref = sudsobject.Property(value)
    moref._type = type_
    return moref


def get_moref_value(moref):
    """Get the value/id of a managed object reference

    This function accepts a string representation of a ManagedObjectReference
    like `VirtualMachine:vm-123` or only `vm-123`, but is also able to extract
    it from the actual object as returned by the API.
    """
    if isinstance(moref, str):
        # handle strings like VirtualMachine:vm-12312, but also vm-123123
        if ':' in moref:
            splits = moref.split(':')
            return splits[1]
        return moref

    # assume it's a ManagedObjectReference object as created by `get_moref()`
    # or returned by a request
    return moref.value


def get_moref_type(moref):
    """Get the type of a managed object reference

    This function accepts a string representation of a ManagedObjectReference
    like `VirtualMachine:vm-123`, but is also able to extract it from the
    actual object as returned by the API.
    """
    if isinstance(moref, str):
        # handle strings like VirtualMachine:vm-12312
        if ':' in moref:
            splits = moref.split(':')
            return splits[0]
        return None

    # assume it's a ManagedObjectReference object as created by `get_moref()`
    # or returned by a request
    return moref._type


def build_selection_spec(client_factory, name):
    """Builds the selection spec.

    :param client_factory: factory to get API input specs
    :param name: name for the selection spec
    :returns: selection spec
    """
    sel_spec = client_factory.create('ns0:SelectionSpec')
    sel_spec.name = name
    return sel_spec


def build_traversal_spec(client_factory, name, type_, path, skip, select_set):
    """Builds the traversal spec.

    :param client_factory: factory to get API input specs
    :param name: name for the traversal spec
    :param type_: type of the managed object
    :param path: property path of the managed object
    :param skip: whether or not to filter the object identified by param path
    :param select_set: set of selection specs specifying additional objects
                       to filter
    :returns: traversal spec
    """
    traversal_spec = client_factory.create('ns0:TraversalSpec')
    traversal_spec.name = name
    traversal_spec.type = type_
    traversal_spec.path = path
    traversal_spec.skip = skip
    traversal_spec.selectSet = select_set
    return traversal_spec


def build_recursive_traversal_spec(client_factory):
    """Builds recursive traversal spec to traverse managed object hierarchy.

    :param client_factory: factory to get API input specs
    :returns: recursive traversal spec
    """
    visit_folders_select_spec = build_selection_spec(client_factory,
                                                     'visitFolders')
    # Next hop from Datacenter
    dc_to_hf = build_traversal_spec(client_factory,
                                    'dc_to_hf',
                                    'Datacenter',
                                    'hostFolder',
                                    False,
                                    [visit_folders_select_spec])
    dc_to_vmf = build_traversal_spec(client_factory,
                                     'dc_to_vmf',
                                     'Datacenter',
                                     'vmFolder',
                                     False,
                                     [visit_folders_select_spec])
    dc_to_netf = build_traversal_spec(client_factory,
                                      'dc_to_netf',
                                      'Datacenter',
                                      'networkFolder',
                                      False,
                                      [visit_folders_select_spec])
    dc_to_df = build_traversal_spec(client_factory,
                                    'dc_to_df',
                                    'Datacenter',
                                    'datastoreFolder',
                                    False,
                                    [visit_folders_select_spec])

    # Next hop from HostSystem
    h_to_vm = build_traversal_spec(client_factory,
                                   'h_to_vm',
                                   'HostSystem',
                                   'vm',
                                   False,
                                   [visit_folders_select_spec])

    # Next hop from ComputeResource
    cr_to_h = build_traversal_spec(client_factory,
                                   'cr_to_h',
                                   'ComputeResource',
                                   'host',
                                   False,
                                   [])
    cr_to_ds = build_traversal_spec(client_factory,
                                    'cr_to_ds',
                                    'ComputeResource',
                                    'datastore',
                                    False,
                                    [])

    rp_to_rp_select_spec = build_selection_spec(client_factory, 'rp_to_rp')
    rp_to_vm_select_spec = build_selection_spec(client_factory, 'rp_to_vm')

    cr_to_rp = build_traversal_spec(client_factory,
                                    'cr_to_rp',
                                    'ComputeResource',
                                    'resourcePool',
                                    False,
                                    [rp_to_rp_select_spec,
                                     rp_to_vm_select_spec])

    # Next hop from ClusterComputeResource
    ccr_to_h = build_traversal_spec(client_factory,
                                    'ccr_to_h',
                                    'ClusterComputeResource',
                                    'host',
                                    False,
                                    [])
    ccr_to_ds = build_traversal_spec(client_factory,
                                     'ccr_to_ds',
                                     'ClusterComputeResource',
                                     'datastore',
                                     False,
                                     [])
    ccr_to_rp = build_traversal_spec(client_factory,
                                     'ccr_to_rp',
                                     'ClusterComputeResource',
                                     'resourcePool',
                                     False,
                                     [rp_to_rp_select_spec,
                                      rp_to_vm_select_spec])
    # Next hop from ResourcePool
    rp_to_rp = build_traversal_spec(client_factory,
                                    'rp_to_rp',
                                    'ResourcePool',
                                    'resourcePool',
                                    False,
                                    [rp_to_rp_select_spec,
                                     rp_to_vm_select_spec])
    rp_to_vm = build_traversal_spec(client_factory,
                                    'rp_to_vm',
                                    'ResourcePool',
                                    'vm',
                                    False,
                                    [rp_to_rp_select_spec,
                                     rp_to_vm_select_spec])

    # Get the assorted traversal spec which takes care of the objects to
    # be searched for from the rootFolder
    traversal_spec = build_traversal_spec(client_factory,
                                          'visitFolders',
                                          'Folder',
                                          'childEntity',
                                          False,
                                          [visit_folders_select_spec,
                                           h_to_vm,
                                           dc_to_hf,
                                           dc_to_vmf,
                                           dc_to_netf,
                                           dc_to_df,
                                           cr_to_ds,
                                           cr_to_h,
                                           cr_to_rp,
                                           ccr_to_h,
                                           ccr_to_ds,
                                           ccr_to_rp,
                                           rp_to_rp,
                                           rp_to_vm])
    return traversal_spec


def build_property_spec(client_factory, type_='VirtualMachine',
                        properties_to_collect=None, all_properties=False):
    """Builds the property spec.

    :param client_factory: factory to get API input specs
    :param type_: type of the managed object
    :param properties_to_collect: names of the managed object properties to be
                                  collected while traversal filtering
    :param all_properties: whether all properties of the managed object need
                           to be collected
    :returns: property spec
    """
    if not properties_to_collect:
        properties_to_collect = ['name']

    property_spec = client_factory.create('ns0:PropertySpec')
    property_spec.all = all_properties
    property_spec.pathSet = properties_to_collect
    property_spec.type = type_
    return property_spec


def build_object_spec(client_factory, root_folder, traversal_specs):
    """Builds the object spec.

    :param client_factory: factory to get API input specs
    :param root_folder: root folder reference; the starting point of traversal
    :param traversal_specs: filter specs required for traversal
    :returns: object spec
    """
    object_spec = client_factory.create('ns0:ObjectSpec')
    object_spec.obj = root_folder
    object_spec.skip = False
    object_spec.selectSet = traversal_specs
    return object_spec


def build_property_filter_spec(client_factory, property_specs, object_specs):
    """Builds the property filter spec.

    :param client_factory: factory to get API input specs
    :param property_specs: property specs to be collected for filtered objects
    :param object_specs: object specs to identify objects to be filtered
    :returns: property filter spec
    """
    property_filter_spec = client_factory.create('ns0:PropertyFilterSpec')
    property_filter_spec.propSet = property_specs
    property_filter_spec.objectSet = object_specs
    return property_filter_spec


def get_objects(vim, type_, max_objects, properties_to_collect=None,
                all_properties=False):
    """Get all managed object references of the given type.

    It is the caller's responsibility to continue or cancel retrieval.

    :param vim: Vim object
    :param type_: type of the managed object
    :param max_objects: maximum number of objects that should be returned in
                        a single call
    :param properties_to_collect: names of the managed object properties to be
                                  collected
    :param all_properties: whether all properties of the managed object need to
                           be collected
    :returns: all managed object references of the given type
    :raises: VimException, VimFaultException, VimAttributeException,
             VimSessionOverLoadException, VimConnectionException
    """
    if not properties_to_collect:
        properties_to_collect = ['name']

    client_factory = vim.client.factory
    recur_trav_spec = build_recursive_traversal_spec(client_factory)
    object_spec = build_object_spec(client_factory,
                                    vim.service_content.rootFolder,
                                    [recur_trav_spec])
    property_spec = build_property_spec(
        client_factory,
        type_=type_,
        properties_to_collect=properties_to_collect,
        all_properties=all_properties)
    property_filter_spec = build_property_filter_spec(client_factory,
                                                      [property_spec],
                                                      [object_spec])
    options = client_factory.create('ns0:RetrieveOptions')
    options.maxObjects = max_objects
    return vim.RetrievePropertiesEx(vim.service_content.propertyCollector,
                                    specSet=[property_filter_spec],
                                    options=options)


def get_object_properties(vim, moref, properties_to_collect, skip_op_id=False):
    """Get properties of the given managed object.

    :param vim: Vim object
    :param moref: managed object reference
    :param properties_to_collect: names of the managed object properties to be
                                  collected
    :param skip_op_id: whether to skip putting opID in the request
    :returns: properties of the given managed object
    :raises: VimException, VimFaultException, VimAttributeException,
             VimSessionOverLoadException, VimConnectionException
    """
    if moref is None:
        return None

    client_factory = vim.client.factory
    all_properties = (properties_to_collect is None or
                      len(properties_to_collect) == 0)
    property_spec = build_property_spec(
        client_factory,
        type_=get_moref_type(moref),
        properties_to_collect=properties_to_collect,
        all_properties=all_properties)
    object_spec = build_object_spec(client_factory, moref, [])
    property_filter_spec = build_property_filter_spec(client_factory,
                                                      [property_spec],
                                                      [object_spec])

    options = client_factory.create('ns0:RetrieveOptions')
    options.maxObjects = 1
    retrieve_result = vim.RetrievePropertiesEx(
        vim.service_content.propertyCollector,
        specSet=[property_filter_spec],
        options=options,
        skip_op_id=skip_op_id)
    cancel_retrieval(vim, retrieve_result)
    return retrieve_result.objects


def get_object_properties_dict(vim, moref, properties_to_collect):
    """Get properties of the given managed object as a dict.

    :param vim: Vim object
    :param moref: managed object reference
    :param properties_to_collect: names of the managed object properties to be
                                  collected
    :returns: a dict of properties of the given managed object
    :raises: VimException, VimFaultException, VimAttributeException,
             VimSessionOverLoadException, VimConnectionException
    """
    obj_contents = get_object_properties(vim, moref, properties_to_collect)
    if obj_contents is None:
        return {}
    property_dict = {}
    if hasattr(obj_contents[0], 'propSet'):
        dynamic_properties = obj_contents[0].propSet
        if dynamic_properties:
            for prop in dynamic_properties:
                property_dict[prop.name] = prop.val
    # The object may have information useful for logging
    if hasattr(obj_contents[0], 'missingSet'):
        for m in obj_contents[0].missingSet:
            LOG.warning("Unable to retrieve value for %(path)s "
                        "Reason: %(reason)s",
                        {'path': m.path,
                         'reason': m.fault.localizedMessage})
    return property_dict


def _get_token(retrieve_result):
    """Get token from result to obtain next set of results.

    :retrieve_result: Result of RetrievePropertiesEx API call
    :returns: token to obtain next set of results; None if no more results.
    """
    return getattr(retrieve_result, 'token', None)


def cancel_retrieval(vim, retrieve_result):
    """Cancels the retrieve operation if necessary.

    :param vim: Vim object
    :param retrieve_result: result of RetrievePropertiesEx API call
    :raises: VimException, VimFaultException, VimAttributeException,
             VimSessionOverLoadException, VimConnectionException
    """
    token = _get_token(retrieve_result)
    if token:
        collector = vim.service_content.propertyCollector
        vim.CancelRetrievePropertiesEx(collector, token=token)


def continue_retrieval(vim, retrieve_result):
    """Continue retrieving results, if available.

    :param vim: Vim object
    :param retrieve_result: result of RetrievePropertiesEx API call
    :raises: VimException, VimFaultException, VimAttributeException,
             VimSessionOverLoadException, VimConnectionException
    """
    token = _get_token(retrieve_result)
    if token:
        collector = vim.service_content.propertyCollector
        return vim.ContinueRetrievePropertiesEx(collector, token=token)


class WithRetrieval(object):
    """Context to retrieve results.

    This context provides an iterator to retrieve results and cancel (when
    needed) retrieve operation on __exit__.

    Example:

      with WithRetrieval(vim, retrieve_result) as objects:
          for obj in objects:
              # Use obj
    """

    def __init__(self, vim, retrieve_result):
        super(WithRetrieval, self).__init__()
        self.vim = vim
        self.retrieve_result = retrieve_result

    def __enter__(self):
        return iter(self)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.retrieve_result:
            cancel_retrieval(self.vim, self.retrieve_result)

    def __iter__(self):
        while self.retrieve_result:
            for obj in self.retrieve_result.objects:
                yield obj
            self.retrieve_result = continue_retrieval(
                self.vim, self.retrieve_result)


def get_object_property(vim, moref, property_name, skip_op_id=False):
    """Get property of the given managed object.

    :param vim: Vim object
    :param moref: managed object reference
    :param property_name: name of the property to be retrieved
    :param skip_op_id: whether to skip putting opID in the request
    :returns: property of the given managed object
    :raises: VimException, VimFaultException, VimAttributeException,
             VimSessionOverLoadException, VimConnectionException
    """
    props = get_object_properties(vim, moref, [property_name],
                                  skip_op_id=skip_op_id)
    prop_val = None
    if props:
        prop = None
        if hasattr(props[0], 'propSet'):
            # propSet will be set only if the server provides value
            # for the field
            prop = props[0].propSet
        if prop:
            prop_val = prop[0].val
    return prop_val


def find_extension(vim, key):
    """Looks for an existing extension.

    :param vim: Vim object
    :param key: the key to search for
    :returns: the data object Extension or None
    """
    extension_manager = vim.service_content.extensionManager
    return vim.FindExtension(extension_manager, extensionKey=key)


def register_extension(vim, key, type, label='OpenStack',
                       summary='OpenStack services', version='1.0'):
    """Create a new extension.

    :param vim: Vim object
    :param key: the key for the extension
    :param type: Managed entity type, as defined by the extension. This
                 matches the type field in the configuration about a
                 virtual machine or vApp
    :param label: Display label
    :param summary: Summary description
    :param version: Extension version number as a dot-separated string
    """
    extension_manager = vim.service_content.extensionManager
    client_factory = vim.client.factory
    os_ext = client_factory.create('ns0:Extension')
    os_ext.key = key
    entity_info = client_factory.create('ns0:ExtManagedEntityInfo')
    entity_info.type = type
    os_ext.managedEntityInfo = [entity_info]
    os_ext.version = version
    desc = client_factory.create('ns0:Description')
    desc.label = label
    desc.summary = summary
    os_ext.description = desc
    os_ext.lastHeartbeatTime = timeutils.utcnow().isoformat()
    vim.RegisterExtension(extension_manager, extension=os_ext)


def get_vc_version(session):
    """Return the dot-separated vCenter version string. For example, "1.2".

    :param session: vCenter soap session
    :return: vCenter version
    """
    return session.vim.service_content.about.version


def get_inventory_path(vim, entity_ref, max_objects=100):
    """Get the inventory path of a managed entity.

    :param vim: Vim object
    :param entity_ref: managed entity reference
    :param max_objects: maximum number of objects that should be returned in
                        a single call
    :return: inventory path of the entity_ref
    """
    client_factory = vim.client.factory
    property_collector = vim.service_content.propertyCollector

    prop_spec = build_property_spec(client_factory, 'ManagedEntity',
                                    ['name', 'parent'])
    select_set = build_selection_spec(client_factory, 'ParentTraversalSpec')
    select_set = build_traversal_spec(
        client_factory, 'ParentTraversalSpec', 'ManagedEntity', 'parent',
        False, [select_set])
    obj_spec = build_object_spec(client_factory, entity_ref, select_set)
    prop_filter_spec = build_property_filter_spec(client_factory,
                                                  [prop_spec], [obj_spec])
    options = client_factory.create('ns0:RetrieveOptions')
    options.maxObjects = max_objects
    retrieve_result = vim.RetrievePropertiesEx(
        property_collector,
        specSet=[prop_filter_spec],
        options=options)
    entity_name = None
    propSet = None
    path = ""
    with WithRetrieval(vim, retrieve_result) as objects:
        for obj in objects:
            if hasattr(obj, 'propSet'):
                propSet = obj.propSet
                if len(propSet) >= 1 and not entity_name:
                    entity_name = propSet[0].val
                elif len(propSet) >= 1:
                    path = '%s/%s' % (propSet[0].val, path)
    # NOTE(arnaud): slice to exclude the root folder from the result.
    if propSet is not None and len(propSet) > 0:
        path = path[len(propSet[0].val):]
    if entity_name is None:
        entity_name = ""
    return '%s%s' % (path, entity_name)


def get_http_service_request_spec(client_factory, method, uri):
    """Build a HTTP service request spec.

    :param client_factory: factory to get API input specs
    :param method: HTTP method (GET, POST, PUT)
    :param uri: target URL
    """
    http_service_request_spec = client_factory.create(
        'ns0:SessionManagerHttpServiceRequestSpec')
    http_service_request_spec.method = method
    http_service_request_spec.url = uri
    return http_service_request_spec


def get_prop_spec(client_factory, spec_type, properties):
    """Builds the Property Spec Object."""
    prop_spec = client_factory.create('ns0:PropertySpec')
    prop_spec.type = spec_type
    prop_spec.pathSet = properties
    return prop_spec


def get_obj_spec(client_factory, obj, select_set=None):
    """Builds the Object Spec object."""
    obj_spec = client_factory.create('ns0:ObjectSpec')
    obj_spec.obj = obj
    obj_spec.skip = False
    if select_set is not None:
        obj_spec.selectSet = select_set
    return obj_spec


def get_prop_filter_spec(client_factory, obj_spec, prop_spec):
    """Builds the Property Filter Spec Object."""
    prop_filter_spec = client_factory.create('ns0:PropertyFilterSpec')
    prop_filter_spec.propSet = prop_spec
    prop_filter_spec.objectSet = obj_spec
    return prop_filter_spec


def get_properties_for_a_collection_of_objects(vim, type_,
                                               obj_list, properties,
                                               max_objects=None):
    """Gets the list of properties for the collection of
    objects of the type specified.
    """
    client_factory = vim.client.factory
    if len(obj_list) == 0:
        return []
    prop_spec = get_prop_spec(client_factory, type_, properties)
    lst_obj_specs = []
    for obj in obj_list:
        lst_obj_specs.append(get_obj_spec(client_factory, obj))
    prop_filter_spec = get_prop_filter_spec(client_factory,
                                            lst_obj_specs, [prop_spec])
    options = client_factory.create('ns0:RetrieveOptions')
    options.maxObjects = max_objects if max_objects else len(obj_list)
    return vim.RetrievePropertiesEx(
        vim.service_content.propertyCollector,
        specSet=[prop_filter_spec], options=options)


def propset_dict(propset):
    """Turn a propset list into a dictionary

    PropSet is an optional attribute on ObjectContent objects
    that are returned by the VMware API.

    You can read more about these at:
    | http://pubs.vmware.com/vsphere-51/index.jsp
    |    #com.vmware.wssdk.apiref.doc/
    |        vmodl.query.PropertyCollector.ObjectContent.html

    :param propset: a property "set" from ObjectContent
    :return: dictionary representing property set
    """
    if propset is None:
        return {}

    return {prop.name: prop.val for prop in propset}


def storage_placement_spec(client_factory,
                           dsc_ref,
                           type,
                           clone_spec=None,
                           config_spec=None,
                           relocate_spec=None,
                           vm_ref=None,
                           folder=None,
                           clone_name=None,
                           res_pool_ref=None,
                           host_ref=None):
    pod_sel_spec = client_factory.create('ns0:StorageDrsPodSelectionSpec')
    pod_sel_spec.storagePod = dsc_ref

    spec = client_factory.create('ns0:StoragePlacementSpec')
    spec.podSelectionSpec = pod_sel_spec
    spec.type = type
    spec.vm = vm_ref
    spec.folder = folder
    spec.cloneSpec = clone_spec
    spec.configSpec = config_spec
    spec.relocateSpec = relocate_spec
    spec.cloneName = clone_name
    spec.resourcePool = res_pool_ref
    spec.host = host_ref
    return spec


def serialize_object(obj):
    """Convert Suds object into serializable format - a dict."""
    d = {}
    for k, v in dict(obj).items():
        if hasattr(v, '__keylist__'):
            d[k] = serialize_object(v)
        elif isinstance(v, list):
            d[k] = []
            for item in v:
                if hasattr(item, '__keylist__'):
                    d[k].append(serialize_object(item))
                else:
                    d[k].append(item)
        else:
            d[k] = v
    return d
