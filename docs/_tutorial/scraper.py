from commons import *

import logging
import logging.config

from mirai import UnboundedThreadPoolExecutor
import click


def fetch(url, finish_by):
  start  = time.time()
  within = finish_by - start
  return (
    Promise
    .call(urlget, url, finish_by)
    .within(within)
    .onsuccess(lambda status   : \
      logging.info(u"Fetched {} in {:0.3f} seconds.".format(url, time.time() - start)) \
    )
    .onfailure(lambda error    : \
      logging.warning(u"Failed to fetch {} in {:.2f} seconds".format(url, finish_by - time.time()))
    )
    .map   (lambda response : Success(url, response))
    .rescue(lambda error    : \
           Promise.exception(TimeoutError(url, error))
      if   isinstance(error, requests.exceptions.Timeout)
      else Promise.exception(error)
    )
  )


def scrape(url, finish_by, maxdepth=0):
  """
  Scrape a webpage and all its links. Guaranteed to finish within a fixed
  amount of time.

  Parameters
  ----------
  url : str
      web page URL
  finish_by : float
      time to finish by in seconds since epoch
  maxdepth : int, optional
      maximum number of links to follow in a chain

  Returns
  -------
  pages : Future([Status])
      A Future containing a list of `Success`, `Error`, or `Timeout` objects.
  """
  within = finish_by - time.time()

  if within <= 0:
    # out of time
    return Promise.value([])

  logging.info("{:0.3f} seconds left to fetch {}".format(within, url))

  # fetch the raw page. this future may contain an exception if it takes too
  # long to retrieve.
  page = fetch(url, finish_by)

  # transform the previous future into a Success/Failure/Timeout, regardless of
  # whether or not it completed successfully.
  page_status = (
    page
    .handle(lambda error    : \
           Timeout(url, error)
      if   isinstance(error, TimeoutError)
      else Error(url, error)
    )
    .map   (lambda status: [status])
  )

  # Scrape all of this page's children. Note that if `page` contains an
  # exception, no scraping will actually be done.
  child_page_statuses = (
    page
    .map(lambda status: links(url, status.response.text))
    .map(lambda linkset: [
      scrape(link, finish_by, maxdepth=(maxdepth - 1))
      for link in linkset
    ])
    .flatmap(Promise.collect)
    .map(fu.cat)
    .handle(lambda e: [])
  )

  # combine [page] with [child1, child2, ...]
  return (
    page_status
    .join_(child_page_statuses)
    .map(lambda (parent, children): parent + children)
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

  Promise.executor(UnboundedThreadPoolExecutor())

  start   = time.time()
  results = scrape(url, finish_by=(start + within), maxdepth=maxdepth).get()
  stop    = time.time()

  print u'Retrieved {:,d} URLs in {:0.3f} seconds'.format(len(results), stop-start)
  for responsetype, responses in fu.group_by(type, results).items():
    print u'{:20s} {:,d}'.format(responsetype.__name__, len(responses))

  Promise.executor().shutdown()


if __name__ == '__main__':
  main()
