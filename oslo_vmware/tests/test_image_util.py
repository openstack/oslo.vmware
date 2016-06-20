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

"""
Unit tests for image_util.
"""

import os

from oslo_vmware import image_util
from oslo_vmware.tests import base


class ImageUtilTest(base.TestCase):

    def test_get_vmdk_name_from_ovf(self):
        ovf_descriptor = os.path.join(os.path.dirname(__file__), 'test.ovf')
        with open(ovf_descriptor) as f:
            vmdk_name = image_util.get_vmdk_name_from_ovf(f)
            self.assertEqual("test-disk1.vmdk", vmdk_name)
