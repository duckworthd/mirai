from threading import Thread
from concurrent.futures import Executor, ThreadPoolExecutor, Future


class UnboundedThreadPoolExecutor(Executor):
  """
  A thread pool with an infinite number of threads.

  This interface conforms to the typical `concurrent.futures.Executor`
  interface, but doesn't limit the user to a finite number of threads. In
  normal situations, this is undesirable -- too many threads, and your program
  will spend more time switching contexts than actually working!

  On the other hand, if you patch the `thread` module with `gevent`, spawning
  tens of thousands of threads is totally OK. This is where this executor comes
  in.

  Parameters
  ----------
  max_workers: None or int, optional
      Number of worker threads. If None, a new thread is created every time a
      new task is submitted. If an integer, this executor acts exactly like a
      normal `concurrent.futures.ThreadPoolExecutor`.
  """

  def __init__(self, max_workers=None):
    self._open       = True
    self.max_workers = max_workers

    if max_workers is None:
      self._pool = None
    else:
      # finite number of workers? just use a ThreadPoolExecutor
      self._pool = ThreadPoolExecutor(max_workerss)

  def submit(self, fn, *args, **kwargs):
    """Submit a new task to be executed asynchronously.

    If `self.max_workers` is an integer, then the behavior of this function
    will be identical to that of `concurrent.futures.ThreadPoolExecutor`.
    However, if it is None, then a new daemonized thread will be constructed
    and started.

    Parameters
    ----------
    fn : function-like
        function (or callable object) to execute asynchronously.
    args : list
        positional arguments to pass to `fn`.
    kwargs: dict
        keyword arguments to pass to `fn`.

    Returns
    -------
    future : concurrent.futures.Future
        Container for future result or exception
    """
    if not hasattr(fn, '__call__'):
      raise ValueError("`fn` argument isn't callable!")

    if not self._open:
      raise RuntimeError(
        "UnboundedThreadPoolExecutor is already closed. You cannot submit "
        "any more tasks."
      )

    if self._pool is not None:
      return self._pool.submit(fn, *args, **kwargs)
    else:
      # future to contain output/exception
      future = Future()
      future.set_running_or_notify_cancel()

      # run function, save output
      def populate():
        try:
          future.set_result(fn(*args, **kwargs))
        except Exception as e:
          future.set_exception(e)

      # create/start a new thread not bound to any threadpool
      thread = Thread(target=populate)
      thread.daemon = True
      thread.start()

      return future

  def shutdown(self, wait=True):
    """Shutdown this thread pool, preventing future tasks from being enqueued.

    Parameters
    ----------
    wait : bool
        Wait for all running threads to finish. Only used if this pool was
        initialized with a fixed number of workers.
    """
    self._open = False
    if self._pool is not None:
      self._pool.shutdown(wait=wait)
