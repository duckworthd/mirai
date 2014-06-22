from gevent.monkey import patch_all; patch_all()

from collections import namedtuple
from urlparse import urljoin
import time

from mirai import Promise, TimeoutError
from pyquery import PyQuery as pq
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


def urlget(url, finish_by=None):
  if finish_by is not None:
    within = finish_by - time.time()
    if within <= 0:
      raise requests.exceptions.Timeout(url)
    else:
      response = requests.get(url, timeout=within)
      if finish_by - time.time() < 0:
        raise requests.exceptions.Timeout(url)
      else:
        return response
  else:
    return requests.get(url)
