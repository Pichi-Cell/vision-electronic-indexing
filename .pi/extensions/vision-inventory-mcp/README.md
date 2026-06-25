# Vision Electronic Indexing Pi Extension

Pi extension for the `vision-electronic-indexing-pi` package. It connects Pi to the bundled Python vision workflow and provides commands for electronics/PCB photo inventory.

## Quick setup

Install the package:

```bash
pi install npm:vision-electronic-indexing-pi
```

Then in Pi:

```text
/vision-inventory-setup
```

Setup creates/checks a Pi-managed Python virtual environment at `~/.pi/agent/vision-inventory/.venv`, installs Python dependencies there when approved, warns that datasheet lookup needs a separate web-search/browser capability, and prompts for Cloudflare Workers AI API token credentials when needed.

On Debian/Ubuntu, Python venv creation may require `python3-venv` or a version-specific package such as `python3.10-venv`. If setup reports that `ensurepip` is unavailable, install the package, remove the incomplete venv with `rm -rf ~/.pi/agent/vision-inventory/.venv`, and rerun `/vision-inventory-setup`.

Credentials are stored at:

```text
~/.pi/agent/vision-inventory/credentials.json
```

The file is written with `chmod 600` when supported. Token input may be visible depending on your Pi UI; avoid entering credentials while screen sharing.

Change them later with:

```text
/vision-inventory-credentials
```

## Recommended workflow

```text
/vision-inventory-agent-bom ./photos ./output
```

The agent workflow:

1. Processes supported images in the folder.
2. Writes raw JSON evidence.
3. Builds `parts_to_lookup.json`.
4. Uses an installed web-search/browser capability to verify datasheets.
5. Writes `datasheet_cache.json`.
6. Regenerates `inventory.csv` and `inventory_evidence.csv`.
7. Summarizes uncertain rows.

## Commands

```text
/vision-inventory-setup
/vision-inventory-credentials
/vision-inventory-restart
/vision-inventory-bom <image_folder> <output_dir> [options]
/vision-inventory-agent-bom <image_folder> <output_dir> [options]
```

- `/vision-inventory-bom` runs only the deterministic image-to-CSV workflow.
- `/vision-inventory-agent-bom` runs the full agent-assisted datasheet-enrichment workflow.
- `/vision-inventory-restart` restarts the local Python vision bridge.

Options are forwarded to `scripts/inventory_folder_to_csv.py`, such as `--recursive`, `--limit`, `--max-side`, and `--jpeg-quality`. The default `--max-side 0` sends images at full resolution; set a positive value to resize.

## Agent tools

- `vision_inventory_process_image` — analyze one electronics/PCB image.
- `vision_inventory_process_folder` — analyze all supported images in a folder.
- `vision_inventory_save` — save inventory output as JSON or quick CSV export. Use `/vision-inventory-bom` for the full BOM/evidence workflow.

## External dependencies not bundled

This package intentionally does **not** bundle:

- Python packages from `requirements.txt`: `mcp`, `requests`, `pillow`, `python-dotenv`; optional `pillow-heif`. Pi setup installs these into the package-managed venv when approved.
- A Pi web-search/browser tool or skill for datasheet lookup.
- Cloudflare Workers AI API token credentials.

## Output

The main output is `inventory.csv`, with columns:

```text
normalized_part
candidate_parts
amount
sighting_count
description
datasheet_url
manufacturer
verified
vision_confidence
needs_review
images
observed_markings
raw_json
notes
```

`inventory_evidence.csv` keeps the non-deduplicated per-image/per-candidate rows. One image can produce multiple rows when it contains multiple different ICs.
