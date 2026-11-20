# Protected Curriculum & Assessment Content Storage

To keep private hidden test cases, diagnostic evaluation keys, and reference solutions out of the public Git repository:

1. **Public Git Tracking:** Only `README.md` and `demo_curriculum_fixture.example.json` (a safe minimal schema template) are committed to Git.
2. **Protected Deployment Content (`*.local.json`):** Production or local curated curriculum bundles live in `.gitignore`-protected `*.local.json` files or secure Admin Studio imports (`POST /api/v1/admin/learning/import-bundle`).
3. **Judge0 Verification Gate:** Every imported coding/debugging problem and diagnostic execution item is validated through isolated Judge0 CE workers before it is marked `published`.
