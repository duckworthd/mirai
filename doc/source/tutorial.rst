Tutorial
========

.. module:: mirai

In this tutorial, we'll explore building a basic web crawler. This web crawler will


def abslink(domain, l):
  if l.startswith("/"): return urljoin(domain, l)
  else                : return l

def links(url):
  repsonse = requests.get(url)
  links = pq(response.body).map(lambda _, el: pq(el).attr("href"))
  return [
    abslink(l) for l in links
    if l.startswith("http") or l.startswith("/")
  ]


- fetching synchronously
- fetching asynchronously
- retrying
- handling timeouts
- grouping together
- recursing
- logging
