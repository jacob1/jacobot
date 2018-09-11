
class Event:
	pass

class LoginEvent(Event):
	pass

class MessageEvent(Event):
	
	def __init__(self, context, message):
		self.context = context
		self.message = message

