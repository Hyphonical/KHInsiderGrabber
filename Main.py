# 📦 Built-in modules
import urllib.parse
import argparse
import asyncio
import re
import sys

# 📥 Custom modules
from Utils.Extracter import ExtractContent, ExtractMP3, ExtractScriptAndIds, FullyUnquote
from Utils.Matcher import FuzzyMatchFilename
from rich_argparse import RichHelpFormatter
from Utils.Downloader import DownloadFiles
from Utils.Config import Config
from Utils.Logger import Logger

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
				Logger.info(f'🚀 Platform(s): {Match.group(1)}')
			elif Match := Config.DevelopedByPattern.match(Line):
				Logger.info(f'👷 Developed by: {Match.group(1)}')
			elif Match := Config.PublishedByPattern.match(Line):
				Logger.info(f'🏢 Published by: {Match.group(1)}')

	# 🏷️ Get MP3 file names
	FileNames = ExtractMP3(Content)
	Logger.info(f'🎵 Found {len(FileNames)} tracks')

	# 📀 Determine number of discs and compute absolute track numbers
	DiscFiles = {}
	for FileName in FileNames:
		Match = re.match(Config.TrackFilePattern, FileName)
		if Match:
			DiscNum = int(Match.group(1)) if Match.group(1) else 1
			TrackNum = int(Match.group(2)) if Match.group(2) else int(Match.group(1))
			if DiscNum not in DiscFiles:
				DiscFiles[DiscNum] = []
			DiscFiles[DiscNum].append((TrackNum, FileName))

	Discs = len(DiscFiles)
	Logger.info(f'📀 Found {Discs} disc(s)')

	# Compute absolute track numbers assuming sequential numbering across discs
	CumulativeTracks = 0
	AbsoluteTracks = {}
	for Disc in sorted(DiscFiles.keys()):
		Tracks = sorted(DiscFiles[Disc], key=lambda x: x[0])
		for TrackNum, FileName in Tracks:
			AbsoluteTrack = CumulativeTracks + TrackNum
			AbsoluteTracks[FileName] = AbsoluteTrack
		CumulativeTracks += len(Tracks)

	# 🪪 Get link IDs and domain from unpacked scripts
	LinkIds, Domain = ExtractScriptAndIds(Content)
	Logger.info(f'🔖 Found {len(LinkIds)} link IDs from scripts')
	LinkIds.sort(key=lambda x: x[0])  # Sort by track number
	LongestName = max((len(Name) for _, Name, _ in LinkIds), default=0) + 2
	DownloadURLs = []
	UsedLinkIds = set() # 💡 Track used link IDs to prevent reuse

	for RawMp3 in FileNames:
		# Get absolute track number
		AbsoluteTrack = AbsoluteTracks.get(RawMp3, None)

		MatchedLink = None
		if AbsoluteTrack is not None:
			# 🎯 Find a direct match using the absolute track number
			for TrackNum, Name, LinkId in LinkIds:
				if TrackNum == AbsoluteTrack and LinkId not in UsedLinkIds:
					MatchedLink = (TrackNum, Name, LinkId)
					break

		# 🔍 Fallback to fuzzy matching if no direct match was found
		if not MatchedLink:
			# 💡 Create a list of available links that haven't been used yet
			AvailableLinks = [link for link in LinkIds if link[2] not in UsedLinkIds]
			MatchedLink = FuzzyMatchFilename(RawMp3, AvailableLinks)
			if MatchedLink:
				Logger.info(f'🔍 Fuzzy matched "{RawMp3}" to "{MatchedLink[1]}"')

		if not MatchedLink:
			Logger.warning(f'🚩 No match found for "{RawMp3}", skipping')
			continue

		TrackNum, Name, LinkId = MatchedLink
		UsedLinkIds.add(LinkId) # Mark this link ID as used

		# 🔄 Fully decode any double-encoded sequences
		CleanMp3 = FullyUnquote(RawMp3)

		# 🎯 Local filename (human readable, spaces not %20)
		FlacFilename = CleanMp3.replace('.mp3', '.flac')

		# 🌐 URL filename (single encoding only, encode parentheses)
		EncodedFilename = urllib.parse.quote(FlacFilename, safe='-._')

		DownloadUrl = f'https://{Domain}/soundtracks/{AlbumName}/{LinkId}/{EncodedFilename}'
		DownloadURLs.append((FlacFilename, DownloadUrl))
		Logger.info(f'💿 Song: {Name.ljust(LongestName)} | ID: {LinkId}')

	# 📊 Log matching summary
	MatchedCount = len(DownloadURLs)
	TotalFiles = len(FileNames)
	if MatchedCount == TotalFiles:
		Logger.info('💯 Successfully matched all songs to their IDs')
	else:
		Logger.warning(f'🚨 Matched {MatchedCount}/{TotalFiles} songs; some may be skipped')

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