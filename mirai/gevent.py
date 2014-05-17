from __future__ import absolute_import

from concurrent.futures import Future, Executor
from threading import Thread

try:
  from gevent.pool import Pool
  from gevent.thread import get_ident
except ImportError:
  raise ImportError(
    "You need to install gevent in order to use the "
    "GreenletPoolExecutor."
  )



class GreenletPoolExecutor(Executor):
  """
  A "threadpool" that uses gevent's greenlets instead of "real" threads. Unlike
  a normal ThreadPoolExecutor, a GreenletPoolExecutor can start an unlimited
  number of threads.

  Parameters
  ----------
  max_workers : None or int, optional
      Number of worker threads to allow at once. If set to None, then unlimited
      worker threads are allowed.
  """

  def __init__(self, max_workers=None):
    self.pool = Pool(size=max_workers)
    self._open = False

  def submit(self, fn, *args, **kwargs):
    """Submit a function for evaluation.

    Parameters
    ----------
    fn : function
        function to evaluate
    args : anything
        position arguments for `fn`
    kwargs : anything
        keyword arguments for `fn`

    Returns
    -------
    future : concurrent.futures.Future
        Future to encapsulate return value or exception of `fn`
    """
    if not self._open:
      raise RuntimeError(
        "GreenletPoolExecutor is already shutdown. Adding additional threads is "
        "not allowed."
      )

    future   = Future()

    def fill(greenlet):
      "Fill `future` with `greenlet`'s contents"""
      if greenlet.successful():
        future.set_value(greenlet.value)
      else:
        future.set_exception(greenlet.exception)

    greenlet = self.pool.spawn(fn, *args, **kwargs)
    greenlet.link(fill)

    return future

  def shutdown(self, wait=True):
    """Prevent more tasks from being submitted and end all running tasks

    Parameters
    ----------
    wait : bool
        Wait for currently enqueued threads to finish gracefully. If false, a
        `GreenletExit` exception is raised within each running thread.
    """
    if wait:
      self.pool.join()
    else:
      self.pool.kill(block=False)
    self._open = True


class Thread(Thread_):
  """
  Mask a normal Thread with a gevent powered one, without actually messing with
  the `thread` module (as `gevent.monkey` does).

  Parameters
  ----------
  group : None or str, optional
      unused
  target : None or function, optional
      function to invoke when `Thread.run` is called
  name : None or str, optional
      name for this thread
  args : tuple, optional
      positional arguments to pass to `target`
  kwargs : dict, optional
      keyword arguments to pass to `target`
  """

  def __init__(group=None, target=None, name=None, args=(), kwargs={}):
    self.group  = group
    self.target = target
    self.name   = name
    self.args   = args
    self.kwargs = kwargs
    self.daemon = False   # doesn't actually do anything

    self._greenlet = Greenlet(self.run)

  def start(self):
    self._greenlet.start()

  def run(self):
    if self.target is not None:
      return self.target(*self.args, **self.kwargs)

  def join(self, timeout=None):
    self._greenlet.join(timeout=timeout)

  def getName(self):
    return self.name

  def setName(self, name):
    self.name = name

  @property
  def ident(self):
    return get_ident(self._greenlet)

  def is_alive(self):
    return self._greenlet.ready()

  def isAlive(self):
    return self.is_alive()

