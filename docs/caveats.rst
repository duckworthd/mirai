Caveats
=======

.. module:: mirai

While :mod:`mirai` tries to make multithreading as painless as possible, there are a
few small cases to be mindful of.


You only have so many threads...
--------------------------------

While :mod:`mirai` does its best to hide thread management from you, the fact
remains that there are a finite number of worker threads (default: 10). If all
of those worker threads are indefinitely busy on never-ending tasks, then all
tasks queued after that won't execute!. For example,

.. code-block:: python

  from concurrent.futures import ThreadPoolExecutor
  from mirai import Promise
  import time

  def forever():
    while True:
      time.sleep(1)

  def work():
    return "I'll never run!"

  # only 5 workers available
  Promise.executor(ThreadPoolExecutor(max_workers=5))

  # these threads take up all the executor's workers
  traffic_jam = [Promise.call(forever) for i in range(5)]

  # this will block forever, as all the workers are busy
  real_work = Promise.call(work).get()


.. _waiting:

Waiting on other Promises
-------------------------

Under the hood, mirai executes all tasks registered with :meth:`Promise.call` via a
:class:`ThreadPoolExecutor` with a finite number of threads (this can be access with
:meth:`Promise.executor`). This is to ensure that there are never `too many threads`_
active at once.

.. _`too many threads`: http://www.jstorimer.com/blogs/workingwithcode/7970125-how-many-threads-is-too-many

The one cardinal sin of :mod:`mirai` is waiting upon a promise with
`Promise.get` within a currently-running promise. The reason is that the
*waiting* thread has reserved one of `mirai`'s finite number of worker
threads, and if all such worker threads are waiting upon *other* promises, then
there will be no workers for *awaited upon* promises. In other words, all
worker threads will wait forever. For example,

.. code-block:: python

  from concurrent.futures import ThreadPoolExecutor
  from mirai import Promise

  def fanout(n):
    secondaries = [Promise.call(time.sleep, 0.1 * i) for i in range(n)]
    return Promise.collect(secondaries).get()

  # only 5 workers available
  Promise.executor(ThreadPoolExecutor(max_workers=5))

  # start 5 "primary" threads. Each of these will wait on 2 "secondary" threads,
  # but due to the maximum worker limit, those secondary threads will never get
  # a chance to run. The primary threads are already taking up all the workers!
  primaries = [Promise.call(fanout, 2) for i in range(5)]

  # this will never return...
  Promise.collect(primaries).get()

The workaround for this is to use :class:`mirai.GreenletPoolExecutor`, which doesn't
have an upper bound on the number of active threads.


Combining promises isn't free
-----------------------------

:mod:`mirai` provides several functions for combining promises together --
namely, :meth:`Promise.collect`, :meth:`Promise.join`, and
:meth:`Promise.select`.  Unlike all callbacks registered with `Promise.call`,
these functions generate threads *outside of mirai's ThreadPoolExecutor*. This
is because these functions ultimately wait upon the completion of other
promises, which we already know can cause race conditions (see :ref:`waiting`).

These threads are not bound by any thread pool, thus each call creates a new
thread. If too many such threads are alive at the same time `bad things can
happen`_.

The workaround for this is to let :mod:`gevent` manage the :mod:`threading`
module. If :func:`gevent.monkey.patch_all` is called before :mod:`mirai` is
first imported, you can generate as many threads as you want, as they will be
implicitly converted to greenlets.

.. _`bad things can happen`: http://www.jstorimer.com/blogs/workingwithcode/7970125-how-many-threads-is-too-many
