from typing import Callable, TypeVar
import collections

K = TypeVar("K")
V = TypeVar("V")

class DefaultDict(dict[K, V]):
	"""Special DefaultDict which passes the key as part of its default_factory"""

	def __init__(self, default_factory: Callable[[K], V]):
		super().__init__()
		self.default_factory = default_factory

	def __missing__(self, key: K) -> V:
		if self.default_factory is None:
			raise KeyError(key)
		else:
			ret = self[key] = self.default_factory(key)
			return ret