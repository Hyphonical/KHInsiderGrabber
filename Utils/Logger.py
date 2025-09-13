# 📦 Built-in modules
import logging

# 📥 Custom modules
from rich.console import Console as RichConsole
from rich.highlighter import RegexHighlighter
from rich.traceback import install as Install
from rich.logging import RichHandler
from rich.theme import Theme

LogLevel = logging.INFO

# 💡 Custom highlighter for log messages
class Highlighter(RegexHighlighter):
	base_style = 'Logger.'
	highlights = [
		r'(?P<Url>https?://[^\s]+)'
	]


# 🌱 Initialize and define logging
def InitLogging():
	ThemeDict = {
		'log.time': 'bright_black',
		'logging.level.debug': '#B3D7EC',
		'logging.level.info': '#A0D6B4',
		'logging.level.warning': '#F5D7A3',
		'logging.level.error': '#F5A3A3',
		'logging.level.critical': '#ffc6ff',
		'Logger.Url': '#F5D7A3'
	}
	Console = RichConsole(
		theme=Theme(ThemeDict),
		force_terminal=True,
		log_path=False,
		highlighter=Highlighter(),
		color_system='truecolor',
	)

	ConsoleHandler = RichHandler(
		markup=False,
		rich_tracebacks=True,
		show_time=True,
		console=Console,
		show_path=False,
		omit_repeated_times=True,
		highlighter=Highlighter(),
		show_level=True,
	)

	ConsoleHandler.setFormatter(logging.Formatter('│ %(message)s', datefmt='[%H:%M:%S]'))

	logging.basicConfig(level=LogLevel, handlers=[ConsoleHandler], force=True)

	RichLogger = logging.getLogger('rich')
	RichLogger.handlers.clear()
	RichLogger.addHandler(ConsoleHandler)
	RichLogger.propagate = False

	HttpxLogger = logging.getLogger('httpx')
	HttpxLogger.handlers.clear()
	HttpxLogger.addHandler(ConsoleHandler)
	HttpxLogger.propagate = False
	HttpxLogger.setLevel(logging.WARNING)

	return Console, RichLogger, ConsoleHandler, HttpxLogger


Console, Logger, ConsoleHandler, HttpxLogger = InitLogging()
Install()

# 🧪 Logging test messages
if __name__ == '__main__':
	Logger.debug('This is a debug message.')
	Logger.info('This is an info message.')
	Logger.warning('This is a warning message.')
	Logger.error('This is an error message.')
	Logger.critical('This is a critical message.')
