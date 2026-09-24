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

from lxml import etree  # nosec: B410


def _get_vmdk_name_from_ovf(root):
    ns_ovf = "{{{}}}".format(root.nsmap["ovf"])
    disk = root.find(f"./{ns_ovf}DiskSection/{ns_ovf}Disk")
    file_id = disk.get(f"{ns_ovf}fileRef")
    f = root.find(
        f'./{ns_ovf}References/{ns_ovf}File[@{ns_ovf}id="{file_id}"]'
    )
    return f.get(f"{ns_ovf}href")


def get_vmdk_name_from_ovf(ovf_handle):
    """Get the vmdk name from the given ovf descriptor."""
    parser = etree.XMLParser(resolve_entities=False)
    return _get_vmdk_name_from_ovf(
        etree.parse(ovf_handle, parser=parser).getroot()
    )  # nosec: B320
