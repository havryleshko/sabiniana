# Sabiniana

Monthly cost watch for independent UK dental practices. A practice sends its bills and gets back one page. This repository is the internal engine that makes that page. Customers never log in.

The product note is [research/one-page-summary.md](research/one-page-summary.md). The public page is the React app in [web/](web/). It asks for one bill and does not send it yet.

## Install and test

```bash
uv sync
uv run pytest
```

Nothing in this tree sends a report. Statements dropped in `engine/inbox/` stay on this machine.
