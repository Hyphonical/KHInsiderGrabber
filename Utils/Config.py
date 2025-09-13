# ⚙️ Configuration settings
class Config:
	# 🌱 General
	Headers = {'User-Agent': 'KHInsider/1.0'}
	BaseUrl = 'https://vgmsite.com/soundtracks'
	DownloadChunkSize = 8192
	DryRun = False

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
	TrackFilePattern = r'(\d+)-(\d+)[ .].*\.mp3'

	# 🌱 Parsing
	PageContentSelector = 'div#pageContent script'
	PackedScriptIdentifier = 'eval(function(p,a,c,k,e,d)'
	ValidUrlDomains = ['vgmsite.com', 'khinsider.com']
	TracklistSelector = 'table#songlist a[href$=".mp3"]'

	# 🌱 Downloading
	MaxWorkers = 2