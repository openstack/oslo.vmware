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
Exception definitions.
"""

import logging

import six

from oslo_vmware._i18n import _, _LE

LOG = logging.getLogger(__name__)

ALREADY_EXISTS = 'AlreadyExists'
CANNOT_DELETE_FILE = 'CannotDeleteFile'
FILE_ALREADY_EXISTS = 'FileAlreadyExists'
FILE_FAULT = 'FileFault'
FILE_LOCKED = 'FileLocked'
FILE_NOT_FOUND = 'FileNotFound'
INVALID_POWER_STATE = 'InvalidPowerState'
INVALID_PROPERTY = 'InvalidProperty'
NO_PERMISSION = 'NoPermission'
NOT_AUTHENTICATED = 'NotAuthenticated'
TASK_IN_PROGRESS = 'TaskInProgress'
DUPLICATE_NAME = 'DuplicateName'
SECURITY_ERROR = "SecurityError"
NO_DISK_SPACE = 'NoDiskSpace'
TOOLS_UNAVAILABLE = 'ToolsUnavailable'


class VimException(Exception):
    """The base exception class for all exceptions this library raises."""

    if six.PY2:
        __str__ = lambda self: six.text_type(self).encode('utf8')
        __unicode__ = lambda self: self.description
    else:
        __str__ = lambda self: self.description

    def __init__(self, message, cause=None):
        Exception.__init__(self)
        if isinstance(message, list):
            # we need this to protect against developers using
            # this method like VimFaultException
            raise ValueError(_("exception_summary must not be a list"))

        self.msg = message
        self.cause = cause

    @property
    def description(self):
        # NOTE(jecarey): self.msg and self.cause may be i18n objects
        # that do not support str or concatenation, but can be used
        # as replacement text.
        descr = six.text_type(self.msg)
        if self.cause:
            descr += '\nCause: ' + six.text_type(self.cause)
        return descr


class VimSessionOverLoadException(VimException):
    """Thrown when there is an API call overload at the VMware server."""
    pass


class VimConnectionException(VimException):
    """Thrown when there is a connection problem."""
    pass


class VimAttributeException(VimException):
    """Thrown when a particular attribute cannot be found."""
    pass


class VimFaultException(VimException):
    """Exception thrown when there are faults during VIM API calls."""

    def __init__(self, fault_list, message, cause=None, details=None):
        super(VimFaultException, self).__init__(message, cause)
        if not isinstance(fault_list, list):
            raise ValueError(_("fault_list must be a list"))
        if details is not None and not isinstance(details, dict):
            raise ValueError(_("details must be a dict"))
        self.fault_list = fault_list
        self.details = details

    if six.PY2:
        __unicode__ = lambda self: self.description
    else:
        __str__ = lambda self: self.description

    @property
    def description(self):
        descr = VimException.description.fget(self)
        if self.fault_list:
            # fault_list doesn't contain non-ASCII chars, we can use str()
            descr += '\nFaults: ' + str(self.fault_list)
        if self.details:
            # details may contain non-ASCII values
            details = '{%s}' % ', '.join(["'%s': '%s'" % (k, v) for k, v in
                                          six.iteritems(self.details)])
            descr += '\nDetails: ' + details
        return descr


class ImageTransferException(VimException):
    """Thrown when there is an error during image transfer."""
    pass


class VMwareDriverException(Exception):
    """Base VMware Driver Exception

    To correctly use this class, inherit from it and define
    a 'msg_fmt' property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.

    """
    msg_fmt = _("An unknown exception occurred.")

    def __init__(self, message=None, details=None, **kwargs):
        self.kwargs = kwargs
        self.details = details

        if not message:
            try:
                message = self.msg_fmt % kwargs

            except Exception:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception(_LE('Exception in string format operation'))
                for name, value in six.iteritems(kwargs):
                    LOG.error(_LE("%(name)s: %(value)s"),
                              {'name': name, 'value': value})
                # at least get the core message out if something happened
                message = self.msg_fmt

        super(VMwareDriverException, self).__init__(message)


class VMwareDriverConfigurationException(VMwareDriverException):
    """Base class for all configuration exceptions.
    """
    msg_fmt = _("VMware Driver configuration fault.")


class UseLinkedCloneConfigurationFault(VMwareDriverConfigurationException):
    msg_fmt = _("No default value for use_linked_clone found.")


class MissingParameter(VMwareDriverException):
    msg_fmt = _("Missing parameter : %(param)s")


class AlreadyExistsException(VMwareDriverException):
    msg_fmt = _("Resource already exists.")
    code = 409


class CannotDeleteFileException(VMwareDriverException):
    msg_fmt = _("Cannot delete file.")
    code = 403


class FileAlreadyExistsException(VMwareDriverException):
    msg_fmt = _("File already exists.")
    code = 409


class FileFaultException(VMwareDriverException):
    msg_fmt = _("File fault.")
    code = 409


class FileLockedException(VMwareDriverException):
    msg_fmt = _("File locked.")
    code = 403


class FileNotFoundException(VMwareDriverException):
    msg_fmt = _("File not found.")
    code = 404


class InvalidPowerStateException(VMwareDriverException):
    msg_fmt = _("Invalid power state.")
    code = 409


class InvalidPropertyException(VMwareDriverException):
    msg_fmt = _("Invalid property.")
    code = 400


class NoPermissionException(VMwareDriverException):
    msg_fmt = _("No Permission.")
    code = 403


class NotAuthenticatedException(VMwareDriverException):
    msg_fmt = _("Not Authenticated.")
    code = 403


class TaskInProgress(VMwareDriverException):
    msg_fmt = _("Entity has another operation in process.")


class DuplicateName(VMwareDriverException):
    msg_fmt = _("Duplicate name.")


class NoDiskSpaceException(VMwareDriverException):
    msg_fmt = _("Insufficient disk space.")


class ToolsUnavailableException(VMwareDriverException):
    msg_fmt = _("VMware Tools is not running.")


# Populate the fault registry with the exceptions that have
# special treatment.
_fault_classes_registry = {
    ALREADY_EXISTS: AlreadyExistsException,
    CANNOT_DELETE_FILE: CannotDeleteFileException,
    FILE_ALREADY_EXISTS: FileAlreadyExistsException,
    FILE_FAULT: FileFaultException,
    FILE_LOCKED: FileLockedException,
    FILE_NOT_FOUND: FileNotFoundException,
    INVALID_POWER_STATE: InvalidPowerStateException,
    INVALID_PROPERTY: InvalidPropertyException,
    NO_PERMISSION: NoPermissionException,
    NOT_AUTHENTICATED: NotAuthenticatedException,
    TASK_IN_PROGRESS: TaskInProgress,
    DUPLICATE_NAME: DuplicateName,
    NO_DISK_SPACE: NoDiskSpaceException,
    TOOLS_UNAVAILABLE: ToolsUnavailableException,
}


def get_fault_class(name):
    """Get a named subclass of VMwareDriverException."""
    name = str(name)
    fault_class = _fault_classes_registry.get(name)
    if not fault_class:
        LOG.debug('Fault %s not matched.', name)
        fault_class = VMwareDriverException
    return fault_class


def register_fault_class(name, exception):
    fault_class = _fault_classes_registry.get(name)
    if not issubclass(exception, VMwareDriverException):
        raise TypeError(_("exception should be a subclass of "
                          "VMwareDriverException"))
    if fault_class:
        LOG.debug('Overriding exception for %s', name)
    _fault_classes_registry[name] = exception
