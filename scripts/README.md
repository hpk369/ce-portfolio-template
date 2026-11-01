# scripts/

- `fetch-customer-data.sh`: copies the synthetic customer profiles into `data/` (gitignored).
  Safe for Claude to run; it only reads from GitHub.
- Scripts that make **live** calls (paid APIs, cloud) also live here, and only you run them.
  Each reads its key from `.env`.
