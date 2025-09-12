# 📦 Built-in modules
import string
import re

# 📥 Custom modules
from .Config import Config
from .Logger import Logger

# 💡 Functor for a given base to convert strings to natural numbers
class Unbaser(object):
	Alphabet = {
		62: string.digits + string.ascii_lowercase + string.ascii_uppercase,
		95: ''.join(chr(i) for i in range(32, 127))
	}

	def __init__(self, Base: int):
		self.Base = Base
		if 36 < Base < 62:
			if Base not in self.Alphabet:
				self.Alphabet[Base] = self.Alphabet[62][:Base]
		if 2 <= Base <= 36:
			self.Unbase = lambda String: int(String, Base)
		else:
			try:
				self.Dictionary = dict(
					(Cipher, Index) for Index, Cipher in enumerate(self.Alphabet[Base])
				)
			except KeyError:
				raise TypeError('Unsupported base encoding.')
			self.Unbase = self._Dictunbaser

	def __call__(self, String: str) -> int:
		return self.Unbase(String)

	def _Dictunbaser(self, String: str) -> int:
		return sum((self.Base ** Index) * self.Dictionary[Cipher] for Index, Cipher in enumerate(String[::-1]))

# 💡 Strip string lookup table and replace values in source
def _ReplaceStrings(Source: str) -> str:
	Match = re.search(Config.StringReplacementPattern, Source, re.DOTALL)
	if Match:
		Varname, Strings = Match.groups()
		Startpoint = len(Match.group(0))
		Lookup = Strings.split('","')
		Variable = f'{Varname}[%d]'
		for Index, Value in enumerate(Lookup):
			Source = Source.replace(Variable % Index, f'"{Value}"')
		return Source[Startpoint:]
	return Source

# 💡 Unpack the obfuscated JavaScript code to extract link IDs
def UnpackScript(PackedString: str, A: int, C: int, K: list) -> str:
	Payload = PackedString
	Symtab = K
	Radix = A
	Count = C
	if Count != len(Symtab):
		Logger.warning(f'UnpackScript: Symbol table length mismatch: {Count} != {len(Symtab)}')
	try:
		Unbase = Unbaser(Radix)
	except TypeError:
		raise ValueError('Unknown p.a.c.k.e.r. encoding.')
	def Lookup(Match):
		Word = Match.group(0)
		try:
			Sym = Symtab[Unbase(Word)]
			return Sym or Word
		except (IndexError, ValueError):
			return Word
	Payload = Payload.replace('\\\\', '\\').replace("\\'", "'")
	Source = re.sub(r'\b\w+\b', Lookup, Payload, flags=re.ASCII)
	return _ReplaceStrings(Source)