from commons import *
from tutorial04 import fetch_sync, fetch_async


def scrape_sync(url, finish_by, retries=3, maxdepth=0):
  remaining = finish_by - time.time()
  if   remaining <= 0:
    return [Timeout(url, None)]
  elif maxdepth  == 0:
    return [fetch_sync(url, finish_by, retries)]
  elif maxdepth   < 0:
    return []
  else:
    status   = fetch_sync(url, finish_by, retries)
    if isinstance(status, Success):
      linkset  = links(url, status.response.text)
      children = [
        scrape_sync(link, finish_by, retries, maxdepth-1)
        for link in linkset
      ]
      return fu.cat([[status]] + children)
    else:
      return [status]


def scrape_async(url, finish_by, retries=3, maxdepth=0):
  remaining = finish_by - time.time()
  if   remaining <= 0:
    return Promise.value([Timeout(url, None)])
  elif maxdepth  == 0:
    return (
      fetch_async(url, finish_by, retries)
      .map(lambda status: [status])
    )
  elif maxdepth   < 0:
    return Promise.value([])
  else:
    status  = fetch_async(url, finish_by, retries)

    children = (
      status
      .map(lambda status: \
        links(url, status.response.text)
        if   isinstance(status, Success)
        else []
      )
      .map(lambda linkset: [
        scrape_async(link, finish_by, retries, maxdepth-1)
        for link in linkset
      ])
      .flatmap(Promise.collect)
    )

    return (
      status.join_(children)
      .map(lambda (status, children): [[status]] + children)
      .map(fu.cat)
    )
