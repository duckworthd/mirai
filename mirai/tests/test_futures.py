import unittest

from mirai import *


class FutureConstructorTests(unittest.TestCase):

  def test_value(self):
    self.assertEqual(Future.value(1).get(), 1)

  def test_exception(self):
    self.assertRaises(Exception, Future.exception(Exception()).get)


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
    fut2 = fut1.rescue(lambda e: e.message)

    self.assertEqual(fut2.get(), "A")

  def test_within_success(self):
    fut1 = Future.value("A")
    fut2 = fut1.within(0)

    self.assertEqual(fut2.get(), "A")

  def test_within_failure(self):
    fut1 = Future()
    fut2 = fut1.within(0)

    self.assertRaises(TimeoutError, fut2.get)


class FutureMergingTests(unittest.TestCase):

  def test_collect_success(self):
    fut1 = [Future.value(1), Future.value(2), Future.value(3)]
    fut2 = Future.collect(fut1, timeout=0.01)

    self.assertEqual(sorted(fut2.get()), [1,2,3])

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
