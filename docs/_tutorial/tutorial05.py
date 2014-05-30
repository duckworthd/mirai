from gevent.monkey import patch_all; patch_all()

from collections import namedtuple
from urlparse import urljoin
from time import time as now

from mirai import Promise, TimeoutError
from pyquery import PyQuery as pq
import funcy as fu
import requests


# containers for possible states of an HTTP response
Error   = namedtuple("Error"  , ["url", "exception",      ])
Success = namedtuple("Success", ["url", "time", "response"])
Timeout = namedtuple("Timeout", ["url",                   ])

def abslink(domain, l):
  """Turn a (potentially) relative URL into an absolute one"""
  if l.startswith("/"): return urljoin(domain, l)
  else                : return l


def links(url, text):
  """Extract all links from a web page"""
  links = pq(text)("a").map(lambda _, el: pq(el).attr("href"))
  return [
    abslink(url, l) for l in links
    if l.startswith("http") or l.startswith("/")
  ]


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


def scrape_sync(url, remaining=10.0, retries=3, maxdepth=0):
  start = now()
  if   remaining <= 0: return [Timeout(url)]
  elif maxdepth  == 0: return [fetch_sync(url, time_left(start, remaining), retries)]
  elif maxdepth   < 0: return []
  else:
    status   = fetch_sync(url, time_left(start, remaining), retries)
    if isinstance(status, Success):
      linkset  = links(url, status.response.text)
      statuses = [
        scrape_sync(link, time_left(start, remaining), retries, maxdepth-1)
        for link in linkset
      ] + [status]
      return fu.cat(statuses)
    else:
      return [status]


def scrape_async(url, remaining=10.0, retries=3, maxdepth=0):
  start = now()
  if   remaining <= 0: return Promise.value([Timeout(url)])
  elif maxdepth  == 0: return fetch_async(url, time_left(start, remaining), retries) \
                              .map(lambda status: [status])
  elif maxdepth   < 0: return Promise.value([])
  else:
    return (
      fetch_async(url, time_left(start, remaining), retries)
      .map(lambda status: (links(url, status.response.text), status) \
        if isinstance(status, Success)
        else ([], status)
      )
      .map(lambda (linkset, status): [
        scrape_async( link, time_left(start, remaining), retries, maxdepth-1)
        for link in linkset
        ] + [ Promise.value([status]) ]
      )
      .flatmap(Promise.collect)
      .map(fu.cat)
    )

