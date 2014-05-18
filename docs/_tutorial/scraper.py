from gevent.monkey import patch_all; patch_all()

from concurrent.futures import ThreadPoolExecutor
from collections import namedtuple
from urlparse import urljoin
import logging
import logging.config
import time

from mirai import Promise, TimeoutError
from pyquery import PyQuery as pq
import click
import funcy as fu
import requests


Error   = namedtuple("Error"  , ["url", "exception"])
Success = namedtuple("Success", ["url", "response" ])
Timeout = namedtuple("Timeout", ["url", "exception"])

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


# def fetch(url):
#   try:
#     start    = time.time()
#     response = requests.get(url)
#     end      = time.time()
#     return Success(url, response)
#   except Exception as e:
#     return Error(url, e)
#
#
# def scrape(url, within, maxdepth=0):
#   start = time.time()
#   if within <= 0:
#     return [Timeout(url, None)]
#   elif maxdepth == 0:
#     status = fetch(url)
#     if within < time.time() - start: return [Timeout(url, e)]
#     else                           : return [status]
#   elif maxdepth < 0:
#     return []
#   else:
#     status = fetch(url)
#     if within < time.time() - start: return [Timeout(url, e)]
#     linkset = links(url, status.response.text)
#     statuses = [
#       scrape(
#         link,
#         within   = (within - (time.time() - start)),
#         maxdepth = maxdepth-1
#       )
#       for link in linkset
#     ] + [status]
#     statuses = fu.concat(statuses)
#     return statuses


def fetch(url):
  start = time.time()
  return (
    Promise.call(requests.get, url)
    .onsuccess(lambda status   : \
      logging.info(u"Fetched {} in {:0.3f} seconds.".format(url, time.time() - start)) \
    )
    .onfailure(lambda error    : \
      logging.warning(u"Failed to fetch {}".format(url))
    )
    .map      (lambda response : Success(url, response))
    .handle   (lambda error    : Error(url, error))
  )


def scrape(url, within, maxdepth=0):
  logging.info("{:0.3f} seconds left to fetch {}".format(within, url))

  start = time.time()
  if within <= 0:
    # out of time
    return Promise.value([Timeout(url, None)])
  elif maxdepth == 0:
    # don't get any more links
    return (
      fetch(url)
      .within(within)
      .map(lambda status: [status])
      .handle(lambda e: [Timeout(url, e)])
    )
  elif maxdepth < 0:
    # this shouldn't happen, but just in case
    return Promise.value([])
  else:
    # fetch links
    return (
      fetch(url)
      .within(within)
      .map(lambda status: (links(url, status.response.text), status))
      .map(lambda (linkset, status): [
        scrape(
          link,
          within   = (within - (time.time() - start)),
          maxdepth = maxdepth - 1,
        ) for link in linkset
      ] + [
        Promise.value([status])
      ])
      .flatmap(Promise.collect)
      .map(fu.cat)
      .handle(lambda err: [Timeout(url, err)])
    )


@click.command()
@click.argument("url")
@click.option("--within", type=float, default=10.0, help="Seconds available.")
@click.option("--maxdepth", type=int, default=2, help="Degrees of separation.")
def main(url, within, maxdepth):
  logging.config.dictConfig({
    "version": 1,
    "root"   : { "level": "INFO" },
    "loggers": {
      "requests": { "level": "CRITICAL" },
    }
  })

  start   = time.time()
  results = scrape(url, within, maxdepth=maxdepth).get()
  stop    = time.time()

  print u'Retrieved {:,d} URLs in {:0.3f} seconds'.format(len(results), stop-start)
  for responsetype, responses in fu.group_by(type, results).items():
    print u'{:20s} {:,d}'.format(responsetype.__name__, len(responses))


if __name__ == '__main__':
  main()
