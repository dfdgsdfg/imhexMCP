---
name: Patch Failure
about: Report patches failing to apply to ImHex
title: '[PATCH] Patch XXX fails to apply'
labels: patch-failure
assignees: ''
---

## Patch Information
**Which patch failed?**
- [ ] 0001-feat-Implement-queue-based-file-opening
- [ ] 0002-improvement-Add-detailed-error-logging
- [ ] 0007-fix-Replace-RequestOpenFile
- [ ] 0008-fix-Improve-disassembly-and-diff
- [ ] 0009-fix-Implement-TaskManager-based-diff
- [ ] 0010-feat-Add-batch-open_directory
- [ ] 0011-Add-batch-search-endpoint
- [ ] 0012-Add-batch-hash-endpoint
- [ ] 0013-Fix-glob-pattern-matching
- [ ] 0014-Fix-glob-pattern-escaping

## ImHex Version
**ImHex commit hash:**
```bash
cd ImHex && git rev-parse HEAD
# Paste output here
```

**ImHex branch:**
- [ ] master
- [ ] nightly
- [ ] Other: ___________

## Error Output
```
Paste the error output from git apply here
```

## Steps Taken
1. Cloned ImHex: `git clone https://github.com/WerWolv/ImHex.git`
2. Attempted to apply patches: `./setup-imhex-mcp.sh`
3. ...

## Additional Information
- Did setup script run automatically or did you apply patches manually?
- Any modifications to ImHex before applying patches?
