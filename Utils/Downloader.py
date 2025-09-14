# 📦 Built-in modules
import asyncio
import os

# 📥 Custom modules
from .Logger import Logger
from .Config import Config
import httpx

# 💡 Download or validate files concurrently with progress + retries
async def DownloadFiles(Urls: list[tuple[str, str]], AlbumId: str, MaxConcurrency: int = Config.MaxWorkers, MaxRetries: int = 3, DryRun: bool = Config.DryRun):
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

	# 🔨 Define a worker task for processing each URL
	Semaphore = asyncio.Semaphore(MaxConcurrency)

	async def ProcessUrl(Filename: str, Url: str):
		async with Semaphore:
			for Attempt in range(MaxRetries):
				try:
					async with httpx.AsyncClient(headers=Config.Headers, timeout=Config.Timeout, http2=True) as Client:
						if DryRun:
							# 🧪 Validate URL with a HEAD request
							Response = await Client.head(Url)
							Response.raise_for_status()
							Logger.info(f'Successfully validated: {Filename}')
							return
						else:
							# 📥 Download file with a GET request
							assert DownloadDirectory is not None
							FilePath = os.path.join(DownloadDirectory, Filename)
							async with Client.stream('GET', Url) as Response:
								Response.raise_for_status()
								with open(FilePath, 'wb') as File:
									async for Chunk in Response.aiter_bytes():
										File.write(Chunk)
								Logger.info(f'Successfully downloaded: {Filename}')
								return

				except (httpx.RequestError, httpx.HTTPStatusError) as E:
					if Attempt < MaxRetries - 1:
						Logger.warning(f'Retry {Attempt + 1}/{MaxRetries} for {Filename}: {E}')
						await asyncio.sleep(1)  # Wait before retrying
					else:
						Logger.error(f'Failed to process {Filename} after {MaxRetries} attempts: {E}')

	# 🚀 Create and run all tasks concurrently
	Tasks = [ProcessUrl(Filename, Url) for Filename, Url in UrlsToProcess]
	await asyncio.gather(*Tasks)