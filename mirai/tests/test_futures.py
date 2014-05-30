from concurrent.futures import ThreadPoolExecutor
import unittest

from mirai import *


class ExampleException(Exception):
  pass


class PromiseConstructorTests(object):
  """Constructing new Promises without any dependencies."""

  def test_value(self):
    self.assertEqual(Promise.value(1).get(0.5), 1)

  def test_exception(self):
    self.assertRaises(ExampleException, Promise.exception(ExampleException()).get, 0.05)

  def test_wait(self):
    self.assertIsNone(Promise.wait(0.05).get(0.5), None)

  def test_eval(self):

    def foo(a, b):
      return a+b

    # value matches
    self.assertEqual(3, Promise.eval(foo, 1, b=2).get(0))

    # exceptions subclass appropriately
    def bar():
      raise NotImplementedError("Uh oh...")

    self.assertRaises(NotImplementedError, Promise.eval(bar).get, 0)
    self.assertRaises(MiraiError, Promise.eval(bar).get, 0)

  def test_call(self):

    def foo(a, b):
      return a+b

    # value matches
    self.assertEqual(3, Promise.call(foo, 1, b=2).get(0.5))

    # exceptions subclass appropriately
    def bar():
      raise NotImplementedError("Uh oh...")

    self.assertRaises(NotImplementedError, Promise.call(bar).get, 0.5)
    self.assertRaises(MiraiError, Promise.call(bar).get, 0.5)


class PromiseBasicTests(object):
  """Core Promise functionality: setting/getting state"""

  def test_setvalue(self):
    o    = object()
    fut1 = Promise()
    fut1.setvalue(o)

    self.assertEqual(fut1.get(0.5), o)

  def test_setvalue_twice(self):
    fut1 = Promise()
    fut1.setvalue(1)

    self.assertRaises(MiraiError, fut1.setvalue, 2)

    fut2 = Promise()
    fut2.setexception(1)

    self.assertRaises(MiraiError, fut2.setvalue, 2)

  def test_setexception(self):
    e    = ExampleException()
    fut1 = Promise()
    fut1.setexception(e)

    self.assertRaises(ExampleException, fut1.get, 0.05)

  def test_setexception_twice(self):
    e    = ExampleException()
    fut1 = Promise()
    fut1.setexception(e)

    self.assertRaises(MiraiError, fut1.setexception, e)

    fut1 = Promise()
    fut1.setvalue(1)

    self.assertRaises(MiraiError, fut1.setexception, e)

  def test_get_success(self):
    fut = Promise.value(1)

    self.assertEqual(fut.get(0.5), 1)

  def test_get_exception(self):
    class VerySpecificException(ExampleException): pass
    fut = Promise.exception(VerySpecificException())

    # raises the right classs
    self.assertRaises(VerySpecificException, fut.get, 0.05)

  def test_isdefined(self):
    self.assertFalse(Promise().isdefined())
    self.assertTrue(Promise.value(1).isdefined())
    self.assertTrue(Promise.exception(ExampleException()).isdefined())

  def test_isfailure(self):
    self.assertIsNone(Promise().isfailure())
    self.assertTrue(Promise.exception(ExampleException()).isfailure())
    self.assertFalse(Promise.value(1).isfailure())

  def test_issuccess(self):
    self.assertIsNone(Promise().issuccess())
    self.assertFalse(Promise.exception(ExampleException()).issuccess())
    self.assertTrue(Promise.value(1).issuccess())

  def test_proxyto(self):
    fut1 = Promise()
    fut2 = Promise.wait(0.05).map(lambda v: 1).proxyto(fut1)

    self.assertEqual(fut1.get(0.1), 1)

    fut1 = Promise()
    fut2 = Promise.wait(0.05) \
        .flatmap(lambda v: Promise.exception(MiraiError())) \
        .proxyto(fut1)

    self.assertRaises(MiraiError, fut1.get, 0.1)


class PromiseCallbackTests(object):
  """Tests for settings callbacks"""

  def test_onsuccess_success(self):
    fut1 = Promise()
    fut2 = Promise.value(1).onsuccess(lambda v: fut1.setvalue(v))

    self.assertEqual(fut1.get(0.5), 1)

  def test_onsuccess_failure(self):
    fut1 = Promise()
    fut2 = Promise.exception(ExampleException()).onsuccess(lambda v: fut1.setvalue(v))

    Promise.join([fut2])

    self.assertRaises(TimeoutError, fut1.within(0).get, 0.05)

  def test_onfailure_exception(self):
    def uhoh(e):
      raise ExampleException("uh oh!")

    fut1 = Promise.value(0).onfailure(uhoh)

    self.assertEqual(0, fut1.get, 0.05)

  def test_onfailure_success(self):
    fut1 = Promise()
    fut2 = Promise.value(1).onfailure(lambda e: fut1.setvalue(e))

    Promise.join([fut2])

    self.assertRaises(TimeoutError, fut1.within(0).get, 0.05)

  def test_onfailure_failure(self):
    e    = ExampleException()
    fut1 = Promise()
    fut2 = Promise.exception(e).onfailure(lambda e: fut1.setvalue(e))

    self.assertEqual(fut1.get(0.5), e)

  def test_onfailure_exception(self):
    def uhoh(e):
      raise ExampleException("uh oh!")

    fut1 = Promise.exception(RuntimeError()).onfailure(uhoh)

    self.assertRaises(RuntimeError, fut1.get, 0.05)


class PromiseMapTests(object):
  """Tests for map/flatmap"""

  def test_flatmap_success(self):
    fut1 = Promise.value(1)
    fut2 = fut1.flatmap(lambda v: Promise.value(v+1))

    self.assertEqual(fut2.get(0.5), 2)

  def test_flatmap_exception(self):
    fut1 = Promise.exception(ExampleException())
    fut2 = fut1.flatmap(lambda v: v+1)

    self.assertRaises(ExampleException, fut2.get, 0.05)

  def test_flatmap_raises(self):
    def uhoh(v):
      raise ExampleException(v)

    fut1 = Promise.value(1)
    fut2 = fut1.flatmap(uhoh)

    self.assertRaises(ExampleException, fut2.get, 0.1)

  def test_flatmap_badfunc(self):
    fut1 = Promise.value(1)
    fut2 = fut1.flatmap(lambda: 1)

    self.assertRaises(TypeError, fut2.get, 0.1)

  def test_flatmap_nonpromise_return_value(self):
    fut1 = Promise.value(1)
    fut2 = fut1.flatmap(lambda v: 1)

    self.assertRaises(MiraiError, fut2.get, 0.1)

  def test_map_success(self):
    fut1 = Promise.value(1)
    fut2 = fut1.map(lambda v: v+1)

    self.assertEqual(fut2.get(0.5), 2)

  def test_map_failure(self):
    fut1 = Promise.exception(ExampleException())
    fut2 = fut1.map(lambda v: v+1)

    self.assertRaises(ExampleException, fut2.get, 0.1)

  def test_map_raises(self):
    def uhoh(v):
      raise ExampleException(v)

    fut1 = Promise.value(1)
    fut2 = fut1.map(uhoh)

    self.assertRaises(ExampleException, fut2.get, 0.1)

  def test_map_badfunc(self):
    fut1 = Promise.value(1)
    fut2 = fut1.map(lambda: 1)
    self.assertRaises(TypeError, fut2.get, 0.1)


class PromiseMiscellaneousTests(object):
  """Other Promise methods..."""

  def test_filter_success(self):
    fut1 = Promise.value(1).filter(lambda v: v != 1)
    self.assertRaises(MiraiError, fut1.get, 0.1)

    fut1 = Promise.value(1).filter(lambda v: v == 1)
    self.assertEqual(fut1.get(0.05), 1)

    fut1 = Promise.exception(MiraiError()).filter(lambda v: v == 1)
    self.assertRaises(MiraiError, fut1.get, 0.1)

  def test_filter_exception(self):
    def uhoh(v):
      raise ExampleException()

    fut1 = Promise.value(1).filter(uhoh)
    self.assertRaises(ExampleException, fut1.get, 0.05)

  def test_filter_badfunc(self):
    fut1 = Promise.value(1).filter(lambda: False)
    self.assertRaises(TypeError, fut1.get, 0.05)

  def test_rescue_success(self):
    fut1 = Promise.value("A")
    fut2 = fut1.rescue(lambda e: "B")

    self.assertEqual(fut2.get(0.5), "A")

  def test_rescue_failure(self):
    fut1 = Promise.exception(ExampleException("A"))
    fut2 = fut1.rescue(lambda e: Promise.value(e.message))

    self.assertEqual(fut2.get(0.5), "A")

  def test_rescue_nonpromise_return_value(self):
    fut1 = Promise.exception(ExampleException("A"))
    fut2 = fut1.rescue(lambda e: "uh oh")

    self.assertRaises(MiraiError, fut2.get, 0.5)

  def test_rescue_raises(self):
    def reraise(e):
      raise e

    fut1 = Promise.exception(ExampleException("A"))
    fut2 = fut1.rescue(reraise)

    self.assertRaises(ExampleException, fut2.get, 0.5)

  def test_rescue_badfunc(self):
    fut1 = Promise.exception(ExampleException("A"))
    fut2 = fut1.rescue(lambda: 1)

    self.assertRaises(TypeError, fut2.get, 0.5)

  def test_transform_success(self):
    fut1 = Promise.value(1)
    fut2 = fut1.transform(lambda p: Promise.exception(ExampleException()))

    self.assertRaises(ExampleException, fut2.get, 0.05)

  def test_transform_bandfunc(self):
    fut1 = Promise.value(1)
    fut2 = fut1.transform(lambda: Promise.value(0))

    self.assertRaises(TypeError, fut2.get, 0.05)

  def test_transform_exception(self):
    def uhoh(fut):
      raise ExampleException()
    fut1 = Promise.value(1)
    fut2 = fut1.transform(uhoh)

    self.assertRaises(ExampleException, fut2.get, 0.05)

  def test_within_success(self):
    fut1 = Promise.value("A")
    fut2 = fut1.within(0.5)

    self.assertEqual(fut2.get(0.5), "A")

  def test_within_failure(self):
    fut1 = Promise()
    fut2 = fut1.within(0)

    self.assertRaises(TimeoutError, fut2.get, 0.05)

  def test_respond_success(self):
    fut1 = Promise()
    Promise.value(1).respond(lambda f: f.proxyto(fut1))

    self.assertEqual(1, fut1.get(0.05))

    fut1 = Promise()
    Promise.exception(MiraiError()).respond(lambda f: f.proxyto(fut1))

    self.assertRaises(MiraiError, fut1.get, 0.05)

  def test_respond_exception(self):
    def uhoh(o):
      raise ExampleException()

    fut1 = Promise.value(1).respond(uhoh)

    self.assertEqual(1, fut1.get(0.05))

  def test_respond_badfunc(self):
    fut1 = Promise.value(1).respond(lambda: 1)
    self.assertEqual(1, fut1.get(0.05))

  def test_unit(self):
    self.assertIsNone(Promise.value(1).unit().get(0.05))
    self.assertRaises(ExampleException, Promise.exception(ExampleException()).unit().get, 0.05)

  def test_update(self):
    # values are propagated
    self.assertEqual(Promise().update(Promise.value(1)).get(0.01), 1)

    # exceptions are propagated
    self.assertRaises(ExampleException, Promise().update(Promise.exception(ExampleException())).get, 0.01)

    # non-Promise argument
    self.assertRaises(MiraiError, Promise().update, 1)

  def test_updateifempty(self):
    # nothing/value
    self.assertEqual(Promise().updateifempty(Promise.value(1)).get(0.01), 1)

    # value/value
    self.assertEqual(Promise().setvalue(2).updateifempty(Promise.value(1)).get(0.01), 2)

    # exception/nothing
    self.assertRaises(MiraiError,
      Promise()
      .setexception(MiraiError())
      .updateifempty(Promise())
      .get,
      0.05
    )

    # nothing/exception
    self.assertRaises(MiraiError,
      Promise()
      .updateifempty(Promise.exception(MiraiError()))
      .get,
      0.05
    )

    # exception/value
    self.assertRaises(MiraiError,
      Promise()
      .setexception(MiraiError())
      .updateifempty(Promise.value(1))
      .get,
      0.05
    )

    self.assertRaises(MiraiError, Promise().updateifempty, 1)

  def test_executor(self):
    old = Promise.executor()
    new = Promise.executor(ThreadPoolExecutor(max_workers=10))
    self.assertEqual(Promise.call(lambda v: v+1, 1).get(0.05), 2)


class PromiseThreadcountTests(object):
  """Tests involving a fixed number of threads"""

  def test_within_many_threads(self):
    # ensure's that within actually works, even when other threads are waiting.
    import time

    Promise.executor(ThreadPoolExecutor(max_workers=20))
    promises = [
      Promise.call(time.sleep, 0.05 if i < 5 else 0.75)
      for i in range(10)
    ]
    promise = (
      Promise.collect(promises)
      .within(0.1)
      .handle(lambda err: "yay")
    )
    self.assertEqual("yay", promise.get(0.5))

  def test_within_few_threads(self):
    # ensure that code doesn't lock up if I create far more threads than I have
    # workers.
    import time

    Promise.executor(ThreadPoolExecutor(max_workers=5))

    def another(i):
      # sleep a little, and a bunch of callbacks
      if i <= 0:
        return Promise.value("done")
      else:
        result = Promise.call(create, i-1)
        for i in range(i):
          result = result.map(lambda i: i)
        time.sleep(0.05)
        return result

    promises = [Promise.call(another, i) for i in range(10)]
    promise  = (
      Promise.collect(promises)
      .within(0.25)
      .handle(lambda err: "yay")
    )

    self.assertEqual("yay", promise.get(0.5))

  def test_select_few_threads(self):
    # this ensures that Promise.select won't cause a threadlock if all workers
    # are busy with the threads it's waiting on.
    Promise.executor(ThreadPoolExecutor(max_workers=2))

    promises = [
      Promise.select([
        Promise.wait(0.5).map(lambda v: v),
        Promise.wait(0.1).map(lambda v: "yay"),
      ])
      .flatmap(lambda (winner, losers): winner)
      for i in range(2)
    ]

    # shouldn't throw a timeout error
    Promise.collect(promises).get(2.5)


class PromiseAlternativeNamesTests(object):
  """Promise methods that are just alternative names for other methods"""

  def test_andthen(self):
    self.assertEqual(
        Promise.value(2).flatmap(lambda v: Promise.value(5)).get(0.5),
        Promise.value(2).andthen(lambda v: Promise.value(5)).get(0.5),
    )

  def test_call(self):
    self.assertEqual(Promise.value(1).get(0.5), Promise.value(1)())
    self.assertRaises(TimeoutError, Promise().get, 0.05)

  def test_ensure(self):
    fut1 = Promise()
    fut2 = Promise.value(2).ensure(lambda: fut1.setvalue(2))

    self.assertEqual(fut1.get(0.5), 2)

    fut1 = Promise()
    fut2 = Promise.exception(ExampleException()).ensure(lambda: fut1.setvalue(2))

    self.assertEqual(fut1.get(0.5), 2)

  def test_ensure_exception(self):
    def uhoh():
      raise ExampleException("uh oh!")

    fut1 = Promise.value(2).ensure(uhoh)

    self.assertEqual(2, fut1.get(0.05))

  def test_foreach(self):
    fut1 = Promise()
    fut2 = Promise.value(1).foreach(lambda v: fut1.setvalue(v))

    self.assertEqual(fut1.get(0.05), 1)

    fut1 = Promise()
    fut2 = Promise.exception(ExampleException()).foreach(lambda v: fut1.setvalue(v))

    self.assertRaises(TimeoutError, fut1.get, 0.05)

  def test_getorelse(self):
    self.assertEqual(Promise().getorelse(0.5), 0.5)
    self.assertEqual(Promise.value(1).getorelse(0.5), 1)
    self.assertEqual(Promise.exception(ExampleException).getorelse(0.5), 0.5)

  def test_handle(self):
    self.assertEqual(
      Promise
        .exception(ExampleException("uh oh"))
        .handle(lambda e: e.message)
        .get(0.05),
      "uh oh",
    )

    self.assertEqual(
      Promise
        .value(1)
        .handle(lambda e: e.message)
        .get(0.05),
      1,
    )

  def test_select_(self):
    self.assertEqual(
      Promise.wait(0.50).flatmap(lambda v: Promise.exception(MiraiError()))
      .select_(
        Promise.wait(0.05).map(lambda v: 2),
        Promise.wait(0.90).map(lambda v: 3),
      ).get(0.40),
      2,
    )


class PromiseMergingTests(object):
  """Methods for combining Promises together"""

  def test_collect_empty(self):
    self.assertEqual(Promise.collect([]).get(0.1), [])

  def test_collect_success(self):
    fut1 = [Promise.value(1), Promise.value(2), Promise.value(3)]
    fut2 = Promise.collect(fut1).within(0.01)

    self.assertEqual(fut2.get(0.5), [1,2,3])

  def test_collect_failure(self):
    fut1 = [Promise.exception(ExampleException()), Promise.value(2), Promise.value(3)]
    fut2 = Promise.collect(fut1)

    self.assertRaises(ExampleException, fut2.get, 0.05)

  def test_join_success(self):
    fut1 = [Promise.wait(0.1).map(lambda v: 0.1), Promise.value(0.1)]
    fut2 = Promise.join(fut1)

    for fut in fut1:
      self.assertEqual(fut.get(0.5), 0.1)

  def test_join_failure(self):
    fut1 = [Promise.value(0), Promise().within(0.05)]
    fut2 = Promise.join(fut1)

    self.assertRaises(TimeoutError, fut2.get, 0.05)

  def test_select(self):
    fut1 = [Promise(), Promise.wait(0.05).map(lambda v: 0.05)]
    resolved, rest = Promise.select(fut1).get(0.1)

    self.assertEqual(len(rest), 1)
    self.assertEqual(resolved.get(0.5), 0.05)
    self.assertFalse(rest[0].isdefined())

  def test_join_(self):
    self.assertEqual(
      Promise.value(1).join_(Promise.value(2)).get(0.05),
      [1,2],
    )

  def test_or_(self):
    self.assertEqual(
      Promise.wait(0.05).map(lambda v: 1).or_(
        Promise.wait(0.25).map(lambda v: 2),
        Promise.wait(0.50).map(lambda v: 3),
      ).get(0.1),
      1,
    )


class FutureTests(
    unittest.TestCase
  ):
  """Tests for read-only Futures"""

  def setUp(self):
    Promise.executor(ThreadPoolExecutor(max_workers=10))

  def test_proxy(self):
    promise = Promise()
    future  = promise.future()

    self.assertRaises(
      TimeoutError,
      future.get,
      timeout=0.01,
    )

    promise.setvalue(1)

    self.assertEqual(1, future.get(timeout=0.01))

  def test_no_set(self):
    future = Promise().future()
    self.assertRaises(AttributeError, future.setvalue, 1)
    self.assertRaises(AttributeError, future.setexception, ExampleException())


class PromiseTests(
    PromiseConstructorTests,
    PromiseBasicTests,
    PromiseCallbackTests,
    PromiseMapTests,
    PromiseMiscellaneousTests,
    PromiseThreadcountTests,
    PromiseAlternativeNamesTests,
    PromiseMergingTests,

    unittest.TestCase,
  ):

  def setUp(self):
    Promise.executor(ThreadPoolExecutor(max_workers=10))


if __name__ == '__main__':
  unittest.main()
