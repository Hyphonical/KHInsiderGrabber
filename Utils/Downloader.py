# 📦 Built-in modules
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import urllib.parse
import os

# 📥 Custom modules
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    TaskID
)
from .Logger import Logger, Console
from .Config import Config
import requests

# 💡 Worker function to download a single file.
def _DownloadFile(Url: str, DownloadDirectory: str, ProgressBar: Progress, TaskId: TaskID, Lock: Lock, TotalFiles: int, CompletedFiles: dict):
	LocalFilename = urllib.parse.unquote(Url.split('/')[-1])
	FilePath = os.path.join(DownloadDirectory, LocalFilename)

	try:
		with requests.get(Url, stream=True, headers=Config.Headers, timeout=30) as Response:
			Response.raise_for_status()
			with open(FilePath, 'wb') as File:
				for Chunk in Response.iter_content(chunk_size=Config.DownloadChunkSize):
					File.write(Chunk)
					ProgressBar.update(TaskId, advance=len(Chunk))
		Logger.info(f'Successfully downloaded: {LocalFilename}')
	except requests.RequestException as E:
		Logger.error(f'Failed to download {LocalFilename}: {E}')
	finally:
		with Lock:
			CompletedFiles['count'] += 1
			Count = CompletedFiles['count']
			ProgressBar.update(TaskId, description=f'[green]Downloading... ({Count}/{TotalFiles})')

# 💡 Download files concurrently using a unified progress bar.
def DownloadFiles(Urls: list[str], AlbumId: str):
	# 🌱 Prepare directory
	DownloadDirectory = AlbumId
	if not os.path.exists(DownloadDirectory):
		os.makedirs(DownloadDirectory)
		Logger.info(f'Created directory: {DownloadDirectory}')

	# 🌱 Filter out files that already exist
	UrlsToDownload = [Url for Url in Urls if not os.path.exists(os.path.join(DownloadDirectory, urllib.parse.unquote(Url.split('/')[-1])))]
	SkippedCount = len(Urls) - len(UrlsToDownload)
	if SkippedCount > 0:
		Logger.info(f'Skipped {SkippedCount} files that already exist.')

	if not UrlsToDownload:
		Logger.info('All files are already downloaded.')
		return

	# 🌱 Get total size for the progress bar
	TotalSize = 0
	with ThreadPoolExecutor(max_workers=Config.MaxWorkers) as Executor:
		Futures = [Executor.submit(requests.head, Url, headers=Config.Headers, timeout=10) for Url in UrlsToDownload]
		for Future in as_completed(Futures):
			try:
				Response = Future.result()
				TotalSize += int(Response.headers.get('content-length', 0))
			except requests.RequestException:
				TotalSize += 0 # Can't determine size, will be handled as 0

	# 🌱 Single progress bar for concurrent downloads
	with Progress(
		TextColumn('{task.description}', justify='left'),
		BarColumn(bar_width=None),
		'[progress.percentage]{task.percentage:>3.1f}%',
		TextColumn('•'),
		DownloadColumn(),
		TextColumn('•'),
		TransferSpeedColumn(),
		TextColumn('•'),
		TimeRemainingColumn(),
		console=Console
	) as ProgressBar:
		TotalFiles = len(UrlsToDownload)
		InitialDescription = f'[green]Downloading... (0/{TotalFiles})'
		TaskId = ProgressBar.add_task(InitialDescription, total=TotalSize)
		CompletedFiles = {'count': 0}
		Locker = Lock()

		with ThreadPoolExecutor(max_workers=Config.MaxWorkers) as Executor:
			Futures = [Executor.submit(_DownloadFile, Url, DownloadDirectory, ProgressBar, TaskId, Locker, TotalFiles, CompletedFiles) for Url in UrlsToDownload]
			for Future in as_completed(Futures):
				Future.result()