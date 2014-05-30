from collections import namedtuple
from time import time as now

from mirai import Promise, TimeoutError
import requests


# containers for possible states of an HTTP response
Error   = namedtuple("Error"  , ["url", "exception",      ])
Success = namedtuple("Success", ["url", "time", "response"])
Timeout = namedtuple("Timeout", ["url",                   ])

def time_left(start, given):
  return given - (now() - start)


def fetch_sync(url, remaining=10.0, retries=3):
  if remaining < 0: return Timeout(url)
  start = now()
  try:
    response = requests.get(url)
    if time_left(start, remaining) > 0:
      return Success(url, now() - start, response)
    else:
      return Timeout(url)
  except Exception as e:
    if retries > 0:
      return fetch_sync(url, time_left(start, remaining), retries-1)
    else:
      return Error(url, e)


def fetch_async(url, remaining=10.0, retries=3):
  if remaining < 0: return Promise.value(Timeout(url))
  start = now()
  return (
    Promise.call(requests.get, url)
    .within(remaining)
    .map      (lambda response : Success(url, now() - start, response))
    .rescue   (lambda error    :
      fetch_async(url, time_left(start, remaining), retries-1) if retries > 0
      else Promise.value(Error(url, error))
    )
  )
