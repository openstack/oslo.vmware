========
Usage
========

Example usage of getting a handle to a vSphere session and retrieving all the
ESX hosts in a server::

    from oslo_vmware import api
    from oslo_vmware import vim_util

    # Get a handle to a vSphere API session
    session = api.VMwareAPISession(
        '10.1.2.3',      # vSphere host endpoint
        'administrator', # vSphere username
        'password',      # vSphere password
        10,              # Number of retries for connection failures in tasks
        0.1              # Poll interval for async tasks (in seconds)
    )

    # Example call to get all the managed objects of type "HostSystem"
    # on the server.
    result = session.invoke_api(
        vim_util,                           # Handle to VIM utility module
        'get_objects',                      # API method name to invoke
        session.vim, 'HostSystem', 100)     # Params to API method (*args)
