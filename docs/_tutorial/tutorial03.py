from collections import namedtuple

from mirai import Promise
import requests


# containers for possible states of an HTTP response
Error   = namedtuple("Error"  , ["url", "exception"])
Success = namedtuple("Success", ["url", "response" ])


def fetch_sync(url, retries=3):
  try:
    response = requests.get(url)
    return Success(url, response)
  except Exception as e:
    if retries > 0:
      return fetch_sync(url, retries-1)
    else:
      return Error(url, e)


def fetch_async(url, retries=3):
  return (
    Promise.call(requests.get, url)
    .map      (lambda response : Success(url, response))
    .rescue   (lambda error    :
      fetch(url, retries-1) if retries > 0
      else Promise.value(Error(url, error))
    )
  )
