from __future__ import annotations

import json
import os
import time

def _get_data(node : dict, key : str) -> dict | str | bool | None:
	for k in key.split("."):
		if k not in node:
			return None
		node = node[k]
	return node

def _store_data(node : dict, key : str, value : dict | str | bool) -> None:
	for k in key.split(".")[:-1]:
		if k not in node:
			node[k] = {}
		node = node[k]
	node[key.split(".")[-1]] = value

def _del_data(node : dict, key : str) -> None:
	for k in key.split(".")[:-1]:
		if k not in node:
			node[k] = {}
		node = node[k]
	node_name = key.split(".")[-1]
	if node_name in node:
		del node[node_name]


class Storage:
	def __init__(self, *file_paths : str):
		*folder_path, file_name = file_paths
		folder_path = os.path.join(*folder_path)
		#folder_path, file_name = os.path.join(*file_paths).split()
		if not os.path.isdir(folder_path):
			os.makedirs(folder_path)

		self.dirty = False
		self.json_file_path = os.path.join(folder_path, f"{file_name}.json")
		try:
			with open(self.json_file_path) as f:
				self.data = json.load(f)
		except FileNotFoundError:
			self.data = {}
		except json.decoder.JSONDecodeError:
			print(f"Got json decode error while reading {folder_path}/{file_name}.json, making backup and resetting")
			timestamp = int(time.time())
			os.rename(self.json_file_path, os.path.join(folder_path, f"{file_name}-{timestamp}.json"))
			self.data = {}

	def get(self, key : str) -> dict | str | bool | None:
		return _get_data(self.data, key)

	def store(self, key : str, value : dict | str | bool):
		_store_data(self.data, key, value)
		self.dirty = True

	def delete(self, key : str):
		_del_data(self.data, key)
		self.dirty = True

	def write(self):
		if not self.dirty:
			return
		with open(self.json_file_path, "w") as f:
			dat = json.dumps(self.data)
			f.write(dat)
		self.dirty = False

	def list_subkeys(self, key : str | None) -> list:
		"""List all subkeys. If key isn't a dict, returns empty list. If key is None, returns root subkeys."""
		if key is None:
			return list(self.data.keys())
		else:
			d = self.get(key)
			if type(d) == dict:
				return list(d.keys())
			return []
