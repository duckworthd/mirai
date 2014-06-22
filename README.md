mirai
=====

`mirai` is a port of [Twitter Futures][1] to python powered by a backport of
Python 3.2's [concurrent.futures][2]. `mirai` offers a simpler
operator chaining-based way for using promises and futures.

[1]: http://twitter.github.io/scala_school/finagle.html#futconcurrent
[2]: https://docs.python.org/dev/library/concurrent.futures.html

### Installation

`mirai` is available on [pypi](http://pypi.python.org/pypi/mirai). Installation 
is as simple as using `pip`,

```bash
$ pip install mirai --upgrade
```

### Diving In

`mirai` is based around the concept of a Promises -- containers that
are populated with the result of an asynchronous computation. Promises provide
a more streamlined way for dealing with asynchronous code than callbacks.

```python
from mirai import Promise
import funcy as fu

(
  Promise

  # `call` is a way to execute a synchronous function asynchronously. It
  # returns a Promise you can use to queue up callbacks
  .call(twitter.get_followers, "duck")

  # `map` means "create another Promise by applying the following function to
  # my contents." If the previous Promise threw an exception, this callback
  # won't execute, and the resulting Promise will contain the previous
  # Promise's exception.
  .map(lambda followers: [
    Future.call(twitter.get_latest_posts, follow)
    for follower in followers
  ])

  # `Promise.collect` turns a sequence of promises into a Promise with a
  # sequence of items. If you have many sources for Promises, you can use
  # `Promise.collect` to bundle them together. Notice that we're using
  # `Promise.flatmap` here -- that's because `Promise.collect` returns a
  # Promise, not a normal value. If we didn't use flatmap, we'd end up with a
  # Promise containing another Promise!
  .flatmap(Promise.collect)

  # Each follower gave me a list of tweets, so rather than dealing a list of
  # lists, lets just turn it into a flat list of tweets
  .map(fu.flatten)

  # `Promise.onsuccess` and `Promise.onfailure` allow you to attach a callback
  # that doesn't actually affect the Promise's value. Great for logging!
  .onsuccess(lambda tweets: print("Retrieved {:,d} Tweets from my followers"))

  # Notice how we turned what could have been a synchronous double-for loop
  # into a series of asynchronous calls? Pretty awesome!
  .map(lambda tweets: [
    Future.call(twitter.retweet, tweet)
    for tweet in tweets
  ])
  .flatmap(Future.collect)
  .onsuccess(lambda retweets: print("I love EVERYBODY!"))

  # You can use `Promise.rescue` to turn a failing Promise into a successfuly
  # one, too.
  .rescue(lambda e: Future.value("Something went wrong...oh well"))

  # All of the above isn't executed until you request it's data, so don't
  # forget to call `Promise.get`! You can also use `Promise.join` and
  # `Promise.select` if you want to gather many Promises or just want the first
  # that finishes.
  .get()
)
```

### Documentation

Learn more about `mirai` at [http://mirai.readthedocs.org/](http://mirai.readthedocs.org/)
