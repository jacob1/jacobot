import os
import urllib.request
import urllib.parse
import urllib.error
import bz2
import bson
import sys

class particle():
	def __init__(self, typ, x, y):
		self.type = typ
		self.x = x
		self.y = y
		self.ctype = 0
		self.life = 0
		self.tmp = 0
		self.tmp2 = 0
		self.dcolor = 0
		self.vx = 0.0
		self.vy = 0.0
		self.temp = 0.0

def GetPage(url, cookies = None, headers = None, removeTags = False, getredirect=False, binary=False, fakeuseragent=False):
	try:
		if cookies or fakeuseragent:
			extra_headers = {}
			if cookies:
				extra_headers['Cookie'] = cookies.encode("utf-8")
			if fakeuseragent:
				extra_headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64; rv:80.0) Gecko/20100101 Firefox/80.0"
		else:
			extra_headers = None

		if extra_headers:
			req = urllib.request.Request(url, data=urllib.parse.urlencode(headers).encode("utf-8") if headers else None, headers=extra_headers)
		else:
			req = urllib.request.Request(url, data=urllib.parse.urlencode(headers).encode("utf-8") if headers else None)
		data = urllib.request.urlopen(req, timeout=10)
		page = data.read()
		if not binary:
			page = page.decode("utf-8", errors="replace")
		url = data.geturl()
		if removeTags and not binary:
			return re.sub("<.*?>", "", page)
		return url if getredirect else page
	except urllib.error.URLError:
	#except IOError:
		return None

def DownloadSave(ID, *, force=False):
	savefilename = "saves/{0}.cps".format(ID)
	if not force and os.path.exists(savefilename):
		return
	save = GetPage("https://static.powdertoy.co.uk/{0}.cps".format(ID), binary=True)
	if not save:
		return False
	savefile = open(savefilename, "wb")
	savefile.write(save)
	savefile.close()
	return True

def GetSaveData(ID):
	compressedsave = open("saves/{0}.cps".format(ID), "rb")
	compressedsave.seek(12)
	save = bz2.decompress(compressedsave.read())
	try:
		data = bson.loads(save)
	except (ValueError, IndexError):
		return None
	return data

def ValidateSize(curPos, size, numBytes, name):
	if curPos + numBytes > size:
		raise Exception(f"Ran past particle data buffer while loading {name}")

def ParseParts(partsData, partsPosData):
	i = 0
	size = len(partsData)
	partsPosIndex = 0
	partsPosSize = len(partsPosData)
	if partsPosSize != 612 * 384 * 3:
		print("Incorrect particle position data size")
		return
	parts = []
	for y in range(0, 384):
		for x in range(0, 612):
			numParts = (partsPosData[partsPosIndex] << 16) + (partsPosData[partsPosIndex + 1] << 8) + partsPosData[partsPosIndex + 2]
			partsPosIndex += 3

			for posCount in range(0, numParts):
				part = {}

				if i + 3 >= size:
					raise Exception("Ran past particle data buffer")
				fieldDescriptor = partsData[i + 1] + (partsData[i + 2] << 8)

				typ = partsData[i]
				if fieldDescriptor & 0x4000:
					typ |= partsData[i + 3]
					i += 1
				part = particle(typ, x, y)
				i += 3

				if fieldDescriptor & 0x01:
					part.temp = partsData[i] + (partsData[i + 1] << 8)
					i += 2
				else:
					part.temp = partsData[i] + 294.15
					i += 1

				if fieldDescriptor & 0x02:
					ValidateSize(i, size, 1, "life")
					part.life = partsData[i]
					i += 1
					if fieldDescriptor & 0x04:
						ValidateSize(i, size, 1, "life")
						part.life |= partsData[i] << 8
						i += 1

				if fieldDescriptor & 0x08:
					ValidateSize(i, size, 1, "tmp")
					part.tmp = partsData[i]
					i += 1
					if fieldDescriptor & 0x10:
						ValidateSize(i, size, 1, "tmp")
						part.tmp |= partsData[i] << 8
						i += 1
						if fieldDescriptor & 0x1000:
							ValidateSize(i, size, 2, "tmp")
							part.tmp |= partsData[i] << 24
							part.tmp |= partsData[i + 1] << 16
							i += 2

				if fieldDescriptor & 0x20:
					ValidateSize(i, size, 1, "ctype")
					part.ctype = partsData[i]
					i += 1
					if fieldDescriptor & 0x200:
						ValidateSize(i, size, 3, "ctype")
						part.ctype |= partsData[i] << 24
						part.ctype |= partsData[i + 1] << 16
						part.ctype |= partsData[i + 2] << 8
						i += 3

				if fieldDescriptor & 0x40:
					ValidateSize(i, size, 4, "deco")
					part.dcolor = (partsData[i] << 24) + (partsData[i + 1] << 16) + (partsData[i + 2] << 8) + partsData[i + 3]
					i += 4
	
				if fieldDescriptor & 0x80:
					ValidateSize(i, size, 1, "vx")
					part.vx = (partsData[i] - 127.0) / 16.0
					i += 1

				if fieldDescriptor & 0x100:
					ValidateSize(i, size, 1, "vy")
					part.vy = (partsData[i] - 127.0) / 16.0
					i += 1

				if fieldDescriptor & 0x400:
					ValidateSize(i, size, 1, "tmp2")
					part.tmp2 = partsData[i]
					i += 1
					if fieldDescriptor & 0x800:
						ValidateSize(i, size, 1, "tmp2")
						part.tmp2 |= partsData[i] << 8
						i += 1
	
				if fieldDescriptor & 0x2000:
					ValidateSize(i, size, 4, "pavg")
					part.pavg0 = partsData[i] + (partsData[i + 1] << 8)
					part.pavg1 = partsData[i + 2] + (partsData[i + 3] << 8)
					i += 4
					# QRTZ, GLAS, TUNG
					if typ == 132 or typ == 45 or type == 171:
						part.pavg0 = part.pavg0 / 64.0
						part.pavg1 = part.pavg1 / 64.0
	
				parts.append(part)
	return parts

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print("Need save ID")
		sys.exit(1)
	saveId = sys.argv[1]
	DownloadSave(saveId)
	savedata = GetSaveData(saveId)
	if not "parts" in savedata:
		print("Save has no parts")
		sys.exit(0)
	parts = ParseParts(savedata["parts"], savedata["partsPos"])
	#print(savedata)

	print(len(parts))
	num_deco = 0
	for part in parts:
		if part.dcolor != 0:
			num_deco += 1
	print(num_deco)

def ValidateSave(saveId):
	if not DownloadSave(saveId):
		return 0, 0
	savedata = GetSaveData(saveId)
	if not "parts" in savedata:
		return 0, 0
	parts = ParseParts(savedata["parts"], savedata["partsPos"])

	numDeco = 0
	for part in parts:
		#if (part.dcolor != 0 and part.type == 28) or part.type == 147: #Has deco or is EMBR
		if part.dcolor or part.type == 147:
			numDeco += 1
	return len(parts), numDeco

