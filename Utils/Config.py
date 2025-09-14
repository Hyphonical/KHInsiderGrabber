import re

# ⚙️ Configuration settings
class Config:
	# 🌱 General
	DryRun = False
	Headers = {'User-Agent': 'KHInsider/2.0'}
	DownloadChunkSize = 8192
	Timeout = 30.0
	CustomFormatterWidth = 120
	DefaultDomain = 'vgmsite.com'
	MetadataUrlTemplate = 'https://vgmtreasurechest.com/soundtracks/{}/khinsider.info.txt'

	# 🌱 Regex Patterns
	PackedStringPattern = (
		r"eval\(function\(p,a,c,k,e,d\)\{.*?\}\('((?:[^']|\\')*)',"
		r"(\d+),"
		r"(\d+),"
		r"'((?:[^']|\\')*)'\.split\('\|'\)"
		r"(?:,[^)]*)?\)"
	)
	StringReplacementPattern = r'var *(_\w+)\=\["(.*?)"\];'
	TrackInfoPattern = r'\{"track":\d+,"name":"([^"]*)","length":"[^"]*","file":"([^"]*)"\}'
	AlbumIdPattern = r'\/album\/([^\/]+)'
	TrackFilePattern = r'(\d+)(?:-(\d+))?[ .].*\.mp3'
	DomainPattern = re.compile(r'([a-z]*\.?vgmsite\.com)')
	NamePattern = re.compile(r'Name: (.*)', re.IGNORECASE)
	YearPattern = re.compile(r'Year: (.*)', re.IGNORECASE)
	PlatformsPattern = re.compile(r'Platforms: (.*)', re.IGNORECASE)
	DevelopedByPattern = re.compile(r'Developed by: (.*)', re.IGNORECASE)
	PublishedByPattern = re.compile(r'Published by: (.*)', re.IGNORECASE)

	# 🌱 Parsing
	PackedScriptIdentifier = 'eval(function(p,a,c,k,e,d)'
	ValidUrlDomains = ['vgmsite.com', 'khinsider.com']

	# 🌱 Downloading
	MaxWorkers = 4

	# 🌱 Argparse
	Description = '🎵 Download FLAC albums from downloads.khinsider.com.'
	ExampleEpilog = 'Example: python {} https://downloads.khinsider.com/game-soundtracks/album/super-mario-galaxy-2'