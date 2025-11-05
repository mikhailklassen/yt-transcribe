# Documentation Directory

This directory contains project documentation for developers and maintainers.

## Documentation Structure

```
docs/
├── README.md          # This file - documentation index
└── DEVELOPMENT.md     # Development notes, architecture, and guidelines
```

## For AI Agents Working on This Project

When working on this project, **please follow these guidelines for documentation:**

### 1. Where to Put Documentation

- **User-facing documentation**: Update the main `README.md` in the project root
- **Code changes**: Update `CHANGELOG.md` in the project root
- **Development notes**: Add to `docs/DEVELOPMENT.md`
- **Architecture decisions**: Add to `docs/DEVELOPMENT.md`
- **Historical context**: Add to `CHANGELOG.md` or `docs/DEVELOPMENT.md`

### 2. What NOT to Create

❌ **Do NOT create these files:**
- `ACTION_PLAN.md` - Use TODO lists or GitHub issues instead
- `CHANGES_IMPLEMENTED.md` - Update `CHANGELOG.md` instead
- `FIXES_SUMMARY.md` - Update `CHANGELOG.md` instead
- `IMPLEMENTATION_SUMMARY.md` - Update `CHANGELOG.md` instead
- `CHECKLIST.md` - Use TODO lists or inline comments instead
- `QUICK_TEST.md` - Add to `docs/DEVELOPMENT.md` testing section
- `REVIEW.md` - Add insights to `docs/DEVELOPMENT.md`
- Any other root-level `.md` files for progress tracking

### 3. Documentation Workflow

When implementing changes:

1. **Before coding:**
   - Read `CHANGELOG.md` to understand recent changes
   - Review `docs/DEVELOPMENT.md` for architecture and patterns
   - Check the main `README.md` for user-facing features

2. **During coding:**
   - Use TODO lists for task tracking (temporary)
   - Add code comments for complex logic
   - Update docstrings for modified functions

3. **After coding:**
   - Update `CHANGELOG.md` with changes (in Unreleased section)
   - Update `README.md` if user-facing features changed
   - Add notes to `docs/DEVELOPMENT.md` if architecture changed
   - Delete any temporary progress files created

### 4. Changelog Format

Use this format in `CHANGELOG.md`:

```markdown
## [Unreleased]

### Added
- New features

### Changed
- Changes to existing features

### Fixed
- Bug fixes

### Removed
- Removed features
```

### 5. Development Notes Format

Add to `docs/DEVELOPMENT.md` using these sections:
- **Architecture Overview** - For structural changes
- **Key Design Decisions** - For important choices
- **Historical Issues and Resolutions** - For bug fixes and solutions
- **Known Limitations** - For current constraints
- **Future Enhancements** - For planned improvements

### 6. Git Practices

When committing documentation:

```bash
# Good commit messages
git commit -m "docs: Update CHANGELOG for v0.2.0 features"
git commit -m "docs: Add batch processing notes to DEVELOPMENT.md"

# Clean up temporary files before committing
rm -f ACTION_PLAN.md CHANGES_IMPLEMENTED.md CHECKLIST.md
git add CHANGELOG.md docs/
git commit -m "docs: Consolidate documentation"
```

### 7. Quick Reference

**Updating user documentation:**
- Edit `../README.md`
- Update installation instructions
- Update CLI options and examples
- Update troubleshooting section

**Recording changes:**
- Edit `../CHANGELOG.md`
- Add to `[Unreleased]` section
- Use clear, concise descriptions
- Group related changes

**Development insights:**
- Edit `DEVELOPMENT.md`
- Add to appropriate section
- Include code examples if helpful
- Reference related issues/PRs

## Documentation Maintenance

### Quarterly Review

Every few months, review documentation for:
- [ ] Outdated information
- [ ] New features not documented
- [ ] Changed CLI options
- [ ] New troubleshooting tips
- [ ] Updated dependencies

### Before Major Releases

1. Move `[Unreleased]` changes to new version in CHANGELOG
2. Update README with new features
3. Review DEVELOPMENT.md for accuracy
4. Check all code examples work
5. Update version numbers

## File Purposes

### Root Directory Files

- `README.md` - Primary user documentation (installation, usage, troubleshooting)
- `CHANGELOG.md` - Version history and change tracking
- `pyproject.toml` - Python project configuration
- `.gitignore` - Git ignore patterns

### Documentation Directory Files

- `docs/README.md` - This file, documentation guidelines
- `docs/DEVELOPMENT.md` - Developer documentation

### Files to Avoid

These patterns were problematic in the past:
- Multiple progress tracking files (consolidate into CHANGELOG)
- Multiple planning files (use issues/todos instead)
- Multiple summary files (one CHANGELOG is enough)
- Test instruction files (add to DEVELOPMENT.md)

## Example Workflow

### Scenario: Adding a New Feature

1. **Plan** (use TODO list, not a new .md file)
   ```
   - [ ] Research approach
   - [ ] Implement feature
   - [ ] Update docs
   ```

2. **Implement** (add logging, validation, error handling)

3. **Document:**
   ```bash
   # Update CHANGELOG.md
   ## [Unreleased]
   ### Added
   - New batch processing feature with `--batch` flag
   
   # Update README.md
   Add new CLI option to usage section
   
   # Update DEVELOPMENT.md if needed
   Add notes about batch processing architecture
   ```

4. **Clean up** (delete temporary files)
   ```bash
   # Don't leave these behind:
   rm FEATURE_PLAN.md IMPLEMENTATION_NOTES.md
   ```

### Scenario: Fixing a Bug

1. **Fix the bug**

2. **Document:**
   ```bash
   # Update CHANGELOG.md
   ## [Unreleased]
   ### Fixed
   - Fixed race condition in audio download cleanup
   
   # If it was a significant bug, add to DEVELOPMENT.md
   ## Historical Issues and Resolutions
   ### Bug: Race condition in cleanup
   Problem: ...
   Solution: ...
   ```

## Questions?

If you're an AI agent unsure about documentation:
1. When in doubt, update `CHANGELOG.md`
2. For user-facing changes, update `README.md`
3. For complex changes, add notes to `docs/DEVELOPMENT.md`
4. **Don't create new .md files in the root directory**

## Summary

✅ **DO:**
- Update `CHANGELOG.md` for all changes
- Update `README.md` for user-facing changes
- Update `docs/DEVELOPMENT.md` for architecture changes
- Use TODO lists for temporary task tracking
- Clean up temporary files

❌ **DON'T:**
- Create multiple progress tracking files
- Create new .md files in root directory
- Leave behind temporary documentation
- Duplicate information across files
- Create checklists, action plans, or summary files

Keep documentation **consolidated**, **current**, and **organized** in these three locations:
1. `README.md` (users)
2. `CHANGELOG.md` (history)
3. `docs/DEVELOPMENT.md` (developers)

