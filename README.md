REPC
========

Redis based distributed RPC library.
The basic idea behind REPC is being able to distribute a task on multiple servers by simply launching another server without any change needed in the client.

Server Usage
--------------

    >>> from repc import RepcServer
    >>> srv = RepcServer(('localhost', 6379), 'namespace', sid=0)
    >>> srv.register(TestClass())
    >>> srv.run()

Client Usage
---------------

    >>> from repc import RepcClient
    >>> cli = RepcClient(('localhost', 6379), 'namespace')
    >>> cli.dosomething()

Namespace
----------------

Namespace is an execution context, each server and client will work inside a namespace.
A server will process requests provided only from clients from its namespace, so be sure to check that
you specified the same namespace on both your client and server.
Als be sure to check that the provided namespace does not collide with the namespace used by
another application using RepcClient or your requests might get served by the server of the other application.

Sid
-----------------

Sid is required only when instancing a server. By default the sid will be 0.
Sids are used by each server instance to keep track of the tasks that it is currently performing and recover
them after a server crash or reboot.
Be sure to always give the same sid when restarting a server so that it can recover its previously running tasks

Balancing on multiple servers
--------------------------------

To distribute across multiple servers your requests you must give the same namespace to all the servers and
a different sid to each running server.

Server API Reference
-----------------------

### register(self, obj)
  Register _obj_ as the object where methods call requests will be dispatched.
  For each method called by the client a method with the same name will be looked up on _obj_ and called.

### run(self)
  Starts serving requests

Client API Reference
-----------------------

Clients will simply expose methods with the same name of the methods exposed by the object registered
on the server with the same namespace.
