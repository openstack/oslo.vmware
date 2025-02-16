# Copyright (c) 2017 OpenStack Foundation.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import itertools

from oslo_vmware.hacking import checks
from oslo_vmware.tests import base


class HackingTestCase(base.TestCase):
    def test_no_log_translations(self):
        for log, hint in itertools.product(checks._all_log_levels,
                                           checks._all_hints):
            bad = 'LOG.{}({}("Bad"))'.format(log, hint)
            self.assertEqual(1, len(list(checks.no_translate_logs(bad, 'f'))))
            # Catch abuses when used with a variable and not a literal
            bad = 'LOG.{}({}(msg))'.format(log, hint)
            self.assertEqual(1, len(list(checks.no_translate_logs(bad, 'f'))))
