# 📦 Built-in modules
import urllib.parse
import argparse
import requests
import html
import sys
import os
import re

# 📥 Custom modules
from rich_argparse import RichHelpFormatter
from Utils.Downloader import DownloadFiles
from Utils.Unpacker import UnpackScript
from Utils.Config import Config
from Utils.Logger import Logger
from bs4 import BeautifulSoup

# 💡 Fully unquote a URL string by repeatedly decoding it.
def FullyUnquote(Url: str) -> str:
	while True:
		UnquotedUrl = urllib.parse.unquote(Url)
		if UnquotedUrl == Url:
			return UnquotedUrl
		Url = UnquotedUrl

# 💡 Extract packed strings from a script using regex.
def ExtractPackedStrings(ScriptContent: str) -> list:
	# 🌱 This pattern is designed to find and capture the arguments of the packer function.
	Matches = re.findall(Config.PackedStringPattern, ScriptContent, re.DOTALL)
	return [(Packed, int(A), int(C), KStr.split('|')) for Packed, A, C, KStr in Matches]

# 💡 Extract link IDs from the unpacked script.
def ExtractLinkIds(UnpackedScript: str, TrackInfoMap: dict) -> list[tuple[str, str, int, int]]:
	# 🌱 Find all track entries using the pattern matching the unpacked script structure.
	Matches = re.findall(Config.TrackInfoPattern, UnpackedScript)
	LinkIds = []
	for Name, Url in Matches:
		# 💡 Decode HTML entities from the name extracted from JavaScript.
		Name = html.unescape(Name)
		if any(Domain in Url for Domain in Config.ValidUrlDomains):
			Parts = Url.split('/')
			if len(Parts) > 4:
				LinkId = Parts[-2]
				# 💡 Look up disc and track number from the map created from the HTML.
				if Name in TrackInfoMap:
					Disc, Track = TrackInfoMap[Name]
					LinkIds.append((Name, LinkId, Track, Disc))
				else:
					Logger.warning(f'Could not find track "{Name}" in the page tracklist.')
	return LinkIds

# 💡 Generate download links from extracted IDs.
def GenerateDownloadLinks(LinkIds: list[tuple[str, str, int, int]], AlbumId: str) -> list[str]:
	# 🌱 Build full download URLs.
	# 📌 Rule:
	#    - Tracks 1..9: zero-pad to 2 digits (01..09)
	#    - Tracks >=10: no extra padding (10, 99, 100, 171, 1000, ...)
	#    - Disc stays unpadded.
	#    - Separator: '<Disc>-<Track> <Title>.flac' (SPACE, no dot after track).
	if not LinkIds:
		return []
	Links = []
	for Name, LinkId, Track, Disc in LinkIds:
		TrackStr = str(Track)
		if len(TrackStr) == 1:
			TrackStr = TrackStr.zfill(2)
		Filename = f'{Disc}-{TrackStr} {Name}.flac'
		EncodedFilename = urllib.parse.quote(Filename, safe='/')
		Url = f'{Config.BaseUrl}/{AlbumId}/{LinkId}/{EncodedFilename}'
		Links.append(Url)
	return Links

# 💡 Fetch content from a URL and extract link IDs.
def ExtractFromUrl(Url: str) -> list[tuple[str, str, int, int]]:
	try:
		Response = requests.get(Url, headers=Config.Headers)
		Response.raise_for_status()
		Soup = BeautifulSoup(Response.content, 'html.parser')

		# 🌱 Create a map of track names to their disc and track numbers from the HTML.
		TrackInfoMap = {}
		TrackLinks = Soup.select(Config.TracklistSelector)
		for Link in TrackLinks:
			# 💡 Decode HTML entities from the track name in the link text.
			TrackName = html.unescape(Link.text)
			Href = Link.get('href', '')
			# 💡 Fully unquote to handle any level of URL encoding.
			DecodedHref = FullyUnquote(Href) # type: ignore
			Match = re.search(Config.TrackFilePattern, os.path.basename(DecodedHref))
			if Match:
				Disc, Track = map(int, Match.groups())
				TrackInfoMap[TrackName] = (Disc, Track)
			else:
				Logger.warning(f'Could not parse track info from href: {Href}')

		ScriptTags = Soup.select(Config.PageContentSelector)
		if not ScriptTags:
			Logger.error(f'ExtractFromUrl: No script tags found in div#pageContent at {Url}')
			return []
		ScriptContent = next((Tag.string for Tag in ScriptTags if Tag.string and Config.PackedScriptIdentifier in Tag.string), None)
		if not ScriptContent:
			Logger.error(f'ExtractFromUrl: No packed script found at {Url}')
			return []
		LinkIds = []
		for Packed, A, C, K in ExtractPackedStrings(ScriptContent):
			Unpacked = UnpackScript(Packed, A, C, K)
			LinkIds.extend(ExtractLinkIds(Unpacked, TrackInfoMap))
		return LinkIds
	except requests.exceptions.RequestException as E:
		Logger.error(f'ExtractFromUrl: Failed to fetch URL {Url}: {E}')
		return []

# 🧪 Main execution logic
def Main():
	# 🌱 Set up a rich-formatted argument parser
	class CustomFormatter(RichHelpFormatter):
		"""Custom help formatter to tweak rich's output."""
		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self.width = 120 # Adjust width for better readability

	Parser = argparse.ArgumentParser(
		description='🎵 A script to download FLAC albums from downloads.khinsider.com.',
		epilog='Example: python Main.py https://downloads.khinsider.com/game-soundtracks/album/super-mario-galaxy-2',
		formatter_class=CustomFormatter
	)
	Parser.add_argument(
		'Url',
		metavar='<url>',
		type=str,
		help='The full URL of the album to download.'
	)

	# 🌱 Show help and exit if no arguments are provided
	if len(sys.argv) == 1:
		Parser.print_help(sys.stderr)
		sys.exit(1)

	Args = Parser.parse_args()
	AlbumUrl = Args.Url

	# 🌱 Extract album ID from URL
	Match = re.search(Config.AlbumIdPattern, AlbumUrl)
	if not Match:
		Logger.error('Invalid album URL format. Please provide a valid khinsider album URL.')
		exit(1)
	AlbumId = Match.group(1)

	# 🌱 Start the extraction and download process
	Logger.info(f'Extracting from: {AlbumId}')
	LinkIds = ExtractFromUrl(AlbumUrl)
	if LinkIds:
		Logger.info(f'Extracted {len(LinkIds)} tracks spread over {len(set(Disc for _, _, _, Disc in LinkIds))} discs.')
		DownloadLinks = GenerateDownloadLinks(LinkIds, AlbumId)
		Logger.info('Generated download links:')
		for Link in DownloadLinks:
			Logger.info(f'  - {Link}')
		Logger.info('Starting download...')
		DownloadFiles(DownloadLinks, AlbumId)
		Logger.info('All downloads completed.')
	else:
		Logger.warning('Could not extract any song IDs.')

# 🚀 Script entry point
if __name__ == '__main__':
	try:
		Main()
	except KeyboardInterrupt:
		Logger.info('Operation cancelled by user.')
		exit(0)