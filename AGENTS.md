# Multi-Region PostgreSQL Testing Dashboard - Agent Guidelines

## Build Commands
- **Setup**: `just setup` - Install dev dependencies and create .env file
- **Dev Server**: `just dev` - Run development server with reload
- **Format**: `just format` - Format code with black (line-length: 100)
- **Lint**: `just lint` - Run ruff checks
- **Type Check**: `just typecheck` - Run mypy type checking
- **All Checks**: `just check` - Run lint + typecheck
- **Clean**: `just clean` - Remove Python cache files

## Code Style Guidelines
- **Formatting**: Black with 100 character line length
- **Imports**: Use ruff/isort, first-party imports: `app`
- **Type Hints**: Use modern union syntax (`str | None`), mypy in strict mode with some relaxations
- **Error Handling**: Use FastAPI's built-in error responses, graceful degradation for feature flags
- **Naming**: snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants
- **Async**: Use async/await throughout, all database operations are async
- **Environment**: Use .env file, never commit secrets, use dataclasses for config
- **Dependencies**: Add with `just add <package>` or `just add-dev <package>` for dev dependencies