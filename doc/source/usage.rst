========
Usage
========

To use in a project::

	from oslo_vmware import api
	from oslo_vmware import vim_util

	api_session = api.VMwareAPISession('10.1.2.3', 'administrator',
	                                   'password', 10, 0.1,
	                                   create_session=False, port=443)
	result = api_session.invoke_api(vim_util, 'get_objects',
	                                api_session.vim, 'HostSystem', 100)
