mirai
=====

Welcome to mirai
----------------

.. currentmodule:: mirai

:mod:`mirai` is a multithreading library for Python that makes asynchronous
computation a breeze. Built on :mod:`concurrent.futures` and modeled after
`Twitter Futures`_, :mod:`mirai` helps you write modular, easy-to-read
asynchronous workflows without falling into callback hell.

What can :mod:`mirai` do for you? Here's a demo for fetching the weather
forecast for San Francisco with a 10 second timeout,

.. code-block:: python

  from mirai import Promise
  from pprint import pprint
  import json
  import requests

  url    = "http://api.openweathermap.org/data/2.5/forecast"
  query  = {"q": "San Francisco", "units": "imperial"}
  result = (
    Promise.call(lambda: requests.get(url, params=query))
    .onsuccess(lambda response: pprint("Success!"))
    .map(lambda response: json.loads(response.text))
    .map(lambda weather: {
      "status": "success",
      "forecast": sorted([
        {
          "time"    : f['dt_txt'],
          "weather" : f['weather'][0]['description'],
          "temp"    : f['main']['temp'],
        } for f in weather['list']
      ])
    })
    .within(10.0)
    .handle(lambda e: {"status": "failure", "reason": unicode(e) })
    .get()
  )

  pprint(result)


You can install the library with,

.. code-block:: bash

  $ pip install mirai


Documentation
-------------

.. toctree::
  :maxdepth: 2

  why
  tutorial
  api
  caveats


.. _`Twitter Futures`: http://twitter.github.io/scala_school/finagle.html#Future
