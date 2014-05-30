from concurrent.futures import wait
import unittest

from mirai import Promise
from mirai.pool import *
from mirai.tests.test_futures import (
    PromiseConstructorTests,
    PromiseBasicTests,
    PromiseCallbackTests,
    PromiseMapTests,
    PromiseMiscellaneousTests,
    PromiseAlternativeNamesTests,
    PromiseMergingTests,
)


class UnboundedThreadPoolExecutorTests(unittest.TestCase):

  def setUp(self):
    self.pool = UnboundedThreadPoolExecutor()

  def test_submit(self):

    def foo(a, b, c):
      return a + b * c

    futures = [self.pool.submit(foo, i, i+1, c=i+2) for i in range(100)]
    wait(futures)
    results = [f.result() for f in futures]

    self.assertEqual(
      [foo(i, i+1, c=i+2) for i in range(100)],
      results,
    )

  def test_shutdown(self):
    self.pool.shutdown()
    self.assertRaises(RuntimeError, self.pool.submit, lambda: 1)


class UnboundedThreadPoolExecutorPromiseTests(
    PromiseConstructorTests,
    PromiseBasicTests,
    PromiseCallbackTests,
    PromiseMapTests,
    PromiseMiscellaneousTests,
    PromiseAlternativeNamesTests,
    PromiseMergingTests,

    unittest.TestCase
  ):

  def setUp(self):
    self.pool = UnboundedThreadPoolExecutor()
    Promise.executor(self.pool)
