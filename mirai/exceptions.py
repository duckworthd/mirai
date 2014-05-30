import sys

import joblib


class MiraiError(Exception):
  """Base class for all exceptions raise by Promises"""
  pass


class AlreadyResolvedError(MiraiError):
  """
  Exception thrown when attempting to set the value or exception of a Promise
  that has already had its value or exception set.
  """
  pass


class ShadowException(MiraiError):
  """
  An exception that's never used directly. In particular, a ShadowException is
  used to wrap a thrown exception and allow it to store the traceback context
  as a string so that users of Promise will have some idea what's going on.

  Parameters
  ----------
  exception : Exception
      Other exception to wrap
  context : string
      Formatted string containing the traceback that caused `other` to be thrown
  """

  def __init__(self, exception, context):
    self.exception = exception
    self.context   = context

  def __unicode__(self):
    return u"{cls}: {msg}\n{ctx}".format(
      cls = self.__class__.__name__,
      msg = self.message,
      ctx = self.context,
    )

  def __str__(self):
    return unicode(self)

  def __repr__(self):
    return u"{cls}({msg})".format(
      cls = self.__class__.__name__,
      msg = self.message,
    )

  def __getattr__(self, key):
    return getattr(self.exception, key)

  @staticmethod
  def build(exception, context):
    """
    Construct a child class of a thrown exception and ShadowException, and
    instantiate it.
    """
    cls = exception.__class__
    t = type(
      "Mirai" + cls.__name__,
      (ShadowException, cls),
      {}
    )
    return t(exception, context)


class SafeFunction(object):
  """
  A function-like object that catches all errors and adds their execution stack
  description to their message.
  """

  def __init__(self, f):
    self.f = f

  def __call__(self, *args, **kwargs):
    try:
      return self.f(*args, **kwargs)
    except Exception as e:
      if isinstance(e, ShadowException):
        raise e
      else:
        e_type, e_value, e_tb = sys.exc_info()

        # turn stack into a string
        text = joblib.format_stack.format_exc(e_type, e_value, e_tb, context=10, tb_offset=1)

        # manually delete e_tb (failing to do so will cause a memory leak. See
        # documentation for sys.exc_info())
        del e_tb

        if isinstance(e, MiraiError):
          # You'll get an invalid MRO if you inherit from MiraiError _and_
          # ShadowException (as the latter is already a child of MiraiError).
          # In this case, there's no need to construct a new type.
          raise ShadowException(e, text)
        else:
          # construct a new exception instance that's of the same class as the one
          # thrown, but also with additional context.
          raise ShadowException.build(e, text)
