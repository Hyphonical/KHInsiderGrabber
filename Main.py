# 📦 Built-in modules
import urllib.parse
import argparse
import asyncio
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
import httpx

# 💡 Fully unquote a URL string
def FullyUnquote(Url: str) -> str:
	while True:
		UnquotedUrl = urllib.parse.unquote(Url)
		if UnquotedUrl == Url:
			return UnquotedUrl
		Url = UnquotedUrl

# 💡 Extract packed strings
def ExtractPackedStrings(ScriptContent: str) -> list:
	Matches = re.findall(Config.PackedStringPattern, ScriptContent, re.DOTALL)
	return [(Packed, int(A), int(C), KStr.split('|')) for Packed, A, C, KStr in Matches]

# 💡 Extract link IDs from unpacked script
def ExtractLinkIds(UnpackedScript: str, TrackInfoMap: dict) -> list[tuple[str, str, int, int, str]]:
	Matches = re.findall(Config.TrackInfoPattern, UnpackedScript)
	LinkIds = []
	for Name, Url in Matches:
		Name = html.unescape(Name)
		if any(Domain in Url for Domain in Config.ValidUrlDomains):
			Parts = Url.split('/')
			if len(Parts) > 4:
				LinkId = Parts[-2]
				if Name in TrackInfoMap:
					Disc, Track, Filename = TrackInfoMap[Name]
					LinkIds.append((Name, LinkId, Track, Disc, Filename))
				else:
					Logger.warning(f'Could not find track "{Name}" in the page tracklist.')
	return LinkIds

# 💡 Generate direct download links (single base)
def GenerateDownloadLinks(LinkIds: list[tuple[str, str, int, int, str]], AlbumId: str) -> list[tuple[str, str]]:
	if not LinkIds:
		return []
	Links = []
	Base = Config.BaseUrl
	for _, LinkId, _, _, Filename in LinkIds:
		FlacFilename = Filename.replace('.mp3', '.flac')
		Encoded = urllib.parse.quote(FlacFilename, safe='/')
		Links.append((FlacFilename, f'{Base}/{AlbumId}/{LinkId}/{Encoded}'))
	return Links

# 💡 Fetch content and extract link IDs
async def ExtractFromUrl(Url: str) -> list[tuple[str, str, int, int, str]]:
	try:
		async with httpx.AsyncClient(headers=Config.Headers, timeout=30.0, http2=True) as Client:
			Response = await Client.get(Url)
			Response.raise_for_status()
			Soup = BeautifulSoup(Response.content, 'html.parser')

			# 🌱 Track info map (disc, track, original filename)
			TrackInfoMap = {}
			for Link in Soup.select(Config.TracklistSelector):
				TrackName = html.unescape(Link.text)
				Href = Link.get('href', '')
				DecodedHref = FullyUnquote(Href)  # type: ignore
				Filename = os.path.basename(DecodedHref)
				Match = re.search(Config.TrackFilePattern, Filename)
				if Match:
					Groups = Match.groups()
					if Groups[1] is None:
						Disc = 1
						Track = int(Groups[0])
					else:
						Disc = int(Groups[0])
						Track = int(Groups[1])
				else:
					Disc = 1
					Track = 1
				TrackInfoMap[TrackName] = (Disc, Track, Filename)

			ScriptTags = Soup.select(Config.PageContentSelector)
			if not ScriptTags:
				Logger.error(f'ExtractFromUrl: No script tags found in div#pageContent at {Url}')
				return []
			ScriptContent = next((Tag.string for Tag in ScriptTags if Tag.string and Config.PackedScriptIdentifier in Tag.string), None)
			if not ScriptContent:
				Logger.error(f'ExtractFromUrl: No packed script found at {Url}')
				return []

			LinkIds: list[tuple[str, str, int, int, str]] = []
			for Packed, A, C, K in ExtractPackedStrings(ScriptContent):
				Unpacked = UnpackScript(Packed, A, C, K)
				LinkIds.extend(ExtractLinkIds(Unpacked, TrackInfoMap))

			return LinkIds
	except httpx.RequestError as E:
		Logger.error(f'ExtractFromUrl: Failed to fetch URL {Url}: {E}')
		return []

# 🧪 Main execution logic
async def Main():
	class CustomFormatter(RichHelpFormatter):
		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self.width = 120

	Parser = argparse.ArgumentParser(
		description='🎵 Download FLAC albums from downloads.khinsider.com.',
		epilog='Example: python Main.py https://downloads.khinsider.com/game-soundtracks/album/super-mario-galaxy-2',
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
		exit(1)
	AlbumId = Match.group(1)

	Logger.info(f'Extracting from: {AlbumId}')
	LinkIds = await ExtractFromUrl(AlbumUrl)
	if LinkIds:
		Logger.info(
			f'Extracted {len(LinkIds)} tracks over '
			f'{len(set(Disc for _, _, _, Disc, _ in LinkIds))} disc(s).'
		)
		Logger.info(f'Using base URL: {Config.BaseUrl}')
		DownloadLinks = GenerateDownloadLinks(LinkIds, AlbumId)
		Logger.info('Generated download links:')
		for Filename, _ in DownloadLinks:
			Logger.info(f'  - {Filename}')
		Logger.info('Starting download...')
		await DownloadFiles(DownloadLinks, AlbumId)
		Logger.info('All downloads completed.')
	else:
		Logger.warning('Could not extract any song IDs.')

# 🚀 Entry
if __name__ == '__main__':
	try:
		asyncio.run(Main())
	except KeyboardInterrupt:
		Logger.info('Operation cancelled by user.')
		exit(0)