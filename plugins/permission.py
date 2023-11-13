from common import *
from typing import Optional

import permissions
from connection.user import User
from connection.channel import Channel

if TYPE_CHECKING:
	from connection.context import Context

def get_channel_name(channel_arg : str | None, channel : Channel | None, context : "Context | None" = None):
	"""Common function for validating and returning channel name"""
	if (channel_arg is None) ^ (channel is None):
		raise ShowHelpException()
	# If context was passed, then take the channel the command was sent to as the default
	if context and not channel and not context.is_private():
		channel = context.receiver
	return channel.name if channel else None

def is_permission_manager(context : "Context") -> bool:
	channel = None if context.is_private() else context.receiver
	if (permissions.check_group_membership(context.get_connection_descriptor(), context.sender, "permission-manager", channel=channel)
			or context.sender.is_owner()):
		return True
	return False

def can_grant_permission(context : "Context", permission : str) -> bool:
	if is_permission_manager(context):
		return True
	# Otherwise, can only grant permissions they already have
	channel = None if context.is_private() else context.receiver
	reason = permissions.check_user_permission(context.get_connection_descriptor(), context.sender, permission, channel=channel)
	if reason and (channel or not reason.channel):
		return True
	return False

def can_grant_membership(context : "Context", group : str) -> bool:
	if is_permission_manager(context):
		return True
	# Otherwise, can only grant permissions they already have
	channel = None if context.is_private() else context.receiver
	reason = permissions.check_group_membership(context.get_connection_descriptor(), context.sender, group, channel=channel)
	if reason and (channel or not reason.channel):
		return True
	return False

@command("permission", elevated=True, group_name="permission-manager")
async def permission(context : "Context"):
	"""(permission grant/deny/remove/check/list) Manages permissions. See help text for individual subcommands."""

	raise ShowHelpException()

@subcommand("permission", "grant", elevated=True, group_name="permission-manager")
async def permission_give(context : "Context", channel_arg : Optional[ExactMatchArg("--channel")], channel : Optional[Channel],
						  user : User, permission : str):
	"""(permission grant [--channel <channel>] <user> <permission>) Gives a user a special permission."""

	channel_name = get_channel_name(channel_arg, channel)
	if not can_grant_permission(context, permission):
		await context.reply_in_notice("You can only grant permissions you already have")
		return

	permissions.set_user_permission(context.get_connection_descriptor(), user, permission, True, channel=channel_name)
	channel_part = f" in {channel_name}" if channel_name else ""
	await context.reply(f"Gave '{permission}' to {user}{channel_part}")

@subcommand("permission", "deny", elevated=True, group_name="permission-manager")
async def permission_give(context : "Context", channel_arg : Optional[ExactMatchArg("--channel")], channel : Optional[Channel],
						  user : User, permission : str):
	"""(permission deny [--channel <channel>] <user> <permission>) Denies a user a special permission."""

	channel_name = get_channel_name(channel_arg, channel)

	if not is_permission_manager(context):
		await context.reply_in_notice("Only users with the 'permission-manager' group can deny permissions")
		return

	permissions.set_user_permission(context.get_connection_descriptor(), user, permission, False, channel=channel_name)
	channel_part = f" in {channel_name}" if channel_name else ""
	await context.reply(f"Denied '{permission}' from {user}{channel_part}'")

@subcommand("permission", "remove", elevated=True, group_name="permission-manager")
async def permission_remove(context : "Context", channel_arg : Optional[ExactMatchArg("--channel")], channel : Optional[Channel],
						  user : User, permission : str):
	"""(permission remove [--channel <channel>] <user> <permission>) Removes a special permission from a user."""

	channel_name = get_channel_name(channel_arg, channel, context)
	if not can_grant_permission(context, permission):
		await context.reply_in_notice("You can only remove permissions you already have")
		return

	reason = permissions.check_user_permission(context.get_connection_descriptor(), user, permission, channel=channel_name)
	if reason and reason.group:
		grant_type_part = "already has" if reason.perm_type else "is already denied"
		chan_command_part = " --channel " + channel_name if channel_name else None
		recommended_command_str = f"{config.command_char}group remove{chan_command_part} {user} {permission}"
		msg = f"{user} {grant_type_part} this permission via group '{reason.group}'.To remove the group, use {recommended_command_str}"
		await context.reply_in_notice(msg)
	elif reason and channel and not reason.channel:
		grant_type_part = "already has" if reason.perm_type else "is already denied"
		recommended_command_str = f"{config.command_char}permission remove {user} {permission}"
		await context.reply(f"{user} {grant_type_part} this permission globally. To remove the permission, use {recommended_command_str}")
	elif reason and not channel and reason.channel:
		msg = f"{user} has that permission via a channel-specific flag. Use the \"--channel {reason.channel}\" argument to remove it."
		await context.reply_in_notice(msg)
	elif reason:
		permissions.del_user_permission(context.get_connection_descriptor(), user, permission, channel=reason.channel)
		grant_type = "+" if reason.flag is True else "-"
		channel_part = f" in {reason.channel}" if reason.channel else ""
		await context.reply(f"Removed '{grant_type}{permission}' from {user}{channel_part} ({reason.perm_type} {reason.match_str})")
	else:
		await context.reply_in_notice(f"{user} does not have that permission")

@subcommand("permission", "check")
async def permission_check(context : "Context", channel_arg : Optional[ExactMatchArg("--channel")], channel : Optional[Channel],
						  user : User, permission : str):
	"""(permission check [--channel <channel>] <user> <permission>) Checks if a user has a permission."""

	channel_name = get_channel_name(channel_arg, channel, context)
	if not can_grant_permission(context, permission):
		await context.reply_in_notice("You can only check permissions you already have")
		return

	reason = permissions.check_user_permission(context.get_connection_descriptor(), user, permission, channel=channel_name)
	if reason:
		grant_type = "+" if reason.flag is True else "-"
		channel_part = f" in {reason.channel}" if reason.channel else ""
		group_part = f" via group {reason.group}" if reason.group else ""
		msg = f"{user} has permission '{grant_type}{permission}'{channel_part}{group_part} ({reason.perm_type} {reason.match_str})"
		await context.reply(msg)
	else:
		await context.reply(f"{user} does not have permission '{permission}'")

@subcommand("permission", "list")
async def permission_list(context : "Context", channel_arg : Optional[ExactMatchArg("--channel")], channel : Optional[Channel],
						  user : User):
	"""(permission list [--channel <channel>] <user>) Lists permissions for a user."""

	channel_name = get_channel_name(channel_arg, channel, context)
	if not is_permission_manager(context):
		await context.reply_in_notice("Only users with the 'permission-manager' group can list permissions")
		return

	all_permissions = permissions.list_all_user_permissions(context.get_connection_descriptor(), user, channel=channel_name)
	if not all_permissions:
		msg = (f"{user} has no special permissions, but may be a member of groups."
			   f"Use \"group list-memberships\" to check for group membership and \"group list-perms\" to check granted permissions")
		await context.reply(msg)
	else:
		num_permissions = len(all_permissions)
		s = "s" if num_permissions != 1 else ""
		all_permissions_str = ", ".join(all_permissions)
		await context.reply(f"{user} has {num_permissions} special permission{s}: {all_permissions_str}")

@command("group", elevated=True, group_name="permission-manager")
async def permission(context : "Context"):
	"""(group add/remove/check/list/list-memberships/list-perms) Manages membership in groups. See help text for individual subcommands."""

	raise ShowHelpException()

@subcommand("group", "add", elevated=True, group_name="permission-manager")
async def group_add(context : "Context", channel_arg : Optional[ExactMatchArg("--channel")], channel : Optional[Channel],
					user : User, group : str):
	"""(group add [--channel <channel>] <user> <group>) Adds a user to a group."""

	channel_name = get_channel_name(channel_arg, channel)
	if not can_grant_membership(context, group):
		await context.reply_in_notice("You can only add users to groups you are already a member of")
		return

	permissions.add_group_membership(context.get_connection_descriptor(), user, group, channel=channel_name)
	channel_part = f" in {channel_name}" if channel_name else ""
	await context.reply(f"Added {user} to group \"{group}\"{channel_part}")

@subcommand("group", "remove", elevated=True, group_name="permission-manager")
async def group_remove(context : "Context", channel_arg : Optional[ExactMatchArg("--channel")], channel : Optional[Channel],
						  user : User, group : str):
	"""(group remove [--channel <channel>] <user> <group>) Removes a user from a group."""

	channel_name = get_channel_name(channel_arg, channel, context)
	if not can_grant_membership(context, group):
		await context.reply_in_notice("You can only remove users from groups you are a member of")
		return

	reason = permissions.check_group_membership(context.get_connection_descriptor(), user, group, channel=channel_name)
	if reason and reason.channel and not channel:
		msg = f"{user} has that group via a channel-specific membership. Use the \"--channel {reason.channel}\" argument to remove it."
		await context.reply_in_notice(msg)
	elif reason and not reason.channel and channel:
		msg = f"{user} is a member of that group globally. Drop the \"--channel\" argument to remove the global membership."
		await context.reply_in_notice(msg)
	elif reason:
		permissions.del_group_membership(context.get_connection_descriptor(), user, group, channel=reason.channel)

		channel_part = f" in {reason.channel}" if reason.channel else ""
		await context.reply(f"Removed {user} from group {group}{channel_part} ({reason.perm_type} {reason.match_str})")
	else:
		await context.reply_in_notice(f"{user} is not part of that group")

@subcommand("group", "check")
async def group_check(context : "Context", channel_arg : Optional[ExactMatchArg("--channel")], channel : Optional[Channel],
						  user : User, group : str):
	"""(permission check [--channel <channel>] <user> <group>) Checks if a user is part of a group."""

	channel_name = get_channel_name(channel_arg, channel, context)
	if not can_grant_membership(context, group):
		await context.reply_in_notice("You can only check membership in groups you are a member of")
		return

	reason = permissions.check_group_membership(context.get_connection_descriptor(), user, group, channel=channel_name)
	if reason:
		channel_part = f" in {reason.channel}" if reason.channel else ""
		await context.reply(f"{user} is part of group {group}{channel_part} ({reason.perm_type} {reason.match_str}")
	else:
		await context.reply(f"{user} is not part of group {group}")

@subcommand("group", "list")
async def group_list(context : "Context"):
	"""(group list) Lists all groups."""
	if not is_permission_manager(context):
		await context.reply_in_notice("Only users with the 'permission-manager' group can list groups")
		return

	groups = permissions.list_all_groups()
	await context.reply("Available groups: " + ", ".join(groups))

@subcommand("group", "list-memberships")
async def group_list_memberships(context : "Context", channel_arg : Optional[ExactMatchArg("--channel")], channel : Optional[Channel],
								 user : User):
	"""(group list-memberships [--channel <channel>] <user>) Lists group memberships for a user."""

	channel_name = get_channel_name(channel_arg, channel, context)
	if not is_permission_manager(context):
		await context.reply_in_notice("Only users with the 'permission-manager' group can list group memberships")
		return

	found_groups = permissions.list_group_memberships(context.get_connection_descriptor(), user, channel=channel_name)
	if not found_groups:
		await context.reply(f"{user} is not part of any groups")
	else:
		num_groups = len(found_groups)
		s = "s" if num_groups != 1 else ""
		found_groups_str = ", ".join(found_groups)
		await context.reply(f"{user} is part of {num_groups} group{s}: {found_groups_str}")

@subcommand("group", "list-perms")
async def group_list_perms(context : "Context", group : str):
	"""(group list-perms <group>) Lists all permissions granted by a group."""

	if not can_grant_membership(context, group):
		await context.reply_in_notice("You can only list permissions for groups you are a member of")
		return

	all_permissions = permissions.list_group_permissions(group)
	if not all_permissions:
		await context.reply_in_notice(f"No such group: {group}")
	else:
		all_permissions_str = ", ".join(all_permissions)
		await context.reply(f"{group} has the following permissions: {all_permissions_str}")

@command("channel-enable", elevated=True, group_name="permission-manager")
async def channel_enable(context : "Context", channel : Optional[Channel], enable : Optional[RegexArg("(?:true|false)")]):
	"""(channel-enable [<channel>] [true/false]) Enables or Disables command processing in a channel. Defaults to current channel."""

	if channel is None:
		if context.is_private():
			await context.reply_in_notice("Channel argument required in private")
			return
		channel = context.receiver
	channel_name = channel.name

	if enable is None:
		is_enabled = permissions.check_permission(context.get_connection_descriptor(), f"channels.{channel_name}.enabled")
		permission_str = "enabled" if is_enabled is True or is_enabled is None else "disabled"
		await context.reply(f"Command processing in {channel_name} is {permission_str}")
	elif enable == "false":
		permissions.set_permission(context.get_connection_descriptor(), f"channels.{channel_name}.enabled", False)
		await context.reply(f"Disabled command processing in {channel_name}")
	else:
		permissions.del_permission(context.get_connection_descriptor(), f"channels.{channel_name}.enabled")
		await context.reply(f"Enabled command processing in {channel_name}")

@command("global-enable", elevated=True, group_name="permission-manager")
async def global_enable(context : "Context", channel : Optional[Channel], enable : Optional[RegexArg("(?:true|false)")]):
	"""(global-enable [true/false]) Enables or Disables command processing throughout an entire server."""

	if enable is None:
		is_enabled = permissions.check_permission(context.get_connection_descriptor(), f"global-enabled")
		permission_str = "enabled" if is_enabled is True or is_enabled is None else "disabled"
		await context.reply(f"Command processing on this server is {permission_str}")
	elif enable == "false":
		permissions.set_permission(context.get_connection_descriptor(), f"global-enabled", False)
		await context.reply(f"Disabled command processing on this server")
	else:
		permissions.del_permission(context.get_connection_descriptor(), f"global-enabled")
		await context.reply(f"Enabled command processing on this server")
