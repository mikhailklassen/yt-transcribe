# Documentation

This directory contains comprehensive documentation for the yt-transcribe project.

## Documentation Structure

```
docs/
├── README.md              # This file - documentation index
├── DEVELOPMENT.md         # Development notes, architecture, and design decisions
├── USAGE.md              # Usage examples and practical scenarios
└── HISTORICAL_REVIEW.md  # Historical project review and analysis
```

## Quick Links

- **[Main README](../README.md)** - User-facing documentation (installation, quick start)
- **[CHANGELOG](../CHANGELOG.md)** - Version history and changes
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Architecture, design decisions, development guidelines
- **[USAGE.md](USAGE.md)** - Detailed usage examples and workflows
- **[HISTORICAL_REVIEW.md](HISTORICAL_REVIEW.md)** - Historical project analysis

## For Contributors

When contributing to this project:

1. **Read first**: Review `DEVELOPMENT.md` for architecture and design patterns
2. **Document changes**: Update `CHANGELOG.md` for all user-facing changes
3. **Update docs**: Modify relevant documentation files as needed
4. **Follow guidelines**: See `DEVELOPMENT.md` for coding standards and practices

## Documentation Guidelines

### Where to Put Documentation

- **User-facing features**: Update the main `README.md` in the project root
- **Code changes**: Update `CHANGELOG.md` in the project root
- **Architecture/design**: Update `docs/DEVELOPMENT.md`
- **Usage examples**: Update `docs/USAGE.md`
- **Historical context**: Keep in `docs/HISTORICAL_REVIEW.md` or `CHANGELOG.md`

### What NOT to Create

❌ **Do NOT create these files:**
- Top-level markdown files for temporary documentation
- Progress tracking files (use TODO lists or GitHub issues)
- Duplicate documentation files
- Files with names like `ACTION_PLAN.md`, `IMPLEMENTATION_SUMMARY.md`, etc.

✅ **DO:**
- Update existing documentation files
- Use TODO lists for temporary task tracking
- Add to `CHANGELOG.md` for change tracking
- Keep documentation in the `docs/` folder

## File Purposes

### Root Directory Files

- `README.md` - Primary user documentation (installation, usage, troubleshooting)
- `CHANGELOG.md` - Version history and change tracking
- `pyproject.toml` - Python project configuration

### Documentation Directory Files

- `docs/README.md` - This file, documentation index and guidelines
- `docs/DEVELOPMENT.md` - Developer documentation, architecture, design decisions
- `docs/USAGE.md` - Comprehensive usage examples and workflows
- `docs/HISTORICAL_REVIEW.md` - Historical project review and analysis

## Maintenance

Documentation should be reviewed and updated:
- When adding new features
- When fixing bugs that affect user behavior
- When architecture changes
- Before major releases
