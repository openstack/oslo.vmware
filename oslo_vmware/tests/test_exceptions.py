# Copyright (c) 2015 VMware, Inc.
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
Unit tests for exceptions module.
"""

from oslo_vmware._i18n import _
from oslo_vmware import exceptions
from oslo_vmware.tests import base


class ExceptionsTest(base.TestCase):

    def test_exception_summary_exception_as_list(self):
        # assert that if a list is fed to the VimException object
        # that it will error.
        self.assertRaises(ValueError,
                          exceptions.VimException,
                          [], ValueError('foo'))

    def test_exception_summary_string(self):
        e = exceptions.VimException(_("string"), ValueError("foo"))
        string = str(e)
        self.assertEqual("string\nCause: foo", string)

    def test_vim_fault_exception_string(self):
        self.assertRaises(ValueError,
                          exceptions.VimFaultException,
                          "bad", ValueError("argument"))

    def test_vim_fault_exception(self):
        vfe = exceptions.VimFaultException([ValueError("example")], _("cause"))
        string = str(vfe)
        self.assertEqual("cause\nFaults: [ValueError('example',)]", string)

    def test_vim_fault_exception_with_cause_and_details(self):
        vfe = exceptions.VimFaultException([ValueError("example")],
                                           "MyMessage",
                                           "FooBar",
                                           {'foo': 'bar'})
        string = str(vfe)
        self.assertEqual("MyMessage\n"
                         "Cause: FooBar\n"
                         "Faults: [ValueError('example',)]\n"
                         "Details: {'foo': 'bar'}",
                         string)

    def _create_subclass_exception(self):
        class VimSubClass(exceptions.VMwareDriverException):
            pass
        return VimSubClass

    def test_register_fault_class(self):
        exc = self._create_subclass_exception()
        exceptions.register_fault_class('ValueError', exc)
        self.assertEqual(exc, exceptions.get_fault_class('ValueError'))

    def test_register_fault_class_override(self):
        exc = self._create_subclass_exception()
        exceptions.register_fault_class(exceptions.ALREADY_EXISTS, exc)
        self.assertEqual(exc,
                         exceptions.get_fault_class(exceptions.ALREADY_EXISTS))

    def test_register_fault_class_invalid(self):
        self.assertRaises(TypeError,
                          exceptions.register_fault_class,
                          'ValueError', ValueError)
