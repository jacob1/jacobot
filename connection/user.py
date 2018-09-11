
class User:
	pass

class DiscordUser(User):

	def __init__(self, user):
		self.user = user

	# TODO: proper permissions, not stored in this file
	def is_owner(self):
		return self.user.name == "jacob1" and self.user.id == "186987207033094146" and self.user.discriminator == "8633"

	@property
	def rawuser(self):
		return self.user

	@property
	def nick(self):
		return self.user.display_name

	@property
	def account_name(self):
		return self.user.name
