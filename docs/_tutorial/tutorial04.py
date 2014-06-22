from commons import *


def fetch_sync(url, finish_by, retries=3):
  remaining = finish_by - time.time()

  if remaining <= 0:
    return Timeout(url, None)

  try:
    response = urlget(url, finish_by)
    return Success(url, response)
  except Exception as e:
    if retries > 0:
      return fetch_sync(url, finish_by, retries-1)
    else:
      if isinstance(e, requests.exceptions.Timeout):
        return Timeout(url, e)
      else:
        return Error(url, e)


def fetch_async(url, finish_by, retries=3):
  remaining = finish_by - time.time()

  if remaining < 0:
    return Promise.value(Timeout(url, None))

  return (
    Promise
    .call     (urlget, url, finish_by)
    .map      (lambda response : Success(url, response))
    .rescue   (lambda error    :
      fetch_async(url, finish_by, retries-1)
      if   retries > 0
      else Promise.value(Timeout(url, error))
           if   isinstance(error, requests.exceptions.Timeout)
           else Promise.value(Error(url, error))
    )
  )
