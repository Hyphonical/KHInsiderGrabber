# 📦 Built-in modules
import urllib.parse
import requests
import os

# 📥 Custom modules
from rich.progress import Progress, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from .Logger import Logger, Console
from .Config import Config

# 💡 Download files from a list of URLs with a rich progress bar
def DownloadFiles(Urls: list[str], AlbumId: str):
	# 🌱 Create a directory for the album if it doesn't exist
	DownloadDirectory = AlbumId
	if not os.path.exists(DownloadDirectory):
		os.makedirs(DownloadDirectory)
		Logger.info(f'Created directory: {DownloadDirectory}')

	# 🌱 Set up the outer progress bar for overall file count
	OverallProgress = Progress(
		TextColumn('{task.description}'),
		BarColumn(bar_width=None),
		'[progress.percentage]{task.percentage:>3.1f}%',
		TextColumn('•'),
		TextColumn('[yellow]{task.completed}/{task.total} Files'),
		console=Console
	)

	# 🌱 Set up the inner progress bar for individual file downloads
	DownloadProgress = Progress(
		TextColumn('  [bold blue]↳ {task.description}'),
		BarColumn(bar_width=None),
		'[progress.percentage]{task.percentage:>3.1f}%',
		'•',
		DownloadColumn(),
		'•',
		TransferSpeedColumn(),
		'•',
		TimeRemainingColumn(),
		console=Console,
		transient=True
	)

	with OverallProgress:
		OverallTask = OverallProgress.add_task(f'[green]Downloading {len(Urls)} files', total=len(Urls))

		# 🌱 Download each file
		for Url in Urls:
			LocalFilename = urllib.parse.unquote(Url.split('/')[-1])
			FilePath = os.path.join(DownloadDirectory, LocalFilename)

			# 💡 Skip if file already exists
			if os.path.exists(FilePath):
				Logger.info(f'File already exists, skipping: {LocalFilename}')
				OverallProgress.update(OverallTask, advance=1)
				continue

			# 💡 Skip actual download if DryRun is enabled
			if Config.DryRun:
				Logger.info(f'[Dry Run] Skipping download of: {LocalFilename}')
				OverallProgress.update(OverallTask, advance=1)
				continue

			try:
				with requests.get(Url, stream=True, headers=Config.Headers) as Response:
					Response.raise_for_status()
					TotalSize = int(Response.headers.get('content-length', 0))

					with DownloadProgress:
						DownloadTask = DownloadProgress.add_task(LocalFilename, total=TotalSize)
						with open(FilePath, 'wb') as File:
							for Chunk in Response.iter_content(chunk_size=Config.DownloadChunkSize):
								File.write(Chunk)
								DownloadProgress.update(DownloadTask, advance=len(Chunk))

					Logger.info(f'Successfully downloaded: {LocalFilename}')

			except requests.exceptions.RequestException as e:
				Logger.error(f'Failed to download {Url}: {e}')
			except Exception as e:
				Logger.error(f'An error occurred while downloading {Url}: {e}')

			# 💡 Update overall progress
			OverallProgress.update(OverallTask, advance=1)