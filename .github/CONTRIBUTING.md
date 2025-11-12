# Contributing to ImHex MCP

Thank you for your interest in contributing to ImHex MCP! This document provides guidelines and instructions for contributing.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Workflow](#development-workflow)
- [Patch Development](#patch-development)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

This project follows a simple code of conduct:
- Be respectful and constructive
- Focus on the technical merits
- Help others learn and grow
- Welcome newcomers

## How Can I Contribute?

### Reporting Bugs
Use the bug report template when creating issues. Include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, architecture, ImHex version)
- Error messages and logs

### Suggesting Features
Use the feature request template. Explain:
- The use case and problem it solves
- Proposed solution
- Any implementation ideas

### Reporting Patch Failures
If patches fail to apply to a newer ImHex version:
- Use the patch failure template
- Include ImHex commit hash
- Include full error output
- This helps us keep patches up-to-date

### Improving Documentation
Documentation improvements are always welcome:
- Fix typos and grammar
- Add examples
- Clarify confusing sections
- Add troubleshooting guides

## Development Workflow

### Setting Up Development Environment

1. **Fork and clone the repository:**
```bash
git clone https://github.com/YOUR_USERNAME/imhexMCP.git
cd imhexMCP
```

2. **Clone ImHex and apply patches:**
```bash
./setup-imhex-mcp.sh
```

3. **Build ImHex:**
```bash
cd ImHex
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug
cmake --build . -j$(nproc)
```

### Making Changes to ImHex Code

1. **Start from clean ImHex with patches applied:**
```bash
cd ImHex
git status  # Should show modified files from patches
```

2. **Make your changes to the ImHex source code**

3. **Test your changes:**
```bash
cd build
cmake --build . -j$(nproc)
./imhex  # Test manually
```

4. **Commit your changes:**
```bash
git add <modified files>
git commit -m "feat: Add new endpoint for XYZ"
```

## Patch Development

### Creating New Patches

If you modify ImHex source code, you need to regenerate patches:

```bash
cd ImHex

# Commit all your changes first
git add .
git commit -m "Your descriptive message"

# Generate patches
git format-patch origin/master..HEAD -o ../patches/

# This creates numbered patch files in patches/
```

### Updating Existing Patches

1. Apply patches to clean ImHex
2. Make your modifications
3. Commit changes
4. Regenerate all patches with new numbering

### Patch Naming Convention

Patches follow this format:
```
NNNN-type-short-description.patch
```

Where:
- `NNNN` = Zero-padded number (0001, 0002, etc.)
- `type` = feat, fix, improvement, etc.
- `short-description` = Kebab-case description

Examples:
- `0001-feat-Implement-queue-based-file-opening.patch`
- `0015-fix-Handle-edge-case-in-batch-search.patch`

### Testing Patches

Before submitting, test that patches apply cleanly:

```bash
# Clone fresh ImHex
git clone https://github.com/WerWolv/ImHex.git ImHex-test
cd ImHex-test

# Apply your patches
git apply --check /path/to/patches/*.patch  # Dry run
git apply /path/to/patches/*.patch          # Actually apply

# Build and test
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . -j$(nproc)
```

## Submitting Changes

### Pull Request Process

1. **Create a feature branch:**
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes and commit:**
```bash
git add .
git commit -m "feat: Add your feature"
```

3. **Push to your fork:**
```bash
git push origin feature/your-feature-name
```

4. **Create Pull Request on GitHub**
   - Use the PR template
   - Fill in all sections
   - Link related issues

### Commit Message Guidelines

Follow conventional commits:
```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `patch`: Patch modifications
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat: Add batch/analyze endpoint for multi-file analysis

Implements new endpoint that combines hash, strings, and magic
operations in a single request for efficiency.

Closes #123
```

### Documentation Updates

If your PR changes functionality:
- Update README.md
- Update PATCH_MANIFEST.md (if patches changed)
- Update ENDPOINTS.md (if endpoints changed)
- Add examples if applicable

## Development Tips

### Local Testing

Test all endpoints after changes:
```bash
cd mcp-server
./venv/bin/python test_binary_analysis.py
```

### Debugging

Enable debug logging in ImHex:
1. Build with `-DCMAKE_BUILD_TYPE=Debug`
2. Check console output when running ImHex
3. Look for `[MCP Plugin]` log messages

### Working with ImHex Updates

When ImHex updates break patches:
1. Clone latest ImHex
2. Try applying patches: `git apply --3way patches/*.patch`
3. Resolve conflicts manually
4. Commit resolutions
5. Regenerate patches
6. Test thoroughly

## Questions?

- Open a discussion on GitHub
- Create an issue with the question label
- Check existing documentation in `docs/`

Thank you for contributing!
