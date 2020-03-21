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
Functions and classes for image transfer between ESX/VC & image service.
"""

import logging
import tarfile

from eventlet import timeout

from oslo_utils import units
from oslo_vmware._i18n import _
from oslo_vmware.common import loopingcall
from oslo_vmware import constants
from oslo_vmware import exceptions
from oslo_vmware import image_util
from oslo_vmware.objects import datastore as ds_obj
from oslo_vmware import rw_handles
from oslo_vmware import vim_util


LOG = logging.getLogger(__name__)

NFC_LEASE_UPDATE_PERIOD = 60  # update NFC lease every 60sec.
CHUNK_SIZE = 64 * units.Ki  # default chunk size for image transfer


def _create_progress_updater(handle):
    if isinstance(handle, rw_handles.VmdkHandle):
        updater = loopingcall.FixedIntervalLoopingCall(handle.update_progress)
        updater.start(interval=NFC_LEASE_UPDATE_PERIOD)
        return updater


def _start_transfer(read_handle, write_handle, timeout_secs):
    # read_handle/write_handle could be an NFC lease, so we need to
    # periodically update its progress
    read_updater = _create_progress_updater(read_handle)
    write_updater = _create_progress_updater(write_handle)

    timer = timeout.Timeout(timeout_secs)
    try:
        while True:
            data = read_handle.read(CHUNK_SIZE)
            if not data:
                break
            write_handle.write(data)
    except timeout.Timeout as excep:
        msg = (_('Timeout, read_handle: "%(src)s", write_handle: "%(dest)s"') %
               {'src': read_handle,
                'dest': write_handle})
        LOG.exception(msg)
        raise exceptions.ImageTransferException(msg, excep)
    except Exception as excep:
        msg = (_('Error, read_handle: "%(src)s", write_handle: "%(dest)s"') %
               {'src': read_handle,
                'dest': write_handle})
        LOG.exception(msg)
        raise exceptions.ImageTransferException(msg, excep)
    finally:
        timer.cancel()
        if read_updater:
            read_updater.stop()
        if write_updater:
            write_updater.stop()
        read_handle.close()
        write_handle.close()


def download_image(image, image_meta, session, datastore, rel_path,
                   bypass=True, timeout_secs=7200):
    """Transfer an image to a datastore.

    :param image: file-like iterator
    :param image_meta: image metadata
    :param session: VMwareAPISession object
    :param datastore: Datastore object
    :param rel_path: path where the file will be stored in the datastore
    :param bypass: if set to True, bypass vCenter to download the image
    :param timeout_secs: time in seconds to wait for the xfer to complete
    """
    image_size = int(image_meta['size'])
    method = 'PUT'
    if bypass:
        hosts = datastore.get_connected_hosts(session)
        host = ds_obj.Datastore.choose_host(hosts)
        host_name = session.invoke_api(vim_util, 'get_object_property',
                                       session.vim, host, 'name')
        ds_url = datastore.build_url(session._scheme, host_name, rel_path,
                                     constants.ESX_DATACENTER_PATH)
        cookie = ds_url.get_transfer_ticket(session, method)
        conn = ds_url.connect(method, image_size, cookie)
    else:
        ds_url = datastore.build_url(session._scheme, session._host, rel_path)
        cookie = '%s=%s' % (constants.SOAP_COOKIE_KEY,
                            session.vim.get_http_cookie().strip("\""))
        conn = ds_url.connect(method, image_size, cookie)
        conn.write = conn.send

    read_handle = rw_handles.ImageReadHandle(image)
    _start_transfer(read_handle, conn, timeout_secs)


def download_flat_image(context, timeout_secs, image_service, image_id,
                        **kwargs):
    """Download flat image from the image service to VMware server.

    :param context: image service write context
    :param timeout_secs: time in seconds to wait for the download to complete
    :param image_service: image service handle
    :param image_id: ID of the image to be downloaded
    :param kwargs: keyword arguments to configure the destination
                   file write handle
    :raises: VimConnectionException, ImageTransferException, ValueError
    """
    LOG.debug("Downloading image: %s from image service as a flat file.",
              image_id)

    # TODO(vbala) catch specific exceptions raised by download call
    read_iter = image_service.download(context, image_id)
    read_handle = rw_handles.ImageReadHandle(read_iter)
    file_size = int(kwargs.get('image_size'))
    write_handle = rw_handles.FileWriteHandle(kwargs.get('host'),
                                              kwargs.get('port'),
                                              kwargs.get('data_center_name'),
                                              kwargs.get('datastore_name'),
                                              kwargs.get('cookies'),
                                              kwargs.get('file_path'),
                                              file_size,
                                              cacerts=kwargs.get('cacerts'))
    _start_transfer(read_handle, write_handle, timeout_secs)
    LOG.debug("Downloaded image: %s from image service as a flat file.",
              image_id)


def download_file(
        read_handle, host, port, dc_name, ds_name, cookies,
        upload_file_path, file_size, cacerts, timeout_secs):
    """Download file to VMware server.

    :param read_handle: file read handle
    :param host: VMware server host name or IP address
    :param port: VMware server port number
    :param dc_name: name of the datacenter which contains the destination
                    datastore
    :param ds_name: name of the destination datastore
    :param cookies: cookies to build the cookie header while establishing
                    http connection with VMware server
    :param upload_file_path: destination datastore file path
    :param file_size: source file size
    :param cacerts: CA bundle file to use for SSL verification
    :param timeout_secs: timeout in seconds to wait for the download to
                         complete
    """
    write_handle = rw_handles.FileWriteHandle(host,
                                              port,
                                              dc_name,
                                              ds_name,
                                              cookies,
                                              upload_file_path,
                                              file_size,
                                              cacerts=cacerts)
    _start_transfer(read_handle, write_handle, timeout_secs)


def download_stream_optimized_data(context, timeout_secs, read_handle,
                                   **kwargs):
    """Download stream optimized data to VMware server.

    :param context: image service write context
    :param timeout_secs: time in seconds to wait for the download to complete
    :param read_handle: handle from which to read the image data
    :param kwargs: keyword arguments to configure the destination
                   VMDK write handle
    :returns: managed object reference of the VM created for import to VMware
              server
    :raises: VimException, VimFaultException, VimAttributeException,
             VimSessionOverLoadException, VimConnectionException,
             ImageTransferException, ValueError
    """
    file_size = int(kwargs.get('image_size'))
    write_handle = rw_handles.VmdkWriteHandle(kwargs.get('session'),
                                              kwargs.get('host'),
                                              kwargs.get('port'),
                                              kwargs.get('resource_pool'),
                                              kwargs.get('vm_folder'),
                                              kwargs.get('vm_import_spec'),
                                              file_size,
                                              kwargs.get('http_method', 'PUT'))
    _start_transfer(read_handle, write_handle, timeout_secs)
    return write_handle.get_imported_vm()


def _get_vmdk_handle(ova_handle):

    with tarfile.open(mode="r|", fileobj=ova_handle) as tar:
        vmdk_name = None
        for tar_info in tar:
            if tar_info and tar_info.name.endswith(".ovf"):
                vmdk_name = image_util.get_vmdk_name_from_ovf(
                    tar.extractfile(tar_info))
            elif vmdk_name and tar_info.name.startswith(vmdk_name):
                # Actual file name is <vmdk_name>.XXXXXXX
                return tar.extractfile(tar_info)


def download_stream_optimized_image(context, timeout_secs, image_service,
                                    image_id, **kwargs):
    """Download stream optimized image from image service to VMware server.

    :param context: image service write context
    :param timeout_secs: time in seconds to wait for the download to complete
    :param image_service: image service handle
    :param image_id: ID of the image to be downloaded
    :param kwargs: keyword arguments to configure the destination
                   VMDK write handle
    :returns: managed object reference of the VM created for import to VMware
              server
    :raises: VimException, VimFaultException, VimAttributeException,
             VimSessionOverLoadException, VimConnectionException,
             ImageTransferException, ValueError
    """
    metadata = image_service.show(context, image_id)
    container_format = metadata.get('container_format')

    LOG.debug("Downloading image: %(id)s (container: %(container)s) from image"
              " service as a stream optimized file.",
              {'id': image_id,
               'container': container_format})

    # TODO(vbala) catch specific exceptions raised by download call
    read_iter = image_service.download(context, image_id)
    read_handle = rw_handles.ImageReadHandle(read_iter)

    if container_format == 'ova':
        read_handle = _get_vmdk_handle(read_handle)
        if read_handle is None:
            raise exceptions.ImageTransferException(
                _("No vmdk found in the OVA image %s.") % image_id)

    imported_vm = download_stream_optimized_data(context, timeout_secs,
                                                 read_handle, **kwargs)

    LOG.debug("Downloaded image: %s from image service as a stream "
              "optimized file.",
              image_id)
    return imported_vm


def copy_stream_optimized_disk(
        context, timeout_secs, write_handle, **kwargs):
    """Copy virtual disk from VMware server to the given write handle.

    :param context: context
    :param timeout_secs: time in seconds to wait for the copy to complete
    :param write_handle: copy destination
    :param kwargs: keyword arguments to configure the source
                   VMDK read handle
    :raises: VimException, VimFaultException, VimAttributeException,
             VimSessionOverLoadException, VimConnectionException,
             ImageTransferException, ValueError
    """
    vmdk_file_path = kwargs.get('vmdk_file_path')
    LOG.debug("Copying virtual disk: %(vmdk_path)s to %(dest)s.",
              {'vmdk_path': vmdk_file_path,
               'dest': write_handle.name})
    file_size = kwargs.get('vmdk_size')
    read_handle = rw_handles.VmdkReadHandle(kwargs.get('session'),
                                            kwargs.get('host'),
                                            kwargs.get('port'),
                                            kwargs.get('vm'),
                                            kwargs.get('vmdk_file_path'),
                                            file_size)

    updater = loopingcall.FixedIntervalLoopingCall(read_handle.update_progress)
    try:
        updater.start(interval=NFC_LEASE_UPDATE_PERIOD)
        _start_transfer(read_handle, write_handle, timeout_secs)
    finally:
        updater.stop()
    LOG.debug("Downloaded virtual disk: %s.", vmdk_file_path)


# TODO(vbala) Remove dependency on image service provided by the client.
def upload_image(context, timeout_secs, image_service, image_id, owner_id,
                 **kwargs):
    """Upload the VM's disk file to image service.

    :param context: image service write context
    :param timeout_secs: time in seconds to wait for the upload to complete
    :param image_service: image service handle
    :param image_id: upload destination image ID
    :param kwargs: keyword arguments to configure the source
                   VMDK read handle
    :raises: VimException, VimFaultException, VimAttributeException,
             VimSessionOverLoadException, VimConnectionException,
             ImageTransferException, ValueError
    """

    LOG.debug("Uploading to image: %s.", image_id)
    file_size = kwargs.get('vmdk_size')
    read_handle = rw_handles.VmdkReadHandle(kwargs.get('session'),
                                            kwargs.get('host'),
                                            kwargs.get('port'),
                                            kwargs.get('vm'),
                                            kwargs.get('vmdk_file_path'),
                                            file_size)

    # TODO(vbala) Remove this after we delete the keyword argument 'is_public'
    # from all client code.
    if 'is_public' in kwargs:
        LOG.debug("Ignoring keyword argument 'is_public'.")

    if 'image_version' in kwargs:
        LOG.warning("The keyword argument 'image_version' is deprecated "
                    "and will be ignored in the next release.")

    image_ver = str(kwargs.get('image_version'))
    image_metadata = {'disk_format': 'vmdk',
                      'name': kwargs.get('image_name'),
                      'properties': {'vmware_image_version': image_ver,
                                     'vmware_disktype': 'streamOptimized',
                                     'owner_id': owner_id}}

    updater = loopingcall.FixedIntervalLoopingCall(read_handle.update_progress)
    store_id = kwargs.get('store_id')
    base_image_ref = kwargs.get('base_image_ref')
    try:
        updater.start(interval=NFC_LEASE_UPDATE_PERIOD)
        image_service.update(context, image_id, image_metadata,
                             data=read_handle, store_id=store_id,
                             base_image_ref=base_image_ref)
    finally:
        updater.stop()
        read_handle.close()
    LOG.debug("Uploaded image: %s.", image_id)
