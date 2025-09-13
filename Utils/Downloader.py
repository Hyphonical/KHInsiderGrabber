# 📦 Built-in modules
import urllib.parse
import requests
import os

# 📥 Custom modules
from rich.progress import Progress, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from .Logger import Logger, Console
from .Config import Config

# 💡 Try to get content length for all files first (to build a total)
def _ProbeSizes(Urls: list[str]) -> dict[str, int]:
	Sizes = {}
	for Url in Urls:
		Size = 0
		try:
			Head = requests.head(Url, headers=Config.Headers, allow_redirects=True, timeout=10)
			if Head.ok:
				Size = int(Head.headers.get('content-length', 0))
			if Size == 0:
				# 🌱 Fallback: lightweight GET (stream) just to read headers
				Resp = requests.get(Url, headers=Config.Headers, stream=True, timeout=10)
				Resp.close()
				Size = int(Resp.headers.get('content-length', 0)) if Resp.ok else 0
		except requests.exceptions.RequestException:
			Size = 0
		Sizes[Url] = Size
	return Sizes

# 💡 Download files using one unified progress bar
def DownloadFiles(Urls: list[str], AlbumId: str):
	# 🌱 Prepare directory
	DownloadDirectory = AlbumId
	if not os.path.exists(DownloadDirectory):
		os.makedirs(DownloadDirectory)
		Logger.info(f'Created directory: {DownloadDirectory}')

	# 🌱 Size probing (best effort)
	Sizes = _ProbeSizes(Urls)
	TotalPlannedBytes = sum(Size for Size in Sizes.values() if Size > 0)

	# 🌱 Single progress bar with aggregate bytes
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
		TaskDescription = f'[green]0/{len(Urls)} Starting...'
		TaskId = ProgressBar.add_task(TaskDescription, total=TotalPlannedBytes if TotalPlannedBytes > 0 else None)

		CompletedFiles = 0

		for Url in Urls:
			LocalFilename = urllib.parse.unquote(Url.split('/')[-1])
			FilePath = os.path.join(DownloadDirectory, LocalFilename)

			# 💡 Skip existing
			if os.path.exists(FilePath):
				CompletedFiles += 1
				Logger.info(f'File already exists, skipping: {LocalFilename}')
				ProgressBar.update(
					TaskId,
					description=f'[green]{CompletedFiles}/{len(Urls)} {LocalFilename} (skipped)'
				)
				continue

			if Config.DryRun:
				CompletedFiles += 1
				Logger.info(f'[Dry Run] Skipping download of: {LocalFilename}')
				ProgressBar.update(
					TaskId,
					description=f'[green]{CompletedFiles}/{len(Urls)} {LocalFilename} (dry run)'
				)
				continue

			PlannedSize = Sizes.get(Url, 0)

			try:
				with requests.get(Url, stream=True, headers=Config.Headers) as Response:
					Response.raise_for_status()
					ContentLength = int(Response.headers.get('content-length', 0))
					# 🌱 If we did not know size earlier and task total was None, extend total dynamically
					if ContentLength and PlannedSize == 0 and TotalPlannedBytes == 0:
						# First time we learn any size -> set total
						TotalPlannedBytes = ContentLength
						ProgressBar.update(TaskId, total=TotalPlannedBytes)
					elif ContentLength and PlannedSize == 0 and TotalPlannedBytes > 0:
						# Adjust total to include newly discovered size
						TotalPlannedBytes += ContentLength
						ProgressBar.update(TaskId, total=TotalPlannedBytes)

					ProgressBar.update(
						TaskId,
						description=f'[green]{CompletedFiles}/{len(Urls)} {LocalFilename}'
					)

					Written = 0
					with open(FilePath, 'wb') as File:
						for Chunk in Response.iter_content(chunk_size=Config.DownloadChunkSize):
							if not Chunk:
								continue
							File.write(Chunk)
							ChunkLen = len(Chunk)
							Written += ChunkLen
							# 🌱 Advance aggregate task by bytes written
							ProgressBar.update(TaskId, advance=ChunkLen)

							# 💡 If file had unknown size and task total is None, grow total progressively
							if TotalPlannedBytes == 0:
								NewTotal = (ProgressBar.tasks[0].total or 0) + ChunkLen
								ProgressBar.update(TaskId, total=NewTotal)

					Logger.info(f'Successfully downloaded: {LocalFilename}')

			except requests.exceptions.RequestException as e:
				Logger.error(f'Failed to download {Url}: {e}')
				# 💡 If file failed and had an expected size, subtract it so ETA stays sane
				if PlannedSize > 0:
					TotalPlannedBytes -= PlannedSize
					ProgressBar.update(TaskId, total=max(TotalPlannedBytes, ProgressBar.tasks[0].completed))

			CompletedFiles += 1
			ProgressBar.update(
				TaskId,
				description=f'[green]{CompletedFiles}/{len(Urls)} {LocalFilename}'
			)