from __future__ import annotations

class PermissionReason:
	"""Class which describes a reason why a user has permission"""

	def __init__(self, flag : bool | None, perm_type : str | None, match_str : str | None):
		self.flag = flag
		self.perm_type = perm_type
		self.match_str = match_str

		self.channel : str | None = None
		self.group : str | None = None

	def __bool__(self):
		"""Returns True if we actually have a permission here (either a grant or a deny)"""
		return self.flag is not None
