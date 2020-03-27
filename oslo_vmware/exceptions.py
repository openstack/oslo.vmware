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

from oslo_vmware._i18n import _

LOG = logging.getLogger(__name__)

ALREADY_EXISTS = 'AlreadyExists'
CANNOT_DELETE_FILE = 'CannotDeleteFile'
DUPLICATE_NAME = 'DuplicateName'
FILE_ALREADY_EXISTS = 'FileAlreadyExists'
FILE_FAULT = 'FileFault'
FILE_LOCKED = 'FileLocked'
FILE_NOT_FOUND = 'FileNotFound'
INVALID_POWER_STATE = 'InvalidPowerState'
INVALID_PROPERTY = 'InvalidProperty'
NO_DISK_SPACE = 'NoDiskSpace'
NO_PERMISSION = 'NoPermission'
NOT_AUTHENTICATED = 'NotAuthenticated'
SECURITY_ERROR = "SecurityError"
MANAGED_OBJECT_NOT_FOUND = 'ManagedObjectNotFound'
TASK_IN_PROGRESS = 'TaskInProgress'
TOOLS_UNAVAILABLE = 'ToolsUnavailable'


class VMwareDriverException(Exception):
    """Base oslo.vmware exception

    To correctly use this class, inherit from it and define
    a 'msg_fmt' property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.

    """
    msg_fmt = _("An unknown exception occurred.")

    def __str__(self):
        return self.description

    def __init__(self, message=None, details=None, **kwargs):

        if message is not None and isinstance(message, list):
            # we need this to protect against developers using
            # this method like VimFaultException
            raise ValueError(_("exception message must not be a list"))

        if details is not None and not isinstance(details, dict):
            raise ValueError(_("details must be a dict"))

        self.kwargs = kwargs
        self.details = details
        self.cause = None

        if not message:
            try:
                message = self.msg_fmt % kwargs
            except Exception:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception('Exception in string format operation')
                for name, value in kwargs.items():
                    LOG.error("%(name)s: %(value)s",
                              {'name': name, 'value': value})
                # at least get the core message out if something happened
                message = self.msg_fmt

        self.message = message
        super(VMwareDriverException, self).__init__(message)

    @property
    def msg(self):
        return self.message

    @property
    def description(self):
        # NOTE(jecarey): self.msg and self.cause may be i18n objects
        # that do not support str or concatenation, but can be used
        # as replacement text.
        descr = str(self.msg)
        if self.cause:
            descr += '\nCause: ' + str(self.cause)
        return descr


class VimException(VMwareDriverException):
    """The base exception class for all VIM related exceptions."""

    def __init__(self, message=None, cause=None, details=None, **kwargs):
        super(VimException, self).__init__(message, details, **kwargs)
        self.cause = cause


class VimSessionOverLoadException(VMwareDriverException):
    """Thrown when there is an API call overload at the VMware server."""

    def __init__(self, message, cause=None):
        super(VimSessionOverLoadException, self).__init__(message)
        self.cause = cause


class VimConnectionException(VMwareDriverException):
    """Thrown when there is a connection problem."""

    def __init__(self, message, cause=None):
        super(VimConnectionException, self).__init__(message)
        self.cause = cause


class VimAttributeException(VMwareDriverException):
    """Thrown when a particular attribute cannot be found."""

    def __init__(self, message, cause=None):
        super(VimAttributeException, self).__init__(message)
        self.cause = cause


class VimFaultException(VimException):
    """Exception thrown when there are unrecognized VIM faults."""

    def __init__(self, fault_list, message, cause=None, details=None):
        super(VimFaultException, self).__init__(message, cause, details)
        if not isinstance(fault_list, list):
            raise ValueError(_("fault_list must be a list"))
        self.fault_list = fault_list

    @property
    def description(self):
        descr = VimException.description.fget(self)
        if self.fault_list:
            # fault_list doesn't contain non-ASCII chars, we can use str()
            descr += '\nFaults: ' + str(self.fault_list)
        if self.details:
            # details may contain non-ASCII values
            details = '{%s}' % ', '.join(["'%s': '%s'" % (k, v) for k, v in
                                          self.details.items()])
            descr += '\nDetails: ' + details
        return descr


class ImageTransferException(VMwareDriverException):
    """Thrown when there is an error during image transfer."""

    def __init__(self, message, cause=None):
        super(ImageTransferException, self).__init__(message)
        self.cause = cause


def _print_deprecation_warning(clazz):
    LOG.warning("Exception %s is deprecated, it will be removed in the "
                "next release.", clazz.__name__)


class VMwareDriverConfigurationException(VMwareDriverException):
    """Base class for all configuration exceptions.
    """
    msg_fmt = _("VMware Driver configuration fault.")

    def __init__(self, message=None, details=None, **kwargs):
        super(VMwareDriverConfigurationException, self).__init__(
            message, details, **kwargs)
        _print_deprecation_warning(self.__class__)


class UseLinkedCloneConfigurationFault(VMwareDriverConfigurationException):
    msg_fmt = _("No default value for use_linked_clone found.")


class MissingParameter(VMwareDriverException):
    msg_fmt = _("Missing parameter : %(param)s")

    def __init__(self, message=None, details=None, **kwargs):
        super(MissingParameter, self).__init__(message, details, **kwargs)
        _print_deprecation_warning(self.__class__)


class AlreadyExistsException(VimException):
    msg_fmt = _("Resource already exists.")
    code = 409


class CannotDeleteFileException(VimException):
    msg_fmt = _("Cannot delete file.")
    code = 403


class FileAlreadyExistsException(VimException):
    msg_fmt = _("File already exists.")
    code = 409


class FileFaultException(VimException):
    msg_fmt = _("File fault.")
    code = 409


class FileLockedException(VimException):
    msg_fmt = _("File locked.")
    code = 403


class FileNotFoundException(VimException):
    msg_fmt = _("File not found.")
    code = 404


class InvalidPowerStateException(VimException):
    msg_fmt = _("Invalid power state.")
    code = 409


class InvalidPropertyException(VimException):
    msg_fmt = _("Invalid property.")
    code = 400


class NoPermissionException(VimException):
    msg_fmt = _("No Permission.")
    code = 403


class NotAuthenticatedException(VimException):
    msg_fmt = _("Not Authenticated.")
    code = 403


class TaskInProgress(VimException):
    msg_fmt = _("Entity has another operation in process.")


class DuplicateName(VimException):
    msg_fmt = _("Duplicate name.")


class NoDiskSpaceException(VimException):
    msg_fmt = _("Insufficient disk space.")


class ToolsUnavailableException(VimException):
    msg_fmt = _("VMware Tools is not running.")


class ManagedObjectNotFoundException(VimException):
    msg_fmt = _("Managed object not found.")
    code = 404


# Populate the fault registry with the exceptions that have
# special treatment.
_fault_classes_registry = {
    ALREADY_EXISTS: AlreadyExistsException,
    CANNOT_DELETE_FILE: CannotDeleteFileException,
    DUPLICATE_NAME: DuplicateName,
    FILE_ALREADY_EXISTS: FileAlreadyExistsException,
    FILE_FAULT: FileFaultException,
    FILE_LOCKED: FileLockedException,
    FILE_NOT_FOUND: FileNotFoundException,
    INVALID_POWER_STATE: InvalidPowerStateException,
    INVALID_PROPERTY: InvalidPropertyException,
    MANAGED_OBJECT_NOT_FOUND: ManagedObjectNotFoundException,
    NO_DISK_SPACE: NoDiskSpaceException,
    NO_PERMISSION: NoPermissionException,
    NOT_AUTHENTICATED: NotAuthenticatedException,
    TASK_IN_PROGRESS: TaskInProgress,
    TOOLS_UNAVAILABLE: ToolsUnavailableException,
}


def get_fault_class(name):
    """Get a named subclass of VimException."""
    name = str(name)
    fault_class = _fault_classes_registry.get(name)
    if not fault_class:
        LOG.debug('Fault %s not matched.', name)
    return fault_class


def translate_fault(localized_method_fault, excep_msg=None):
    """Produce proper VimException subclass object,

    The exception is based on a vmodl.LocalizedMethodFault.

    :param excep_msg: Message to set to the exception. Defaults to
                      localizedMessage of the fault.
    """
    try:
        if not excep_msg:
            excep_msg = str(localized_method_fault.localizedMessage)
        name = localized_method_fault.fault.__class__.__name__
        fault_class = get_fault_class(name)
        if fault_class:
            ex = fault_class(excep_msg)
        else:
            ex = VimFaultException([name], excep_msg)
    except Exception as e:
        LOG.debug("Unexpected exception thrown (%s) while translating"
                  " fault (%s) with message: %s.",
                  e, localized_method_fault, excep_msg)
        ex = VimException(message=excep_msg, cause=e)

    return ex


def register_fault_class(name, exception):
    fault_class = _fault_classes_registry.get(name)
    if not issubclass(exception, VimException):
        raise TypeError(_("exception should be a subclass of "
                          "VimException"))
    if fault_class:
        LOG.debug('Overriding exception for %s', name)
    _fault_classes_registry[name] = exception
