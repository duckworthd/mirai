
def proxyto(target, source, allowed_specials=[]):
  """Proxy all attributes to another object.

  Copies all attributes from `source` to `target`, excepting "special"
  methods (those with leading and trailing double-underscores).
  `allowed_specials` allows you to whitelist selected special methods.

  Parameters
  ----------
  target : object
      object to copy attributes to
  source : object
      object to copy attributes from
  allowed_specials : [str], optional
      names of special methods to copy.

  Returns
  -------
  target : object
  """

  # set all non-hidden methods
  for k in dir(source):
    k_is_special = k.startswith("__") and k.endswith("__")
    copy_k       = not k_is_special or k in allowed_specials
    if not hasattr(target, k) and copy_k:
      setattr(target, k, getattr(source, k))

  return target
