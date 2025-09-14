# 📦 Built-in modules
import asyncio
import httpx
import os

# 📥 Custom modules
from rich.progress import (
	TimeRemainingColumn,
	TransferSpeedColumn,
	DownloadColumn,
	TextColumn,
	BarColumn,
	Progress
)
from .Logger import Logger, Console
from .Config import Config

# 💡 Download or validate files concurrently with progress + retries
async def DownloadFiles(Urls: list[tuple[str, str]], AlbumId: str, MaxConcurrency: int = Config.MaxWorkers, MaxRetries: int = 3, DryRun: bool = False):
	# 🌱 Prepare directory and filter URLs if not a dry run
	DownloadDirectory: str | None = None
	UrlsToProcess: list[tuple[str, str]] = []

	if not DryRun:
		DownloadDirectory = AlbumId
		if not os.path.exists(DownloadDirectory):
			os.makedirs(DownloadDirectory)
			Logger.info(f'Created directory: {DownloadDirectory}')

		# 🌱 Filter out files that already exist
		for Filename, Url in Urls:
			if not os.path.exists(os.path.join(DownloadDirectory, Filename)):
				UrlsToProcess.append((Filename, Url))

		SkippedCount = len(Urls) - len(UrlsToProcess)
		if SkippedCount > 0:
			Logger.info(f'Skipped {SkippedCount} files that already exist.')

		if not UrlsToProcess:
			Logger.info('All files are already downloaded.')
			return
	else:
		UrlsToProcess = Urls
		Logger.info('Dry run mode: Validating URLs without downloading.')

	# 🌱 Define progress bar columns
	if DryRun:
		ProgressBarColumns = [
			TextColumn('[progress.description]{task.description}', style='logging.level.info'),
			BarColumn(bar_width=None, complete_style='logging.level.info', finished_style='logging.level.info'),
			TextColumn('[progress.percentage]{task.percentage:>3.1f}%', style='logging.level.info'),
			TextColumn('•', style='bright_black'),
			TextColumn('Validating...', style='logging.level.info'),
		]
	else:
		ProgressBarColumns = [
			TextColumn('[progress.description]{task.description}', style='logging.level.info'),
			BarColumn(bar_width=None, complete_style='logging.level.info', finished_style='logging.level.info'),
			TextColumn('•', style='bright_black'),
			DownloadColumn(),
			TextColumn('•', style='bright_black'),
			TransferSpeedColumn(),
			TextColumn('•', style='bright_black'),
			TimeRemainingColumn(),
		]

	# 🔨 Define a worker task for processing each URL
	async def ProcessUrl(Filename: str, Url: str, TaskId, ProgressBar, Description: str):
		for Attempt in range(MaxRetries):
			try:
				async with httpx.AsyncClient(headers=Config.Headers, timeout=Config.Timeout, http2=True) as Client:
					if DryRun:
						# 🧪 Validate URL with a HEAD request
						Response = await Client.head(Url)
						Response.raise_for_status()
						ProgressBar.update(TaskId, completed=1, description=f'[green]✓[/green] {Description}')
						Logger.info(f'Successfully validated: {Filename}')
						return
					else:
						# 📥 Download file with a GET request
						assert DownloadDirectory is not None
						FilePath = os.path.join(DownloadDirectory, Filename)
						async with Client.stream('GET', Url) as Response:
							Response.raise_for_status()
							TotalSize = int(Response.headers.get('Content-Length', 0))
							ProgressBar.update(TaskId, total=TotalSize)
							with open(FilePath, 'wb') as File:
								if TotalSize > 0:
									async for Chunk in Response.aiter_bytes():
										File.write(Chunk)
										ProgressBar.update(TaskId, advance=len(Chunk))
							ProgressBar.update(TaskId, description=f'[green]✓[/green] {Description}')
							Logger.info(f'Successfully downloaded: {Filename}')
							return
			except (httpx.RequestError, httpx.HTTPStatusError) as E:
				if Attempt < MaxRetries - 1:
					Logger.warning(f'Retry {Attempt + 1}/{MaxRetries} for {Filename}: {E}')
					await asyncio.sleep(Attempt + 1) # 💡 Exponential backoff
				else:
					ProgressBar.update(TaskId, description=f'[red]✗[/red] {Description}')
					Logger.error(f'Failed to process {Filename} after {MaxRetries} attempts.')
					return # 💡 Return to prevent removing task again

	# 🚀 Create and run all tasks concurrently
	Semaphore = asyncio.Semaphore(MaxConcurrency)
	with Progress(*ProgressBarColumns, console=Console) as ProgressBar:
		Tasks = []
		TotalFiles = len(UrlsToProcess)
		for Index, (Filename, Url) in enumerate(UrlsToProcess):
			async def StartTask(Filename, Url, Index):
				async with Semaphore:
					Description = f'({Index + 1}/{TotalFiles}) {Filename}'
					TaskId = ProgressBar.add_task(Description, total=1 if DryRun else None, start=True)
					await ProcessUrl(Filename, Url, TaskId, ProgressBar, Description)
					if TaskId in ProgressBar.task_ids: # 💡 Safely remove task
						ProgressBar.remove_task(TaskId)
			Tasks.append(asyncio.create_task(StartTask(Filename, Url, Index)))
		await asyncio.gather(*Tasks)