API
===

.. module:: mirai

This part of the documentation shows the full API reference of all public
classes and functions.

Creating Promises
-----------------

.. automethod:: Promise.value
.. automethod:: Promise.exception
.. automethod:: Promise.call
.. automethod:: Promise.wait
.. automethod:: Promise.eval

Using Promises
--------------

.. autoclass:: Promise
  :members: andthen, ensure, filter, flatmap, foreach, future, get, getorelse, handle, isdefined, isfailure, issuccess, join_, map, onfailure, onsuccess, or_, proxyto, rescue, respond, select_, setexception, setvalue, transform, unit, update, updateifempty, within

Combining Promises
------------------

.. automethod:: Promise.collect
.. automethod:: Promise.join
.. automethod:: Promise.select

Thread Management
-----------------

.. automethod:: Promise.executor
.. autoclass:: UnboundedThreadPoolExecutor
  :members: submit, shutdown

Exceptions
----------

.. autoexception:: MiraiError
   :members:

.. autoexception:: AlreadyResolvedError
   :members:

.. autoexception:: TimeoutError
   :members:
