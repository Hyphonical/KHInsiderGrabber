# 📦 Built-in modules
import difflib
import re

# 📥 Custom modules
from .Extracter import FullyUnquote

# 💡 Fuzzy match a filename to the closest track name
def FuzzyMatchFilename(Filename: str, LinkIds: list[tuple[int, str, str]], Cutoff: float = 0.8) -> tuple[int, str, str] | None:
	'''
	⛏️ Use fuzzy matching to find the best track match for a filename.
	Args:
		Filename (str): The raw filename (e.g., '1-01. Song Title.mp3').
		LinkIds (list[tuple[int, str, str]]): List of (track_num, name, link_id).
		Cutoff (float): Similarity threshold (0.0 to 1.0).
	Returns:
		tuple[int, str, str] | None: Best match or None if no good match.
	'''
	# 🔄 Fully unquote the filename to handle encoded characters like %2520
	UnquotedFilename = FullyUnquote(Filename)
	# 🧹 Clean filename: remove track number prefix and extension for better matching
	CleanName = re.sub(r'^\d+[-.]?\d*[ .]*', '', UnquotedFilename).replace('.mp3', '').strip()

	TrackNames = [Name for _, Name, _ in LinkIds]
	Matches = difflib.get_close_matches(CleanName, TrackNames, n=1, cutoff=Cutoff)

	if Matches:
		MatchedName = Matches[0]
		# 🎯 Find the corresponding full link tuple
		for Link in LinkIds:
			if Link[1] == MatchedName:
				return Link
	return None