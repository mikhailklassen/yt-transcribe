# Agent Instructions for yt-transcribe

This document provides specific instructions for AI agents working on this project.

## ⚠️ CRITICAL: Documentation File Management

### DO NOT Create Top-Level Markdown Files

**Agents MUST NOT create new markdown files in the project root directory.**

Instead, work with existing documentation files:

#### ✅ CORRECT: Update Existing Files

- **User-facing changes**: Update `README.md` in the project root
- **Code changes**: Update `CHANGELOG.md` in the project root
- **Architecture/design**: Update `docs/DEVELOPMENT.md`
- **Usage examples**: Update `docs/USAGE.md`
- **Documentation structure**: Update `docs/README.md`

#### ❌ INCORRECT: Creating New Files

**DO NOT create these or similar files:**
- `ACTION_PLAN.md`
- `IMPLEMENTATION_SUMMARY.md`
- `CHANGES_IMPLEMENTED.md`
- `FIXES_SUMMARY.md`
- `QUICK_START.md`
- `CLI_STRUCTURE.md`
- `REPORT_MODE_SUMMARY.md`
- `USAGE_EXAMPLES.md`
- `CHECKLIST.md`
- `TODO.md`
- `PROGRESS.md`
- Any other top-level `.md` files for documentation

### Prefer Updating Existing Files

**When documenting changes:**

1. **Before creating a new file, ask**: "Does this content belong in an existing file?"
2. **Check existing files first**: Review `docs/` folder and root `README.md` and `CHANGELOG.md`
3. **Consolidate information**: Add new content to appropriate existing files
4. **Use TODO lists**: For temporary task tracking, use the todo tool, not markdown files

### Documentation File Organization

```
Project Root:
├── README.md              ← User documentation (update this)
├── CHANGELOG.md           ← Version history (update this)
└── docs/                  ← All other documentation goes here
    ├── README.md          ← Documentation index
    ├── DEVELOPMENT.md     ← Architecture and development notes
    ├── USAGE.md           ← Usage examples and workflows
    └── HISTORICAL_REVIEW.md ← Historical analysis
```

## File Modification Guidelines

### When to Create New Files

Only create new files when:
- Adding new source code modules
- Adding test files
- Adding configuration files (e.g., `.gitignore`, `.env.example`)
- Adding scripts that are part of the project functionality

### When to Update Existing Files

Always prefer updating existing files for:
- Documentation updates
- Change tracking
- Progress notes
- Implementation summaries
- Feature descriptions

## Workflow for Agents

### 1. Before Making Changes

1. Read existing documentation in `docs/` folder
2. Review `CHANGELOG.md` for recent changes
3. Check `README.md` for user-facing features
4. Understand the architecture from `docs/DEVELOPMENT.md`

### 2. During Development

- Use TODO lists for task tracking (not markdown files)
- Add code comments for complex logic
- Update docstrings for modified functions
- Log appropriately using the logging framework

### 3. After Making Changes

1. **Update `CHANGELOG.md`** with changes (in `[Unreleased]` section)
2. **Update `README.md`** if user-facing features changed
3. **Update `docs/DEVELOPMENT.md`** if architecture changed
4. **Update `docs/USAGE.md`** if usage examples changed
5. **Delete any temporary files** created during development

### 4. Documentation Updates

When updating documentation:
- Add to existing sections rather than creating new files
- Keep related information together
- Reference other documentation files when appropriate
- Use clear, concise language

## Example: Correct Documentation Workflow

### Scenario: Adding a New Feature

**❌ WRONG:**
```
Create NEW_FEATURE.md
Create IMPLEMENTATION_NOTES.md
Create FEATURE_SUMMARY.md
```

**✅ CORRECT:**
```
1. Update CHANGELOG.md:
   ## [Unreleased]
   ### Added
   - New feature description

2. Update README.md:
   Add feature to usage section

3. Update docs/DEVELOPMENT.md:
   Add architecture notes if needed

4. Update docs/USAGE.md:
   Add usage examples if applicable
```

## File Naming Conventions

### Source Code Files
- Use snake_case: `my_module.py`
- Place in appropriate package directory

### Documentation Files
- Use UPPERCASE for root files: `README.md`, `CHANGELOG.md`
- Use UPPERCASE for docs: `docs/DEVELOPMENT.md`
- Do NOT create new top-level documentation files

### Temporary Files
- Use TODO lists instead of temporary markdown files
- Clean up any temporary files before completing tasks

## Common Mistakes to Avoid

1. **Creating `ACTION_PLAN.md`** → Use TODO lists instead
2. **Creating `IMPLEMENTATION_SUMMARY.md`** → Update `CHANGELOG.md` instead
3. **Creating `QUICK_START.md`** → Update `README.md` or `docs/USAGE.md` instead
4. **Creating multiple summary files** → Consolidate into `CHANGELOG.md`
5. **Leaving temporary documentation files** → Delete before completing

## Summary

**Key Principles:**
1. ✅ Update existing documentation files
2. ✅ Keep documentation in `docs/` folder
3. ✅ Use TODO lists for temporary tracking
4. ✅ Update `CHANGELOG.md` for all changes
5. ❌ Do NOT create top-level markdown files
6. ❌ Do NOT create temporary documentation files

**Remember:** The goal is to maintain a clean, organized project structure with consolidated documentation, not scattered files across the project root.

