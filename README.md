# celine-training-materials
Training Materials for the AI Assistant

## CLI

This repository includes a small CLI to notify `celine-ai-assistant` that new training materials have been committed.

Example:

```bash
uv run celine-training-materials sync-ai-assistant \
  --api http://api.celine.localhost \
  --client-id celine-cli \
  --client-secret '<secret>'
```
