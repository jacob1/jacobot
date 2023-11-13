from __future__ import annotations

from permissions.reason import PermissionReason
from permissions.permission_storage import permissions, group_memberships, groups, StructuredPermission, StructuredGroup

from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from connection.context import ConnectionDescriptor, Context
	from connection.user import User

__all__ = ["check_permission", "check_user_permission", "set_permission", "set_user_permission", "del_permission", "del_user_permission",
		   "check_group_membership", "add_group_membership", "del_group_membership", "add_permission_to_group",
		   "add_command_permission_to_group", "list_group_memberships", "list_group_permissions", "list_all_groups",
		   "list_all_user_permissions", "check_command_permission", "check_command_enabled", "check_channel_enabled",
		   "check_global_enabled", "write_all_permissions"]

def check_permission(con_desc : ConnectionDescriptor, permission : str) -> dict | str | bool | None:
	"""Get permission data, could be any arbitrary type, or a dict"""

	return permissions[con_desc].get(permission)

def check_user_permission(con_desc : ConnectionDescriptor, user : User, permission : str, *,
						  channel : str | None = None) -> PermissionReason | None:
	"""Check if a user has permission"""

	# Check if user was granted special permission for this channel
	if channel:
		reason = StructuredPermission(con_desc, permission, channel).check_account_permission(user)
		if reason:
			return reason

	# Normal, server-wide permissions
	reason = StructuredPermission(con_desc, permission).check_account_permission(user)
	if reason:
		return reason

	# Check groups user is a part of
	for group_name, group_permissions in groups.items():
		if permission in group_permissions:
			reason = check_group_membership(con_desc, user, group_name, channel=channel)
			if reason:
				return reason
	return None

def set_permission(con_desc : ConnectionDescriptor, permission : str, value : dict | str | bool) -> None:
	"""Set an unstructured permission"""

	permissions[con_desc].store(permission, value)

def set_user_permission(con_desc : ConnectionDescriptor, user : User, permission : str, value : bool, *,
						channel : str | None = None) -> None:
	"""Set a permission on a user"""

	StructuredPermission(con_desc, permission, channel).add_account_permission(user, value)

def del_permission(con_desc : ConnectionDescriptor, permission : str) -> None:
	"""Deletes a permission. If this is a parent node, deletes all children as well"""

	permissions[con_desc].delete(permission)

def del_user_permission(con_desc : ConnectionDescriptor, user : User, permission : str, *,
						channel : str | str | None = None) -> None:
	"""Deletes a permission from a user"""

	StructuredPermission(con_desc, permission, channel).delete_account_permission(user)

def check_group_membership(con_desc : ConnectionDescriptor, user : User, group : str, *,
						   channel : str | None = None) -> PermissionReason | None:
	"""Check if a user is part of a certain permission group"""

	# Check if user was granted special group membership for this channel
	if channel:
		reason = StructuredGroup(con_desc, group, channel).check_account_permission(user)
		if reason:
			return reason

	reason = StructuredGroup(con_desc, group).check_account_permission(user)
	if reason:
		return reason

	return None

def add_group_membership(con_desc : ConnectionDescriptor, user : User, group : str, *, channel : str | None = None) -> None:
	"""Adds a user to a group"""

	StructuredGroup(con_desc, group, channel).add_account_permission(user, True)

def del_group_membership(con_desc : ConnectionDescriptor, user : User, group : str, *, channel : str | None = None) -> None:
	"""Removes a user from a group"""

	StructuredGroup(con_desc, group, channel).delete_account_permission(user)


def add_permission_to_group(permission : str, group_name : str) -> None:
	"""Add permission to group. All members of this group will automatically have this permission.
	Meant to be run on startup only to initialize group permissions."""
	group = groups.get(group_name)
	if not group:
		groups[group_name] = {permission}
	else:
		group.add(permission)

def add_command_permission_to_group(command_name : str, group_name : str) -> None:
	"""Add command permission to group. All members of this group will automatically have this permission.
	Meant to be run on startup only to initialize group permissions."""
	group = groups.get(group_name)
	if not group:
		groups[group_name] = {f"commands.{command_name}"}
	else:
		group.add(f"commands.{command_name}")

def list_group_memberships(con_desc : ConnectionDescriptor, user : User, *, channel : str | None = None) -> set[str]:
	"""List groups that this user is a member of"""

	found_groups = set()
	for group in groups:
		reason = check_group_membership(con_desc, user, group, channel=channel)
		if reason:
			found_groups.add(group)

	return found_groups

def list_group_permissions(group : str) -> set[str] | None:
	"""Lists all permissions granted by a group"""
	if group in groups:
		return groups[group]
	return None

def list_all_groups() -> list[str]:
	return list(groups.keys())

def _list_permissions(con_desc : ConnectionDescriptor, prefix : str, permission : str | None, user : User, found_permissions : set, *,
					  channel : str = None):
	"""Internal method for list_all_user_permissions"""
	full_permission = f"{prefix}.{permission}" if permission else prefix
	permission_data = StructuredPermission(con_desc, permission, channel)
	for sub_permission in permissions[con_desc].list_subkeys(full_permission):
		if sub_permission == "@accounts":
			continue
		new_key = f"{permission}.{sub_permission}" if permission else sub_permission
		_list_permissions(con_desc, prefix, new_key, user, found_permissions)

	reason = permission_data.check_account_permission(user)
	if reason:
		suffix = f" (in {channel})" if channel else ""
		if reason.flag is True:
			found_permissions.add(f"+{permission}{suffix}")
		elif reason.flag is False:
			found_permissions.add(f"-{permission}{suffix}")

def list_all_user_permissions(con_desc : ConnectionDescriptor, user : User, *, channel : str | None = None) -> set[str]:
	"""List all positive and negative permissions that a user has (outside of groups).
	Expensive iteration currently, as all permissions are fully scanned."""

	found_permissions = set()
	_list_permissions(con_desc, "permissions", None, user, found_permissions)
	_list_permissions(con_desc, f"channels.{channel}.permissions", None, user, found_permissions, channel=channel)

	return found_permissions

def check_command_permission(context : Context, command : str) -> PermissionReason | None:
	"""Checks if sender in this context has permission to run this command"""

	channel_name = None if context.is_private() else context.receiver.name
	return check_user_permission(context.get_connection_descriptor(), context.sender, f"commands.{command}", channel=channel_name)

def check_command_enabled(context : Context, command : str) -> bool:
	"""Checks if a command is enabled in this context"""
	if context.is_private():
		return True
	channel = context.receiver.name

	# First check if it's enabled in channel, and then next, overall
	perm = permissions[context.get_connection_descriptor()].get(f"channels.{channel}.commands.{command}.enabled")
	if perm is True or perm is False:
		return perm
	perm = permissions[context.get_connection_descriptor()].get(f"commands.{command}.enabled")
	if perm is True or perm is False:
		return perm
	return True

def check_channel_enabled(context : Context) -> bool:
	"""Checks if channel in this context has commands / processing enabled"""
	if not context.is_private():
		channel = context.receiver.name
		perm = permissions[context.get_connection_descriptor()].get(f"channels.{channel}.enabled")
		if perm is True or perm is False:
			return perm
	return True

def check_global_enabled(context : Context) -> bool:
	"""Checks if the bot is globally disabled in this context"""
	perm = permissions[context.get_connection_descriptor()].get("global-enabled")
	if perm is True or perm is False:
		return perm
	return True

def write_all_permissions() -> None:
	"""Write out all pending permission and group membership changes"""

	for con_desc, storage in permissions.items():
		storage.write()
	for con_desc, storage in group_memberships.items():
		storage.write()
