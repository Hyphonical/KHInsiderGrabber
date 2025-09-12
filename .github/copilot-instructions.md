### Copilot Coding Style Instructions

Use these guidelines to maintain consistency in code generation and modifications:

- **Naming Conventions**:
	- Classes: PascalCase (e.g., `Highlighter`, `RichConsole`)
	- Functions: PascalCase (e.g., `InitLogging`)
	- Variables: PascalCase (e.g., `ThemeDict`, `ConsoleHandler`)
	- Constants: PascalCase (e.g., `ThemeDict`)

- **Sorting Modules**:
	- Sort imports by length from long to short within each group (built-in vs. custom).
	- If lengths are equal, sort alphabetically.

- **Indentation**:
	- Use tabs only for indentation (no spaces). Each level: one tab.

- **Comments**:
	- Add clear, descriptive comments with a fitting prefix emoji.
	- Examples:
		- `# 📦 Built-in modules` for imports
		- `# 📥 Custom modules` for custom imports
		- `# 💡 Custom highlighter for log messages` for explanations
		- `# 🌱 Initialize and define logging` for sections
		- `# 🧪 Logging test messages` for tests

- **Code Structure**:
	- Group imports: Built-in first (# 📦), then custom (# 📥)
	- Use f-strings with single quotes if needed (e.g., `f'{__name__}.'`)
	- Prefer concise, readable code with emoji-prefixed comments for clarity.
	- Limit lines to 100 characters where possible for readability.
	- Use type hints for function parameters and return types when applicable.

Apply these rules to all generated or modified code.