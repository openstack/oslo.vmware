# Copyright (c) 2016 VMware, Inc.
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

from lxml import etree  # nosec (bandit bug 1582516)


def _get_vmdk_name_from_ovf(root):
    ns_ovf = "{{{0}}}".format(root.nsmap["ovf"])
    disk = root.find("./{0}DiskSection/{0}Disk".format(ns_ovf))
    file_id = disk.get("{0}fileRef".format(ns_ovf))
    f = root.find('./{0}References/{0}File[@{0}id="{1}"]'.format(ns_ovf,
                                                                 file_id))
    return f.get("{0}href".format(ns_ovf))


def get_vmdk_name_from_ovf(ovf_handle):
    """Get the vmdk name from the given ovf descriptor."""
    return _get_vmdk_name_from_ovf(etree.parse(ovf_handle).getroot())
