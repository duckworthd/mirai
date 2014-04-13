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


class Future(object):

  EXECUTOR = futures.ThreadPoolExecutor(max_workers=10)

  def __init__(self, future=None):
    self._future = future or futures.Future()

  def andthen(self, fn):
    return self.flatmap(fn)

  def __call__(self, duration=None):
    return self.get(duration)

  def ensure(self, fn):
    self.onsuccess(fn).onfailure(fn)

  def filter(self, fn):
    result = Future()

    def filter(v):
      def check(b):
        if b: result.setvalue(v)
        else: result.setexception(FutureError("Value was filtered out"))

      (
        Filter(self.EXECUTOR.submit(fn, v))
        .onsuccess(check)
        .onfailure(result.setexception)
      )

    self.EXECUTOR.submit(filter)
    return result

  def flatmap(self, fn):
    result = Future()

    def populate(v):
      (
        Future(self.EXECUTOR.submit(fn, v))
        .onsuccess(lambda fut: fut.onsuccess(result.setvalue))
        .onfailure(lambda fut: fut.onfailure(result.setexception))
      )

    self.onsuccess(populate)
    self.onfailure(result.setexception)

    return result
  def foreach(self, fn):
    self.onsuccess(fn)

  def get(self, timeout=None):
    return self._future.result(timeout)

  def getorelse(self, default, timeout=None):
    try:
      return self.get(timeout)
    except Exception as e:
      return default

  def handle(self, fn):
    return self.rescue(fn)

  def isdefined(self):
    return self._future.done()

  def isfailure(self):
    v = self.issuccess()
    if v is None : return None
    else         : return not v

  def issuccess(self):
    if not self.isdefined():
      return None
    else:
      try:
        self.get()
        return True
      except Exception as e:
        return False

  def join(self, *others):
    return self.collect([self] + others)

  def map(self, fn):
    result = Future()

    def map(v):
      try:
        Future(self.EXECUTOR.submit(fn, v)).proxyto(result)
      except Exception as e:
        result.setexception(e)

    self.onsuccess(map)
    self.onfailure(result.setexception)

    return result

  def onfailure(self, fn):
    def onfailure(fut):
      try:
        fut.result()
      except Exception as e:
        self.EXECUTOR.submit(fn, e)

    self._future.add_done_callback(onfailure)
    return self

  def onsuccess(self, fn):
    def onsuccess(fut):
      try:
        v = fut.result()
        self.EXECUTOR.submit(fn, v)
      except Exception as e:
        pass

    self._future.add_done_callback(onsuccess)
    return self

  def or_(self, *others):
    result = Future()

    def or_():
      finished, remaining = self.select([self] + others)
      Future(finished).proxyto(result)

    self.EXECUTOR.submit(or_)
    return result

  def proxyto(self, other):
    self.onsuccess(other.setvalue).onfailure(other.setexception)

  def rescue(self, fn):
    result = Future()

    def rescue(e):
      Future(self.EXECUTOR.submit(fn, e)).proxyto(result)

    self.onsuccess(result.setvalue)
    self.onfailure(rescue)

    return result

  def respond(self, fn):

    def respond(fut):
      self.EXECUTOR.submit(fn, Future(fut))

    self.EXECUTOR.submit(respond)

  def select_(self, *others):
    return self.or_(*others)

  def setexception(self, e):
    if self.isdefined():
      raise FutureError("Future is already resolved; you cannot set its status again.")
    self._future.set_exception(e)
    return self

  def setvalue(self, val):
    if self.isdefined():
      raise FutureError("Future is already resolved; you cannot set its status again.")
    self._future.set_result(val)
    return self

  def unit(self):
    result = Future()
    (
      self
      .onsuccess(lambda v: result.setvalue(None))
      .onfailure(result.setexception)
    )
    return result

  def update(self, other):
    other.proxyto(self)

  def updateifempty(self, other):
    def setvalue(v):
      try:
        self.setvalue(v)
      except Exception as e:
        pass

    def setexception(e):
      try:
        self.setexception(e)
      except Exception as e:
        pass

    other.onsuccess(setvalue).onfailure(setexception)

  def within(self, duration):
    result = Future()

    def within():
      try:
        result.setvalue(self.get(0))
      except TimeoutError as e:
        result.setexception(e)

    threading.Timer(duration, within).start()

    return result


  # CONSTRUCTORS
  @classmethod
  def value(cls, val):
    f = cls()
    f.setvalue(val)
    return f

  @classmethod
  def wait(cls, duration):
    result = cls()

    def wait():
      try:
        time.sleep(duration)
        result.setvalue(None)
      except Exception as e:
        result.setexception(e)

    cls.EXECUTOR.submit(wait)
    return result

  @classmethod
  def exception(cls, exc):
    f = cls()
    f.setexception(exc)
    return f


  # COMBINING
  @classmethod
  def collect(cls, fs, timeout=None):
    """Convert a seq of futures to a future of a seq"""
    # create a result future, then create a task that gets all the futures'
    # values and sets it to result future's ouptut
    result = cls()

    def collect():
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
        result.setvalue([c.result() for c in complete])

    cls.EXECUTOR.submit(collect)
    return result

  @classmethod
  def join(cls, fs, timeout=None):
    result = cls()

    def join():
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

    cls.EXECUTOR.submit(join)
    return result

  @classmethod
  def select(cls, fs, timeout=None):
    result = cls()

    def select():
      try:
        _futures = [f._future for f in fs]
        complete, incomplete = futures.wait(_futures, timeout=timeout, return_when=futures.FIRST_COMPLETED)
        result.setvalue( (cls(list(complete)[0]), map(cls, incomplete)) )
      except Exception as e:
        result.setexception(e)

    cls.EXECUTOR.submit(select)
    return result
