from commons import *


def fetch_sync(url, retries=3):
  try:
    response = urlget(url)
    return Success(url, response)
  except Exception as e:
    if retries > 0:
      return fetch_sync(url, retries-1)
    else:
      return Error(url, e)


def fetch_async(url, retries=3):
  return (
    Promise
    .call     (urlget, url)
    .map      (lambda response : Success(url, response))
    .rescue   (lambda error    :
      fetch_async(url, retries-1)
      if   retries > 0
      else Promise.value(Error(url, error))
    )
  )
