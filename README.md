mirai
=====

`mirai` is a port of [Twitter Futures][1] to python based on a backport of
Python 3.2's [concurrent.futures][2]. `mirai` offers a simpler
operator-chaining based way for taking advantage of futures.

[1]: http://twitter.github.io/scala_school/finagle.html#futconcurrent
[2]: https://docs.python.org/dev/library/concurrent.futures.html

Here's an excellent example taken from Twitter's [Introduction to Finagle][1]
page, converted into Python,


```python
from collections import namedtuple
from mirai import Future

class HTMLPage(object):
  def __init__(self, i, l):
    self.image_links = i
    self.links       = l

class Img(object):
  def __init__(self):
    self.image_links = []
    self.links       = []

profile  = HTMLPage(["portrait.jpg"], ["gallery.html"])
portrait = Img()
gallery  = HTMLPage(["kitten.jpg", "puppy.jpg"], ["profile.html"])
kitten   = Img()
puppy    = Img()

internet = {
  "profile.html" : profile,
  "gallery.html" : gallery,
  "portrait.jpg" : portrait,
  "kitten.jpg"   : kitten,
  "puppy.jpg"    : puppy,
}

# In a real crawler, this would be replaced by something that downloads content
# from the web and populates a future with it.
def fetch(url):
  return Future.value(internet[url])

# get a single image from a page
def get_thumbnail(url):
  return fetch(url).flatmap(lambda page: fetch(page.image_links[0]))

# get all images from a page
def get_thumbnails(url):
  return fetch(url).flatmap(lambda page:
    Future.collect(
      map(fetch, page.image_links])
    )
  )

# recursively crawl the entire internet. since there's no checks for loops
# (e.g. profile.html -> gallery.html -> profile.html -> ...), this will run
# forever.
def crawl(url):

  def flatten(lol):   # since there's no list.flatten in Python
    result = []
    for l in lol:
      result.extend(l)
    return result

  return fetch(url).flatmap(lambda page:
    Future
      .collect(map(crawl, page.links))
      .map(flatten)
  )
```
