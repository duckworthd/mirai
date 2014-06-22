Tutorial
========

.. module:: mirai

The primary benefit of working with :mod:`mirai` is the ability to write
asynchronous code much the same way you already write synchronous code. We'll
illustrate this by writing a simple web scraper, step-by-step, with and without
:mod:`mirai`.

Fetching a Page
---------------

We begin with the most basic task for any web scraper -- fetching a single web
page. Rather than directly returning the page's contents, we'll return a
:class:`Success` container indicating that our request went through
successfully.  Similarly, we'll return an :class:`Error` container if the
request failed.

Using a function :func:`urlget`, which returns a response if a request succeeds
and raises an exception if a request fails, we can start with the following two
`fetch` functions,

.. literalinclude:: _tutorial/tutorial02.py

Retrying on Failure
-------------------

Sometimes, an fetch failure is simply transient; that is to say, if we simply
retry we may be able to fetch the page.  Using recursion, let's add an optional
`retries` argument to our `fetch` functions,

.. literalinclude:: _tutorial/tutorial03.py

Handling Timeouts
-----------------

Another common concern is time -- if a page takes too long to fetch, we may
rather consider it a loss rather than wait for it to finish downloading. Let's
construct a new container called :class:`Timeout` that will indicate that a
page took too long to retrieve. We'll give `fetch` a `finish_by` argument
specifying when, in time, we want the function to return by.

You'll notice that rather than telling the `fetch` functions how much time they
have, we give them a deadline by which they must finish. This is because
relative durations become easily muddled in asynchronous code when functions
are called with a delay.

.. literalinclude:: _tutorial/tutorial04.py

Scraping Links
--------------

Finally, let's complete our scraper by following each page's links. To keep our
code from running forever, we'll only follow links up to a fixed maximum depth.
Moreover, we'll add a `finish_by` to limit the amount of time until the
function returns.

This is where :mod:`mirai`'s asynchronous nature really shines. While the
synchronous version must fetch each page one at a time, :mod:`mirai` makes it
easy to fetch pages in parallel with minimal change to the source,

.. literalinclude:: _tutorial/tutorial05.py

Wrapping Up
-----------

We now have a fully functional web scraper, capable of handling timeouts and
retrying on failure. To try this scraper out for yourself, download the code in
the [tutorial folder](https://github.com/duckworthd/mirai/tree/develop/docs/_tutorial)
and see for yourself how :mod:`mirai` can make your life easier!
