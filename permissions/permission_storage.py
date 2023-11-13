from __future__ import annotations

from permissions.reason import PermissionReason
from storage import Storage
from utility import DefaultDict

from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from connection.context import ConnectionDescriptor
	from connection.user import User

# Tracks all permissions, separately for each server. Supports arbitrary path lookups
# But effectively, These are all the current paths:
# permissions.<arbitrary boolean flags>
# permissions.<arbitrary path>.{StructuredPermission}
# permissions.command.<command>.{StructuredPermission}
# commands.<command>.enabled
# channels.<channel>.enabled
# global-enabled
# Most paths can have channels.<channel> before it, to make it channel-specific
# Channel-specific permissions are checked first and override any server-wide permissions
permissions : DefaultDict[ConnectionDescriptor, Storage]\
	= DefaultDict(default_factory=lambda con_desc: Storage("data", "permissions", f"permissions-{con_desc}"))

# Membership in groups
# Known paths:
# <group>.{StructuredGroup}
# channels.<channel>.<group>.{StructuredGroup}
group_memberships : DefaultDict[ConnectionDescriptor, Storage]\
	= DefaultDict(default_factory=lambda con_desc: Storage("data", "permissions", f"group-memberships-{con_desc}"))

# Mapping of groups, to list of all permissions granted to that group
groups : dict[str, set[str]] = {}

class StructuredStorage:
	"""Class which facilitates getting / storing structured PermissionData for appropriate key / channel

	Right now, handles account names only"""

	def __init__(self, key : str, channel : str | None = None):
		self.key = key if not channel else f"channels.{channel}.{key}"
		self.channel = channel
		self.accounts : dict[str: bool] | None = None
		self.initialized_storage = False
		self.storage : Storage | None = None

	def _fetch_data(self):
		if not self.initialized_storage:
			data : dict[str, dict] = self.storage.get(self.key)
			self.accounts: dict[str: bool] = data["@accounts"] if data and "@accounts" in data else None
			self.initialized_storage = True

	def _as_dict(self) -> dict[str, dict]:
		"""Returns this object as a dict, for saving back into the .json"""
		ret = {"accounts": self.accounts}

		return ret

	def has_any_account_permissions(self) -> bool:
		"""Check if we have any account permissions"""
		self._fetch_data()
		return self.accounts is not None

	def check_account_permission(self, user : User) -> PermissionReason | None:
		"""Check permission for account"""
		self._fetch_data()

		account_name = user.account_name
		if self.accounts and account_name in self.accounts:
			reason = PermissionReason(self.accounts[account_name], "account", account_name)
			if self.channel:
				reason.channel = self.channel
			return reason
		return None

	def add_account_permission(self, user : User, value : bool) -> None:
		"""Adds account permission and writes it out to storage"""
		self._fetch_data()
		if self.accounts is None:
			self.accounts = {}
		self.accounts[user.account_name] = value
		self.storage.store(self.key, self._as_dict())

	def delete_account_permission(self, user : User) -> None:
		"""Deletes account permission and writes it out to storage"""
		self._fetch_data()
		# Already no permissions
		if self.accounts is None:
			return
		del self.accounts[user.account_name]

		if len(self.accounts.keys()) > 0:
			self.storage.store(self.key, self._as_dict())
		# No permissions left in this object, delete the key instead
		else:
			self.storage.delete(self.key)

class StructuredPermission(StructuredStorage):
	"""Class which facilitates getting / storing structured PermissionData for appropriate key / channel"""

	def __init__(self, con_desc : ConnectionDescriptor, permission : str, channel : str | None = None):
		super().__init__(f"permissions.{permission}", channel)
		self.storage = permissions[con_desc]

class StructuredCommandPermission(StructuredStorage):
	"""Class which facilitates getting / storing structured PermissionData for appropriate key / channel"""

	def __init__(self, con_desc : ConnectionDescriptor, permission : str, channel : str | None = None):
		super().__init__(f"permissions.{permission}", channel)
		self.storage = permissions[con_desc]

class StructuredGroup(StructuredStorage):
	"""Class which facilitates getting / storing structured PermissionData for appropriate key / channel"""

	def __init__(self, con_desc : ConnectionDescriptor, group : str, channel : str | None = None):
		super().__init__(group, channel)
		self.group = group
		self.storage = group_memberships[con_desc]

	def check_account_permission(self, user: User) -> PermissionReason | None:
		"""Check permission for account"""
		reason = super().check_account_permission(user)
		if reason:
			reason.group = self.group
		return reason

