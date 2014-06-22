from commons import *


def fetch_sync(url):
  try:
    response = urlget(url)
    return Success(url, response)
  except Exception as e:
    return Error(url, e)


def fetch_async(url):
  return (
    Promise
    .call  (urlget, url)
    .map   (lambda response : Success(url, response))
    .handle(lambda error    : Error  (url, error   ))
  )
