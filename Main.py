# 📦 Built-in modules
import urllib.parse
import argparse
import asyncio
import html
import sys
import re

# 📥 Custom modules
from rich_argparse import RichHelpFormatter
from Utils.Downloader import DownloadFiles
from Utils.Unpacker import UnpackScript
from Utils.Config import Config
from Utils.Logger import Logger
import httpx

# 💡 Fully unquote repeatedly (handles %2520 -> %20 -> space)
def FullyUnquote(Value: str) -> str:
	'''
	⛏️ Repeatedly unquote a percent-encoded string until stable.
	Example:
		'%2520' -> '%20' -> ' '
	'''
	Previous = Value
	while True:
		Decoded = urllib.parse.unquote(Previous)
		if Decoded == Previous:
			return Decoded
		Previous = Decoded

# 💡 Extract the content of a given URL (now async)
async def ExtractContent(Url: str) -> str:
	'''
	⛏️ Extract the content of a given URL asynchronously.
	Args:
		Url (str): The URL to extract content from.
	Returns:
		str: The content of the URL as a string.
	Example:
		>>> await ExtractContent('https://downloads.khinsider.com/game-soundtracks/album/five-nights-at-freddy-s-fnaf')
		'<!DOCTYPE html>...'
	'''
	async with httpx.AsyncClient(http2=True) as Client:
		Response = await Client.get(Url, headers=Config.Headers, timeout=Config.Timeout)
		if Response.status_code == 200:
			return Response.text
		else:
			Logger.error(f'Failed to fetch URL: {Url} with status code {Response.status_code}')
			return ''

# 💡 Extract MP3 links from a given URL content
def ExtractMP3(Content: str) -> list[str]:
	'''
	⛏️ Extract MP3 links from a given URL content.
	Args:
		Content (str): The HTML content of the URL to extract MP3 links from.
	Returns:
		list[str]: A list of extracted MP3 links.
	Example:
		>>> ExtractMP3('<html>...</html>')
		['Ambience%25202.mp3', 'Ballasthummedium2.mp3', ...]
	'''
	Matches = re.findall(r'<a[^>]+href=["\'].*\/([^"\']+\.mp3)["\']', Content, re.IGNORECASE)
	if Matches:
		Matches = list(set(Matches))
		Matches.sort()
		return Matches
	else:
		Logger.warning('No MP3 links found in the content')
		return []

# 💡 Extract packed strings from script content
def ExtractPackedStrings(ScriptContent: str) -> list[tuple[str, int, int, list[str]]]:
	'''
	⛏️ Extract packed strings and their parameters from script content.
	Args:
		ScriptContent (str): The script content to parse.
	Returns:
		list[tuple[str, int, int, list[str]]]: List of (packed_string, A, C, K) tuples.
	'''
	Matches = re.findall(Config.PackedStringPattern, ScriptContent, re.DOTALL)
	return [(Packed, int(A), int(C), KStr.split('|')) for Packed, A, C, KStr in Matches]

# 💡 Extract link IDs from unpacked script using regex
def ExtractLinkIds(UnpackedScript: str) -> list[tuple[str, str]]:
	'''
	⛏️ Extract song names and link IDs from unpacked script.
	Args:
		UnpackedScript (str): The unpacked JavaScript string.
	Returns:
		list[tuple[str, str]]: List of (song_name, link_id) tuples.
	Example:
		>>> ExtractLinkIds('...unpacked script...')
		[('Song Name', 'link_id'), ...]
	'''
	Matches = re.findall(Config.TrackInfoPattern, UnpackedScript)
	LinkIds = []
	for Name, Url in Matches:
		Name = html.unescape(Name)
		if any(Domain in Url for Domain in Config.ValidUrlDomains):
			Parts = Url.split('/')
			if len(Parts) > 4:
				LinkId = Parts[-2]
				LinkIds.append((Name, LinkId))
			else:
				Logger.warning(f'Invalid URL format for "{Name}": {Url}')
	return LinkIds

# 💡 Extract domain from unpacked script using regex
def ExtractDomain(UnpackedScript: str) -> str:
	'''
	⛏️ Extract the domain from the unpacked script.
	Args:
		UnpackedScript (str): The unpacked JavaScript string.
	Returns:
		str: The extracted domain (e.g., 'vgmsite.com').
	Example:
		>>> ExtractDomain('...unpacked script...')
		'vgmsite.com'
	'''
	Match = Config.DomainPattern.search(UnpackedScript)
	if Match:
		return Match.group(1)
	else:
		Logger.warning('Domain not found in unpacked script')
		return Config.DefaultDomain  # Use config fallback

# 💡 Extract and unpack scripts, then get link IDs
def ExtractScriptAndIds(Content: str) -> tuple[list[tuple[str, str]], str]:
	'''
	⛏️ Extract scripts, unpack them, and get link IDs and domain.
	Args:
		Content (str): The HTML content to extract scripts from.
	Returns:
		tuple: (list of (song_name, link_id) tuples, domain string).
	Example:
		>>> ExtractScriptAndIds('<html>...</html>')
		([('Song Name', 'link_id'), ...], 'vgmsite.com')
	'''
	# Find script tags
	ScriptTags = re.findall(r'<script[^>]*>(.*?)</script>', Content, re.DOTALL)
	if not ScriptTags:
		Logger.warning('No script tags found')
		return [], ''

	AllLinkIds = []
	Domain = ''
	for ScriptContent in ScriptTags:
		if Config.PackedScriptIdentifier in ScriptContent:
			PackedList = ExtractPackedStrings(ScriptContent)
			for Packed, A, C, K in PackedList:
				try:
					Unpacked = UnpackScript(Packed, A, C, K)
					if not Domain:
						Domain = ExtractDomain(Unpacked)
					LinkIds = ExtractLinkIds(Unpacked)
					AllLinkIds.extend(LinkIds)
				except Exception as E:
					Logger.error(f'Failed to unpack script: {E}')

	if not AllLinkIds:
		Logger.warning('No link IDs found in any script')
	return AllLinkIds, Domain

async def Main():
	class CustomFormatter(RichHelpFormatter):
		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self.width = Config.CustomFormatterWidth

	Parser = argparse.ArgumentParser(
		description=Config.Description,
		epilog=Config.ExampleEpilog.format(sys.argv[0]),
		formatter_class=CustomFormatter
	)
	Parser.add_argument('Url', metavar='<url>', type=str, help='Full album URL.')

	if len(sys.argv) == 1:
		Parser.print_help(sys.stderr)
		sys.exit(1)

	Args = Parser.parse_args()
	AlbumUrl = Args.Url

	Match = re.search(Config.AlbumIdPattern, AlbumUrl)
	if not Match:
		Logger.error('Invalid album URL format.')
		sys.exit(1)
	AlbumName = Match.group(1)

	# 🌱 Main execution
	Logger.info(f'🎬 Processing album: {AlbumName}')
	# 📡 Fetch metadata and album content concurrently
	MetadataUrl = Config.MetadataUrlTemplate.format(AlbumName)
	Metadata, Content = await asyncio.gather(
		ExtractContent(MetadataUrl),
		ExtractContent(AlbumUrl)
	)

	if Metadata:
		for Line in Metadata.splitlines():
			if Match := Config.NamePattern.match(Line):
				Logger.info(f'🎮 Game: {Match.group(1)}')
			elif Match := Config.YearPattern.match(Line):
				Logger.info(f'📅 Year: {Match.group(1)}')
			elif Match := Config.PlatformsPattern.match(Line):
				Logger.info(f'🚀 Platforms: {Match.group(1)}')
			elif Match := Config.DevelopedByPattern.match(Line):
				Logger.info(f'👷 Developed by: {Match.group(1)}')
			elif Match := Config.PublishedByPattern.match(Line):
				Logger.info(f'🏢 Published by: {Match.group(1)}')

	# 🏷️ Get MP3 file names
	FileNames = ExtractMP3(Content)
	Logger.info(f'🎵 Found {len(FileNames)} tracks')

	# 📀 Determine number of discs
	Discs = 0
	for FileName in FileNames:
		Match = re.match(Config.TrackFilePattern, FileName)
		if Match:
			DiscNum = int(Match.group(1)) if Match.group(1) else 1
			if DiscNum > Discs:
				Discs = DiscNum

	Logger.info(f'📀 Found {Discs} disc(s)')

	# 🪪 Get link IDs and domain from unpacked scripts
	LinkIds, Domain = ExtractScriptAndIds(Content)
	LongestName = max((len(Name) for Name, _ in LinkIds), default=0) + 2
	DownloadURLs = []
	for Name, LinkId in LinkIds:
		Index = LinkIds.index((Name, LinkId))
		RawMp3 = FileNames[Index]

		# 🔄 Fully decode any double-encoded sequences
		CleanMp3 = FullyUnquote(RawMp3)

		# 🎯 Local filename (human readable, spaces not %20)
		FlacFilename = CleanMp3.replace('.mp3', '.flac')

		# 🌐 URL filename (single encoding only)
		EncodedFilename = urllib.parse.quote(FlacFilename, safe='-._()')

		DownloadUrl = f'https://{Domain}/soundtracks/{AlbumName}/{LinkId}/{EncodedFilename}'
		DownloadURLs.append((FlacFilename, DownloadUrl))
		Logger.info(f'💿 Song: {Name.ljust(LongestName)} | ID: {LinkId}')

	# 📥 Start downloading
	Logger.info('Starting download...')
	await DownloadFiles(DownloadURLs, AlbumName)
	Logger.info('All downloads completed.')

if __name__ == '__main__':
	try:
		asyncio.run(Main())
	except KeyboardInterrupt:
		Logger.info('Process interrupted by user. Exiting...')
		sys.exit(0)
	except Exception as E:
		Logger.error(f'An unexpected error occurred: {E}')
		sys.exit(1)