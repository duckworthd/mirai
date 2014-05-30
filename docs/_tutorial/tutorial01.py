from collections import namedtuple

import requests


# containers for possible states of an HTTP response
Error   = namedtuple("Error"  , ["url", "exception"])
Success = namedtuple("Success", ["url", "response" ])


def fetch_sync(url):
  try:
    response = requests.get(url)
    return Success(url, response)
  except Exception as e:
    return Error(url, e)
