from concurrent import futures
from concurrent.futures import TimeoutError
import threading
import time

# Future methods:
#   cancel()
#   cancelled()
#   running()
#   done()
#   result(timeout=None)
#   exception(timeout=None)
#   add_done_callback(fn)
#   set_result(result)
#   set_exception(exception)
#
# futures.wait(fs, timeout=None, return_when=ALL_COMPLETED)
#   (alt: FIRST_COMPLETED, FIRST_EXCEPTION)
# futures.as_completed(fs, timeout=None)
#
# Executor methods:
#   submit(fn *args, **kwargs)
#   map(fn, iterables)
#   shutdown()


class FutureError(Exception):
  pass


class AlreadyResolvedError(FutureError):
  pass


class Future(object):

  EXECUTOR = futures.ThreadPoolExecutor(max_workers=10)

  def __init__(self, future=None):
    self._future = future or futures.Future()

  def andthen(self, fn):
    """
    Apply a function with a single argument: the value this Future resolves to.
    The function must return another future.  If this Future fails, `fn` will
    not be called. Same as as `Future.flatmap`.

    Parameters
    ==========
    fn : (value,) -> Future
        Function to apply. Takes 1 positional argument. Must return a Future.

    Returns
    =======
    result : Future
        Future `fn` will return.
    """
    return self.flatmap(fn)

  def __call__(self, timeout=None):
    """
    Retrieve value of Future; block until it's ready or `timeout` seconds
    have passed. If `timeout` seconds pass, then a `TimeoutError` will
    be raised. If this Future failed, the set exception will be raised.

    Parameters
    ==========
    timeout : number or None
        Number of seconds to wait until raising a `TimeoutError`. If `None`,
        then wait indefinitely.

    Returns
    =======
    result
        Contents of this future if it resolved successfully.

    Raises
    ======
    exception
        Set exception if this future failed.
    """
    return self.get(timeout)

  def ensure(self, fn):
    """
    Ensure that no-argument function `fn` is called when this Future resolves,
    regardless of whether or not it completes successfuly.

    Parameters
    ==========
    fn : (,) -> None
        function to apply upon Future completion. takes no arguments. Return
        value ignored.

    Returns
    =======
    self : Future
    """
    def ensure(v):
      try:
        Future.call(fn)
      except Exception as e:
        pass

    return self.onsuccess(ensure).onfailure(ensure)

  def filter(self, fn):
    """
    Construct a new Future that fails if `fn` doesn't evaluate truthily when
    given `self.get()` as its only argument. If `fn` evaluates falsily, then
    the resulting Future fails with a `FutureError`.

    Parameters
    ==========
    fn : (value,) -> bool
        function used to check `self.get()`. Must return a boolean-like value.

    Returns
    =======
    result : Future
        Future whose contents are the contents of this Future if `fn` evaluates
        truth on this Future's contents.
    """
    return (
      self
      .flatmap(lambda v: Future.collect([
        Future.value(v),
        Future.call(fn, v),
      ]))
      .flatmap(lambda (v, b):
        Future.value(v) if b
        else Future.exception(FutureError("Value {} was filtered out".format(v)))
      )
    )

  def flatmap(self, fn):
    """
    Apply a function with a single argument: the value this Future resolves to.
    The function must return another future.  If this Future fails, `fn` will
    not be called.

    Parameters
    ==========
    fn : (value,) -> Future
        Function to apply. Takes 1 positional argument. Must return a Future.

    Returns
    =======
    result : Future
        Future containing return result of `fn`
    """

    result = Future()

    def populate(v):
      def setvalue(fut):
        try:
          fut.proxyto(result)
        except Exception as e:
          result.setexception(e)

      try:
        (
          Future.call(fn, v)
          .onsuccess(setvalue)
          .onfailure(result.setexception)
        )
      except Exception as e:
        result.setexception(e)

    self.onsuccess(populate)
    self.onfailure(result.setexception)

    return result
  def foreach(self, fn):
    """
    Apply a function if this Future resolves successfully. The function
    receives the contents of this Future as its only argument.

    Parameters
    ==========
    fn : (value,) -> None
        Function to apply to this Future's contents. Return value ignored.

    Returns
    =======
    None
    """
    self.onsuccess(fn)

  def get(self, timeout=None):
    """
    Retrieve value of Future; block until it's ready or `timeout` seconds
    have passed. If `timeout` seconds pass, then a `TimeoutError` will
    be raised. If this Future failed, the set exception will be raised.

    Parameters
    ==========
    timeout : number or None
        Number of seconds to wait until raising a `TimeoutError`. If `None`,
        then wait indefinitely.

    Returns
    =======
    result
        Contents of this future if it resolved successfully.

    Raises
    ======
    exception
        Set exception if this future failed.
    """
    return self._future.result(timeout)

  def getorelse(self, default):
    """
    Like `Future.get`, but instead of raising an exception when this Future
    fails, returns a default value.

    Parameters
    ==========
    default : anything
        default value to return in case of time
    """
    try:
      return self.get(timeout=0)
    except Exception as e:
      return default

  def handle(self, fn):
    """
    If this Future fails, call `fn` on the ensuing exception to obtain a
    successful value.

    Parameters
    ==========
    fn : (exception,) -> anything
        Function applied to recover from a failed exception. Its return value
        will be the value of the resulting Future.

    Returns
    =======
    result : Future
        Resulting Future returned by apply `fn` to the exception, then setting
        the return value to to `result`'s value. If this Future is already
        successful, its value is propagated onto `result`.
    """
    return self.rescue(lambda v: Future.call(fn, v))

  def isdefined(self):
    """
    Return `True` if this Future has already been resolved, successfully or
    unsuccessfully.

    Returns
    =======
    result : bool
    """
    return self._future.done()

  def isfailure(self):
    """
    Return `True` if this Future failed, `False` if it succeeded, and `None` if
    it's not yet resolved.

    Returns
    =======
    result : bool
    """
    v = self.issuccess()
    if v is None : return None
    else         : return not v

  def issuccess(self):
    """
    Return `True` if this Future succeeded, `False` if it failed, and `None` if
    it's not yet resolved.

    Returns
    =======
    result : bool
    """
    if not self.isdefined():
      return None
    else:
      try:
        self.get()
        return True
      except Exception as e:
        return False

  def join_(self, *others):
    """
    Combine values of this Future and 1 or more other Futures into a list.
    Results are in the same order `[self] + others` is in.

    Parameters
    ==========
    others : 1 or more Futures
        Futures to combine with this Future.

    Returns
    =======
    result : Future
        Future resolving to a list of containing the values of this Future and
        all other Futures. If any Future fails, `result` holds the exception in
        the one which fails soonest.
    """
    return self.collect([self] + list(others))

  def map(self, fn):
    """
    Transform this Future by applying a function to its value

    Parameters
    ==========
    fn : (value,) -> anything
        Function to apply to this Future's value on completion.

    Returns
    =======
    result : Future
        Future containing `fn` applied to this Future's value. If this Future
        fails, the exception is propagated.
    """
    result = Future()

    def map(v):
      try:
        Future.call(fn, v).proxyto(result)
      except Exception as e:
        result.setexception(e)

    self.onsuccess(map)
    self.onfailure(result.setexception)

    return result

  def onfailure(self, fn):
    """
    Apply a callback if this Future fails. Callbacks can be added after this
    Future has resolved.

    Parameters
    ==========
    fn : (exception,) -> None
        Function to call upon failure. Its only argument is the exception set
        to this Future. If this future succeeds, `fn` will not be called.

    Returns
    =======
    self : Future
    """
    def onfailure(fut):
      try:
        fut.result()
      except Exception as e:
        Future.call(fn, e)

    self._future.add_done_callback(onfailure)
    return self

  def onsuccess(self, fn):
    """
    Apply a callback if this Future succeeds. Callbacks can be added after this
    Future has resolved.

    Parameters
    ==========
    fn : (value,) -> None
        Function to call upon success. Its only argument is the value set
        to this Future. If this future fails, `fn` will not be called.

    Returns
    =======
    self : Future
    """
    def onsuccess(fut):
      try:
        Future.call(fn, fut.result())
      except Exception as e:
        pass

    self._future.add_done_callback(onsuccess)
    return self

  def or_(self, *others):
    """
    Return the first Future that finishes among this Future and one or more
    other Futures.

    Parameters
    ==========
    others : one or more Futures
        Other futures to consider.

    Returns
    =======
    result : Future
        First future that is resolved, successfully or otherwise.
    """
    result = Future()

    def or_():
      def setresult(v):
        try:
          v[0].proxyto(result)
        except Exception as e:
          result.setexception(e)

      try:
        (
          Future.select([self] + list(others))
          .onsuccess(setresult)
          .onfailure(result.setexception)
        )
      except Exception as e:
        result.setexception(e)

    self.EXECUTOR.submit(or_)
    return result

  def proxyto(self, other):
    """
    Copy the state of this Future to another.

    Parameters
    ==========
    other : Future
        Another Future to copy the state of this Future to, upon completion.

    Returns
    =======
    self : Future
    """
    self.onsuccess(other.setvalue).onfailure(other.setexception)
    return self

  def rescue(self, fn):
    """
    If this Future fails, call `fn` on the ensuing exception to recover another
    (potentially successful) Future. Same as `Future.handle`.

    Parameters
    ==========
    fn : (exception,) -> Future
        Function applied to recover from a failed exception. Must return a Future.

    Returns
    =======
    result : Future
        Resulting Future returned by apply `fn` to the exception this Future
        contains. If this Future is successful, its value is propagated onto
        `result`.
    """
    result = Future()

    def rescue(e):
      def setvalue(fut):
        try:
          fut.proxyto(result)
        except Exception as e:
          result.setexception(e)

      try:
        (
          Future.call(fn, e)
          .onsuccess(setvalue)
          .onfailure(result.setexception)
        )
      except Exception as e:
        result.setexception(e)

    self.onsuccess(result.setvalue)
    self.onfailure(rescue)

    return result

  def respond(self, fn):
    """
    Apply a function to this Future when it's resolved.

    Parameters
    ==========
    fn : (future,) -> None
        Function to apply to this Future upon completion. Return value is ignored

    Returns
    =======
    self : Future
    """
    def respond(fut):
      self.EXECUTOR.submit(fn, Future(fut))

    self._future.add_done_callback(lambda fut: fn(Future(fut)))
    return self

  def select_(self, *others):
    """
    Return the first Future that finishes among this Future and one or more
    other Futures.

    Parameters
    ==========
    others : one or more Futures
        Other futures to consider.

    Returns
    =======
    result : Future
        First future that is resolved, successfully or otherwise.
    """
    return self.or_(*others)

  def setexception(self, e):
    """
    Set the state of this Future as failed with a given Exception. State can
    only be set once; once a Future is defined, it cannot be redefined.

    Parameters
    ==========
    e : Exception

    Returns
    =======
    self : Future
    """
    if self.isdefined():
      raise AlreadyResolvedError("Future is already resolved; you cannot set its status again.")
    self._future.set_exception(e)
    return self

  def setvalue(self, val):
    """
    Set the state of this Future as successful with a given value. State can
    only be set once; once a Future is defined, it cannot be redefined.

    Parameters
    ==========
    val : value

    Returns
    =======
    self : Future
    """
    if self.isdefined():
      raise AlreadyResolvedError("Future is already resolved; you cannot set its status again.")
    self._future.set_result(val)
    return self

  def unit(self):
    """
    Convert this Future to another that disregards its result.

    Returns
    =======
    result : Future
        Future with a value of `None` if this Future succeeds. If this Future
        fails, the exception is propagated.
    """
    result = Future()
    try:
      (
        self
        .onsuccess(lambda v: result.setvalue(None))
        .onfailure(result.setexception)
      )
    except Exception as e:
      result.setexception(e)
    return result

  def update(self, other):
    """
    Populate this Future with the contents of another.

    Parameters
    ==========
    other : Future
        Future to copy

    Returns
    =======
    self : Future
    """
    other.proxyto(self)
    return self

  def updateifempty(self, other):
    """
    Like `Future.update`, but update only if this Future isn't already defined.

    Parameters
    ==========
    other : Future
        Future to copy, if necessary.

    Returns
    =======
    self : Future
    """
    def setvalue(v):
      try:
        self.setvalue(v)
      except AlreadyResolvedError as e:
        pass
      except Exception as e:
        self.setexception(e)

    def setexception(e):
      try:
        self.setexception(e)
      except AlreadyResolvedError as e_:
        pass
      except Exception as e_:
        self.setexception(e_)

    other.onsuccess(setvalue).onfailure(setexception)
    return self

  def within(self, duration):
    """
    Return a Future whose state is guaranteed to be resolved within `duration`
    seconds. If this Future completes before `duration` seconds expire, it will
    contain this Future's contents. If this Future is not resolved by then, the
    resulting Future will fail with a `TimeoutError`.

    Parameters
    ==========
    duration : number
        Number of seconds to wait before resolving a `TimeoutError`

    Returns
    =======
    result : Future
        Future guaranteed to resolve in `duration` seconds.
    """
    e = TimeoutError("Future did not finish in {} seconds".format(duration))
    return self.or_(Future.wait(duration).flatmap(lambda v: Future.exception(e)))

  # CONSTRUCTORS
  @classmethod
  def value(cls, val):
    """
    Construct a Future that is already resolved successfully to a value.

    Parameters
    ==========
    val : anything
        Value to resolve new Future to.

    Returns
    =======
    result : Future
        Future containing `val` as its value.
    """
    f = cls()
    f.setvalue(val)
    return f

  @classmethod
  def wait(cls, duration):
    """
    Construct a Future that succeeds in `duration` seconds with value `None`.

    Parameters
    ==========
    duration : number
        Number of seconds to wait before resolving a `TimeoutError`

    Returns
    =======
    result : Future
        Future that will resolve in `duration` seconds with value `None`.
    """
    result = cls()

    def wait():
      try:
        time.sleep(duration)
        result.setvalue(None)
      except Exception as e:
        result.setexception(e)

    threading.Thread(target=wait).start()
    return result

  @classmethod
  def exception(cls, exc):
    """
    Construct a Future that has already failed with a given exception.

    Parameters
    ==========
    exc : Exception
        Exception to fail new Future with

    Returns
    =======
    result : Future
        New Future that has already failed with the given exception.
    """
    f = cls()
    f.setexception(exc)
    return f


  # COMBINING
  @classmethod
  def collect(cls, fs, timeout=None):
    """
    Convert a sequence of Futures into a Future containing a sequence of
    values, one per Future in `fs`. The resulting Future resolves once all
    Futures in `fs` resolve successsfully or upon the first failure. In the
    latter case, the failing Future's exception is propagated.

    Parameters
    ==========
    fs : [Future]
        List of Futures to merge.
    timeout : number or None
        Number of seconds to wait before registering a `TimeoutError` with the
        resulting Future. If `None`, wait indefinitely.

    Returns
    =======
    result : Future
        Future containing values of all Futures in `fs`. If any Future in `fs`
        fails, `result` fails with the same exception. If `timeout` seconds
        pass before all Futures in `fs` resolve, `result` fails with a
      `TimeoutError`.
    """
    # create a result future, then create a task that gets all the futures'
    # values and sets it to result future's ouptut
    result = cls()

    def collect():
      try:
        _futures = [f._future for f in fs]
        complete, incomplete = futures.wait(_futures, timeout=timeout, return_when=futures.FIRST_EXCEPTION)

        # 1 or more finished with failures
        failed = [c for c in complete if cls(c).isfailure()]
        if len(failed) > 0:
          cls(failed[0]).onfailure(result.setexception)

        # didn't finish in time
        elif len(incomplete) > 0:
          m, n = len(complete), len(incomplete)
          result.setexception(TimeoutError(
            "{} of {} futures failed to complete in {} seconds."
            .format(n, n+m, timeout)
          ))

        # all futures succeeded
        else:
          result.setvalue([f.get(timeout=0) for f in fs])

      except Exception as e:
        result.setexception(e)

    cls.EXECUTOR.submit(collect)
    return result

  @classmethod
  def join(cls, fs, timeout=None):
    """
    Construct a Future that resolves when all Futures in `fs` have resolved. If
    any Future in `fs` fails, the error is propagated into the resulting
    Future. If `timeout` seconds pass before all Futures have resolved, the
    resulting Future fails with a `TimeoutError`.

    Parameters
    ==========
    fs : [Future]
        List of Futures to merge.
    timeout : number or None
        Number of seconds to wait before registering a `TimeoutError` with the
        resulting Future. If `None`, wait indefinitely.

    Returns
    =======
    result : Future
        Future containing None if all Futures in `fs` succeed, the exception of
        the first failing Future in `fs`, or a `TimeoutError` if `timeout`
        seconds pass before all Futures in `fs` resolve.
    """
    result = cls()

    def join():
      try:
        _futures = [f._future for f in fs]
        complete, incomplete = futures.wait(_futures, timeout=timeout, return_when=futures.FIRST_EXCEPTION)

        # 1 or more finished with failures
        failed = [c for c in complete if cls(c).isfailure()]
        if len(failed) > 0:
          cls(failed[0]).onfailure(result.setexception)

        # didn't finish in time
        elif len(incomplete) > 0:
          m, n = len(complete), len(incomplete)
          result.setexception(TimeoutError(
            "{} of {} futures failed to complete in {} seconds."
            .format(n, n+m, timeout)
          ))

        # all good
        else:
          result.setvalue(None)

      except Exception as e:
        result.setexception(e)

    cls.EXECUTOR.submit(join)
    return result

  @classmethod
  def select(cls, fs, timeout=None):
    """
    Return a Future containing a tuple of 2 elements. The first is the first
    Future in `fs` to resolve; the second is all remaining Futures that may or
    may not be resolved yet. If `timeout` seconds pass before any Future
    resolves, the resulting Future fails with a `TimeoutError`. The resolved
    Future is not guaranteed to have completed successfully.

    Parameters
    ==========
    fs : [Future]
        List of Futures to merge.
    timeout : number or None
        Number of seconds to wait before registering a `TimeoutError` with the
        resulting Future. If `None`, wait indefinitely.

    Returns
    =======
    result : Future
        Future containing the first Future in `fs` to finish and all remaining
        (potentially) unresolved Futures as a tuple of 2 elements for its value
        or a `TimeoutError` for its exception.
    """
    result = cls()

    def select():
      try:
        _futures = [f._future for f in fs]
        complete, incomplete = futures.wait(_futures, timeout=timeout, return_when=futures.FIRST_COMPLETED)

        complete, incomplete = map(list, [complete, incomplete])
        complete, incomplete = complete[0], list(incomplete) + list(complete[1:])

        result.setvalue( (cls(complete), map(cls, incomplete)) )
      except Exception as e:
        result.setexception(e)

    cls.EXECUTOR.submit(select)
    return result

  @classmethod
  def call(self, fn, *args, **kwargs):
    """
    Call a function asynchronously and return a Future with its result.

    Parameters
    ==========
    fn : function
        Function to be called
    *args : arguments
    **kwargs : keyword arguments

    Returns
    =======
    result : Future
        Future containing the result of `fn(*args, **kwargs)` as its value or
        the exception thrown as its exception.
    """
    return Future(self.EXECUTOR.submit(fn, *args, **kwargs))

  @classmethod
  def executor(cls, executor=None):
    """
    Set/Get the EXECUTOR Future uses.

    Parameters
    ==========
    executor : futures.Executor or None
        If None, retrieve the current executor, otherwise, shutdown the current
        Executor object and replace it with this argument.

    Returns
    =======
    executor : Executor
        Current executor
    """
    if executor is None:
      return cls.EXECUTOR
    else:
      if cls.EXECUTOR is not None:
        cls.EXECUTOR.shutdown()
      cls.EXECUTOR = executor
      return cls.EXECUTOR
