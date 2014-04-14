from concurrent.futures import ThreadPoolExecutor
import unittest

from mirai import *


class FutureConstructorTests(unittest.TestCase):

  def test_value(self):
    self.assertEqual(Future.value(1).get(), 1)

  def test_exception(self):
    self.assertRaises(Exception, Future.exception(Exception()).get)

  def test_wait(self):
    self.assertIsNone(Future.wait(0.05).get(), None)


class FutureBasicTests(unittest.TestCase):

  def test_setvalue(self):
    o    = object()
    fut1 = Future()
    fut1.setvalue(o)

    self.assertEqual(fut1.get(), o)

  def test_setvalue_twice(self):
    fut1 = Future()
    fut1.setvalue(1)

    self.assertRaises(FutureError, fut1.setvalue, 2)

    fut2 = Future()
    fut2.setexception(1)

    self.assertRaises(FutureError, fut2.setvalue, 2)

  def test_setexception(self):
    e    = Exception()
    fut1 = Future()
    fut1.setexception(e)

    self.assertRaises(Exception, fut1.get)

  def test_setexception_twice(self):
    e    = Exception()
    fut1 = Future()
    fut1.setexception(e)

    self.assertRaises(FutureError, fut1.setexception, e)

    fut1 = Future()
    fut1.setvalue(1)

    self.assertRaises(FutureError, fut1.setexception, e)

  def test_get_success(self):
    fut = Future.value(1)

    self.assertEqual(fut.get(), 1)

  def test_get_exception(self):
    fut = Future.exception(Exception())

    self.assertRaises(Exception, fut.get)

  def test_isdefined(self):
    self.assertFalse(Future().isdefined())
    self.assertTrue(Future.value(1).isdefined())
    self.assertTrue(Future.exception(Exception()).isdefined())

  def test_isfailure(self):
    self.assertIsNone(Future().isfailure())
    self.assertTrue(Future.exception(Exception()).isfailure())
    self.assertFalse(Future.value(1).isfailure())

  def test_issuccess(self):
    self.assertIsNone(Future().issuccess())
    self.assertFalse(Future.exception(Exception()).issuccess())
    self.assertTrue(Future.value(1).issuccess())

  def test_proxyto(self):
    fut1 = Future()
    fut2 = Future.wait(0.05).map(lambda v: 1).proxyto(fut1)

    self.assertEqual(fut1.get(0.1), 1)

    fut1 = Future()
    fut2 = Future.wait(0.05) \
        .flatmap(lambda v: Future.exception(FutureError())) \
        .proxyto(fut1)

    self.assertRaises(FutureError, fut1.get, 0.1)


class FutureCallbackTests(unittest.TestCase):

  def test_onsuccess_success(self):
    fut1 = Future()
    fut2 = Future.value(1).onsuccess(lambda v: fut1.setvalue(v))

    self.assertEqual(fut1.get(), 1)

  def test_onsuccess_failure(self):
    fut1 = Future()
    fut2 = Future.exception(Exception()).onsuccess(lambda v: fut1.setvalue(v))

    Future.join([fut2])

    self.assertRaises(TimeoutError, fut1.within(0).get)

  def test_onfailure_success(self):
    fut1 = Future()
    fut2 = Future.value(1).onfailure(lambda e: fut1.setvalue(e))

    Future.join([fut2])

    self.assertRaises(TimeoutError, fut1.within(0).get)

  def test_onfailure_failure(self):
    e    = Exception()
    fut1 = Future()
    fut2 = Future.exception(e).onfailure(lambda e: fut1.setvalue(e))

    self.assertEqual(fut1.get(), e)


class FutureMapTests(unittest.TestCase):

  def test_flatmap_success(self):
    fut1 = Future.value(1)
    fut2 = fut1.flatmap(lambda v: Future.value(v+1))

    self.assertEqual(fut2.get(), 2)

  def test_flatmap_exception(self):
    fut1 = Future.exception(Exception())
    fut2 = fut1.flatmap(lambda v: v+1)

    self.assertRaises(Exception, fut2.get)

  def test_map_success(self):
    fut1 = Future.value(1)
    fut2 = fut1.map(lambda v: v+1)

    self.assertEqual(fut2.get(), 2)

  def test_map_failure(self):
    fut1 = Future.exception(Exception())
    fut2 = fut1.map(lambda v: v+1)

    self.assertRaises(Exception, fut2.get)


class FutureMiscellaneousTests(unittest.TestCase):

  def test_rescue_success(self):
    fut1 = Future.value("A")
    fut2 = fut1.rescue(lambda e: "B")

    self.assertEqual(fut2.get(), "A")

  def test_rescue_failure(self):
    fut1 = Future.exception(Exception("A"))
    fut2 = fut1.rescue(lambda e: Future.value(e.message))

    self.assertEqual(fut2.get(), "A")

  def test_within_success(self):
    fut1 = Future.value("A")
    fut2 = fut1.within(0)

    self.assertEqual(fut2.get(), "A")

  def test_within_failure(self):
    fut1 = Future()
    fut2 = fut1.within(0)

    self.assertRaises(TimeoutError, fut2.get)

  def test_respond(self):
    fut1 = Future()
    Future.value(1).respond(lambda f: f.proxyto(fut1))

    self.assertEqual(fut1.get(0.05), 1)

    fut1 = Future()
    Future.exception(FutureError()).respond(lambda f: f.proxyto(fut1))

    self.assertRaises(FutureError, fut1.get, 0.05)

  def test_unit(self):
    self.assertIsNone(Future.value(1).unit().get(0.05))
    self.assertRaises(Exception, Future.exception(Exception()).unit().get, 0.05)

  def test_update(self):
    self.assertEqual(Future().update(Future.value(1)).get(0.01), 1)
    self.assertRaises(Exception, Future().update(Future.exception(Exception())).get, 0.01)

  def test_updateifempty(self):
    # nothing/value
    self.assertEqual(Future().updateifempty(Future.value(1)).get(0.01), 1)

    # value/value
    self.assertEqual(Future.value(2).updateifempty(Future.value(1)).get(0.01), 2)

    # exception/nothing
    self.assertRaises(FutureError,
      Future
      .exception(FutureError())
      .updateifempty(Future())
      .get,
      0.05
    )

    # nothing/exception
    self.assertRaises(FutureError,
      Future()
      .updateifempty(Future.exception(FutureError()))
      .get,
      0.05
    )

    # exception/value
    self.assertRaises(FutureError,
      Future.exception(FutureError())
      .updateifempty(Future.value(1))
      .get,
      0.05
    )

  def test_executor(self):
    old = Future.executor()
    new = Future.executor(ThreadPoolExecutor(max_workers=10))
    self.assertEqual(Future.call(lambda v: v+1, 1).get(0.05), 2)


class FutureAlternativeNamesTests(unittest.TestCase):

  def test_andthen(self):
    self.assertEqual(
        Future.value(2).flatmap(lambda v: Future.value(5)).get(),
        Future.value(2).andthen(lambda v: Future.value(5)).get(),
    )

  def test_call(self):
    self.assertEqual(Future.value(1).get(), Future.value(1)())
    self.assertRaises(TimeoutError, Future().get, 0.05)

  def test_ensure(self):
    fut1 = Future()
    fut2 = Future.value(2).ensure(lambda: fut1.setvalue(2))

    self.assertEqual(fut1.get(0.5), 2)

    fut1 = Future()
    fut2 = Future.exception(Exception()).ensure(lambda: fut1.setvalue(2))

    self.assertEqual(fut1.get(0.5), 2)

  def test_filter(self):
    fut1 = Future.value(1).filter(lambda v: v != 1)
    self.assertRaises(FutureError, fut1.get, 0.1)

    fut1 = Future.value(1).filter(lambda v: v == 1)
    self.assertEqual(fut1.get(0.05), 1)

    fut1 = Future.exception(FutureError()).filter(lambda v: v == 1)
    self.assertRaises(FutureError, fut1.get, 0.1)

  def test_foreach(self):
    fut1 = Future()
    fut2 = Future.value(1).foreach(lambda v: fut1.setvalue(v))

    self.assertEqual(fut1.get(0.05), 1)

    fut1 = Future()
    fut2 = Future.exception(Exception()).foreach(lambda v: fut1.setvalue(v))

    self.assertRaises(TimeoutError, fut1.get, 0.05)

  def test_getorelse(self):
    self.assertEqual(Future().getorelse(0.5), 0.5)
    self.assertEqual(Future.value(1).getorelse(0.5), 1)
    self.assertEqual(Future.exception(Exception).getorelse(0.5), 0.5)

  def test_handle(self):
    self.assertEqual(
      Future
        .exception(Exception("uh oh"))
        .handle(lambda e: e.message)
        .get(0.05),
      "uh oh",
    )

    self.assertEqual(
      Future
        .value(1)
        .handle(lambda e: e.message)
        .get(0.05),
      1,
    )

  def test_select_(self):
    self.assertEqual(
      Future.wait(0.15).flatmap(lambda v: Future.exception(FutureError()))
      .select_(
        Future.wait(0.05).map(lambda v: 2),
        Future.wait(0.10).map(lambda v: 3),
      ).get(0.2),
      2,
    )


class FutureMergingTests(unittest.TestCase):

  def test_collect_success(self):
    fut1 = [Future.value(1), Future.value(2), Future.value(3)]
    fut2 = Future.collect(fut1, timeout=0.01)

    self.assertEqual(fut2.get(), [1,2,3])

  def test_collect_failure(self):
    fut1 = [Future.exception(Exception()), Future.value(2), Future.value(3)]
    fut2 = Future.collect(fut1)

    self.assertRaises(Exception, fut2.get)

  def test_join_success(self):
    fut1 = [Future.wait(0.1).map(lambda v: 0.1), Future.value(0.1)]
    fut2 = Future.join(fut1)

    for fut in fut1:
      self.assertEqual(fut.get(), 0.1)

  def test_join_failure(self):
    fut1 = [Future.value(0), Future().within(0.05)]
    fut2 = Future.join(fut1)

    self.assertRaises(TimeoutError, fut2.get)

  def test_select(self):
    fut1 = [Future(), Future.wait(0.05).map(lambda v: 0.05)]
    resolved, rest = Future.select(fut1).get(0.1)

    self.assertEqual(len(rest), 1)
    self.assertEqual(resolved.get(), 0.05)
    self.assertFalse(rest[0].isdefined())

  def test_join_(self):
    self.assertEqual(
      Future.value(1).join_(Future.value(2)).get(0.05),
      [1,2],
    )

  def test_or_(self):
    self.assertEqual(
      Future.wait(0.05).map(lambda v: 1).or_(
        Future.wait(0.10).map(lambda v: 2),
        Future.wait(0.15).map(lambda v: 3),
      ).get(0.2),
      1,
    )
