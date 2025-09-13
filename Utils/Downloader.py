# 📦 Built-in modules
import asyncio
import os

# 📥 Custom modules
from rich.progress import (
	Progress,
	BarColumn,
	TextColumn,
	DownloadColumn,
	TransferSpeedColumn,
	TimeRemainingColumn
)
from .Logger import Logger, Console
from .Config import Config
import httpx

# 💡 Download files concurrently with a themed progress bar, retries, and validation.
async def DownloadFiles(Urls: list[tuple[str, list[str]]], AlbumId: str, MaxConcurrency: int = Config.MaxWorkers, MaxRetries: int = 3):
	# 🌱 Prepare directory
	DownloadDirectory = AlbumId
	if not os.path.exists(DownloadDirectory):
		os.makedirs(DownloadDirectory)
		Logger.info(f'Created directory: {DownloadDirectory}')

	# 🌱 Filter out files that already exist
	UrlsToDownload = [
		(Filename, UrlList) for Filename, UrlList in Urls 
		if not os.path.exists(os.path.join(DownloadDirectory, Filename))
	]
	SkippedCount = len(Urls) - len(UrlsToDownload)
	if SkippedCount > 0:
		Logger.info(f'Skipped {SkippedCount} files that already exist.')

	if not UrlsToDownload:
		Logger.info('All files are already downloaded.')
		return

	# 🌱 Set up themed progress bar (matching logger colors)
	with Progress(
		TextColumn('[progress.description]{task.description}', style='logging.level.info'),
		BarColumn(bar_width=None, complete_style='logging.level.info', finished_style='logging.level.info'),
		TextColumn('[progress.percentage]{task.percentage:>3.1f}%', style='logging.level.info'),
		TextColumn('•', style='bright_black'),
		DownloadColumn(),
		TextColumn('•', style='bright_black'),
		TransferSpeedColumn(),
		TextColumn('•', style='bright_black'),
		TimeRemainingColumn(),
		console=Console
	) as ProgressBar:
		# 🌱 Semaphore for concurrency control
		Semaphore = asyncio.Semaphore(MaxConcurrency)
		Tasks = []

		async def DownloadSingle(Filename: str, UrlList: list[str], Index: int, TotalFiles: int):
			async with Semaphore:
				FilePath = os.path.join(DownloadDirectory, Filename)
				Description = f'({Index + 1}/{TotalFiles}) {Filename}'
				TaskId = ProgressBar.add_task(Description, total=1)  # Placeholder total

				for Url in UrlList:
					for Attempt in range(MaxRetries):
						try:
							async with httpx.AsyncClient(headers=Config.Headers, timeout=30.0, http2=True) as Client:
								async with Client.stream('GET', Url) as Response:
									Response.raise_for_status()
									TotalSize = int(Response.headers.get('Content-Length', 0))
									ProgressBar.update(TaskId, total=TotalSize)

									with open(FilePath, 'wb') as File:
										DownloadedSize = 0
										async for Chunk in Response.aiter_bytes(chunk_size=Config.DownloadChunkSize):
											File.write(Chunk)
											DownloadedSize += len(Chunk)
											ProgressBar.update(TaskId, advance=len(Chunk))

									# 🧪 Validate file size
									if TotalSize > 0 and DownloadedSize != TotalSize:
										raise ValueError(f'Size mismatch: expected {TotalSize}, got {DownloadedSize}')

									ProgressBar.update(TaskId, description=f'[green]✓ {Description}')
									Logger.info(f'Successfully downloaded: {Filename}')
									ProgressBar.remove_task(TaskId)  # Remove completed task
									return

						except (httpx.RequestError, httpx.TimeoutException, ValueError) as E:
							if Attempt == MaxRetries - 1:
								Logger.warning(f'Failed attempt for {Filename} with URL {Url}: {E}')
							else:
								Logger.warning(f'Retry {Attempt + 1}/{MaxRetries} for {Filename} with URL {Url}: {E}')
								await asyncio.sleep(1)  # Brief delay before retry
					else:
						continue  # Try next URL
					break  # Success, exit URL loop
				else:
					# All URLs failed
					ProgressBar.update(TaskId, description=f'[red]✗ Failed: {Filename}', completed=1)
					Logger.error(f'Failed to download {Filename} after trying all URLs.')
					ProgressBar.remove_task(TaskId)  # Remove failed task

		# 🌱 Create and run tasks
		TotalFiles = len(UrlsToDownload)
		for Index, (Filename, UrlList) in enumerate(UrlsToDownload):
			Task = asyncio.create_task(DownloadSingle(Filename, UrlList, Index, TotalFiles))
			Tasks.append(Task)

		await asyncio.gather(*Tasks)