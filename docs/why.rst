Why mirai?
==========

.. module:: mirai

Above all, :mod:`mirai` aims to make asynchronous code modular. The result of this
is code that looks not unlike synchronous code -- perhaps even cleaner. I'll
illustrate with a simple example.

A common use case for multithreading is when your code is IO-bound. For
example, the following code fetches a set of webpages within a timeout, then
ranks them according to fetch time.

.. code-block:: python
  :linenos:

  import time

  from mirai import Promise
  import requests


  def fetch(url):
    start    = time.time()
    response = requests.get(url)
    response.raise_for_status()
    return (time.time() - start, url)


  def fetch_within(url, timeout):
    return (
      Promise.call(fetch, url)
      .within(timeout)
      .handle(lambda e: (float('inf'), url))
    )


  def fetch_times(urls, timeout):
    promises = [ fetch_within(url, timeout) for url in urls ]
    return sorted(Promise.collect(promises).get())


In total, we have 24 lines. Notice that exception handling is done independent
of time calculation, and that there's no need to think about locking or queues.


Why not threading?
------------------

:mod:`threading` is Python's low-level library for multithreaded code. It's
extremely scant in its offering and requires significant attention to locking,
timing, and racing threads, obscuring the program's actual intent. The
following 48(!) lines implement equivalent logic, employing a :class:`Queue` to
pass information between threads,

.. code-block:: python
  :linenos:

  from Queue import Queue
  from threading import Thread, Timer, Lock
  import time

  import requests


  class FetchThread(Thread):

    def __init__(self, url, queue, timeout):
      super(FetchThread, self).__init__()
      self.url       = url
      self.queue     = queue
      self.timeout   = timeout
      self.lock      = Lock()
      self.submitted = False

    def run(self):
      timer = Timer(self.timeout, self._submit, args=(float('inf'),))
      timer.start()

      start = time.time()
      try:
        response = requests.get(self.url)
        response.raise_for_status()
        self._submit( time.time() - start )
      except Exception as e:
        self._submit(float('inf'))

    def _submit(self, elapsed):
      with self.lock:
        if not self.submitted:
          self.submitted = True
          self.queue.put( (elapsed, self.url) )


  def fetch_async(url, queue, timeout):
    thread = FetchThread(url, queue, timeout)
    thread.start()
    return thread


  def fetch_times(urls, timeout):
    queue = Queue()
    threads = [fetch_async(url, queue, timeout=timeout) for url in urls]
    [thread.join() for thread in threads]

    return sorted([queue.get() for url in urls])



Why not concurrent.futures?
---------------------------

:mod:`concurrent.futures` is the new asynchronous computation library added to
Python's standard library in version 3.2.  While the library offers the same
core benefits of `mirai`, it lacks the method-chaining additions that make
working with futures a breeze. The following 27 lines of code illustrate the
same logic,

.. _`PEP 3148`:  http://legacy.python.org/dev/peps/pep-3148/

.. code-block:: python
  :linenos:

  from concurrent.futures import ThreadPoolExecutor, wait
  import time

  import requests


  EXECUTOR = ThreadPoolExecutor(max_workers=10)

  def fetch_sync(url):
      start    = time.time()
      try:
        response = requests.get(url)
        response.raise_for_status()
        return (time.time() - start, url)
      except Exception as e:
        return (float('inf'), url)


  def fetch_times(urls, timeout):
    threads = [EXECUTOR.submit(fetch_sync, url) for url in urls]
    complete, incomplete = wait(threads, timeout=timeout)
    results = [future.result() for future in complete]
    result_urls = set(r[1] for r in results)
    for url in urls:
      if url not in result_urls:
        results.append( (float('inf'), url) )
    return sorted(results)




Why not multiprocessing?
------------------------

:mod:`multiprocessing` and `mirai` actually achieve different things and
actually have very little overlap. Whereas `mirai` is designed to speed up
*IO-bound* code, whereas `multiprocessing` is designed to speed up *CPU-bound*
code. If the latter sounds more like what you're looking for, **mirai cannot
help you!** as it still bound by the `GIL`_. Instead, you should take a look at
`multiprocessing`, `celery`_, or `joblib`_.

.. _celery:  http://www.celeryproject.org/
.. _joblib:  http://pythonhosted.org//joblib/
.. _GIL:     http://42bits.wordpress.com/2010/10/24/python-global-interpreter-lock-gil-explained-pycon-tech-talk/


Why not gevent?
---------------

:mod:`gevent` replaces Python's default threads with "greenlets" managed by
`libev`. The value in using `gevent` is that one can generate thousands of
greenlets and still maintain a performant asynchronous system. Used directly,
`gevent` is not dissimilar from `concurrent.futures`, but does require more
work to compose results. The following 28 lines of code illustrate.

.. code-block:: python
  :linenos:

  from gevent.monkey import patch_all; patch_all()

  import gevent
  import time

  import requests


  def fetch_sync(url):
      start    = time.time()
      try:
        response = requests.get(url)
        response.raise_for_status()
        return (time.time() - start, url)
      except Exception as e:
        return (float('inf'), url)


  def fetch_times(urls, timeout):
    threads  = [gevent.spawn(fetch_sync, url) for url in urls]
    gevent.joinall(threads, timeout=timeout)
    results = []
    for (url, thread) in zip(urls, threads):
      try:
        results.append( thread.get(timeout=0) )
      except gevent.Timeout:
        results.append( (float('inf'), url) )
    return sorted(results)


"But `gevent` uses `libev`, which is way more scalable than any of the other
alternatives, including `mirai`!" you might say, but fear not -- `mirai`  (and
`threading` and `concurrent.futures`) can use greenlets by monkey patching the
standard library at the start of your code. Simply put the following line at
the top of your main script, before any other import statements,

.. code-block:: python

  from gevent.monkey import patch_all; patch_all()

Now `mirai` has all the performance benefits of greenlets!
