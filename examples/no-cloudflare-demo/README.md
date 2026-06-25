# No-Cloudflare Demo

This demo lets you exercise the deterministic CSV/datasheet-cache workflow without Cloudflare credentials or image processing.

Run from the repository root:

```bash
python3 scripts/inventory_folder_to_csv.py ./examples/no-cloudflare-demo/photos ./examples/no-cloudflare-demo/output --skip-vision
```

The command reuses the checked-in mock raw JSON under `output/raw/`, reads `output/datasheet_cache.json`, and regenerates:

- `output/parts_to_lookup.json`
- `output/datasheet_cache.template.json`
- `output/inventory.csv`
- `output/inventory_evidence.csv`

The `photos/` directory is only a placeholder for the positional argument when using `--skip-vision`.
