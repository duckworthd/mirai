from collections import namedtuple

from mirai import Promise
import requests


# containers for possible HTTP responses
Error   = namedtuple("Error"  , ["url", "exception"])
Success = namedtuple("Success", ["url", "response" ])


def fetch_async(url):
  return (
    Promise.call(requests.get, url)
    .map      (lambda response : Success(url, response))
    .handle   (lambda error    : Error(url, error))
  )
