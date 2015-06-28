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
        class VimSubClass(exceptions.VimException):
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

    def test_log_exception_to_string(self):
        self.assertEqual('Insufficient disk space.',
                         str(exceptions.NoDiskSpaceException()))

    def test_get_fault_class(self):
        self.assertEqual(exceptions.AlreadyExistsException,
                         exceptions.get_fault_class("AlreadyExists"))
        self.assertEqual(exceptions.CannotDeleteFileException,
                         exceptions.get_fault_class("CannotDeleteFile"))
        self.assertEqual(exceptions.FileAlreadyExistsException,
                         exceptions.get_fault_class("FileAlreadyExists"))
        self.assertEqual(exceptions.FileFaultException,
                         exceptions.get_fault_class("FileFault"))
        self.assertEqual(exceptions.FileLockedException,
                         exceptions.get_fault_class("FileLocked"))
        self.assertEqual(exceptions.FileNotFoundException,
                         exceptions.get_fault_class("FileNotFound"))
        self.assertEqual(exceptions.InvalidPowerStateException,
                         exceptions.get_fault_class("InvalidPowerState"))
        self.assertEqual(exceptions.InvalidPropertyException,
                         exceptions.get_fault_class("InvalidProperty"))
        self.assertEqual(exceptions.NoPermissionException,
                         exceptions.get_fault_class("NoPermission"))
        self.assertEqual(exceptions.NotAuthenticatedException,
                         exceptions.get_fault_class("NotAuthenticated"))
        self.assertEqual(exceptions.TaskInProgress,
                         exceptions.get_fault_class("TaskInProgress"))
        self.assertEqual(exceptions.DuplicateName,
                         exceptions.get_fault_class("DuplicateName"))
        self.assertEqual(exceptions.NoDiskSpaceException,
                         exceptions.get_fault_class("NoDiskSpace"))
        self.assertEqual(exceptions.ToolsUnavailableException,
                         exceptions.get_fault_class("ToolsUnavailable"))
        self.assertEqual(exceptions.ManagedObjectNotFoundException,
                         exceptions.get_fault_class("ManagedObjectNotFound"))
        # Test unknown fault.
        self.assertIsNone(exceptions.get_fault_class("NotAFile"))
