# Vision Electronic Indexing MCP — Improvement Plan

This document lists improvable points selected for implementation consideration. Each entry explains why the improvement is useful and suggests a possible solution.

## Active improvement candidates

### 1. Pin or constrain Python dependency versions in `requirements.txt`

**Why it is needed:**  
The current dependency list uses unpinned package names. Future releases of `mcp`, `pillow`, `requests`, or `python-dotenv` could introduce breaking changes or behavior differences, making installs less reproducible.

**Possible solution:**  
Use conservative version ranges instead of fully unbounded dependencies, for example:

```text
mcp>=1.0,<2.0
requests>=2.31,<3.0
pillow>=10.0,<12.0
python-dotenv>=1.0,<2.0
```

Exact bounds should be chosen after testing with the current environment.

---

### 2. Clarify whether `.universal/setup/install.sh` and `install.ps1` are legacy/manual or remove them

**Why it is needed:**  
The repository has both `.universal/scripts/quick-install.sh` and older-looking setup scripts under `.universal/setup/`. The quick installer performs a more complete setup, while the setup scripts mostly install dependencies and tell the user to manually copy configs. This can confuse users about which installer is recommended.

**Possible solution:**  
Either:

- mark `.universal/setup/install.sh` and `install.ps1` as “manual/legacy setup helpers” in comments and docs, or
- remove them if `quick-install.sh` is now the intended universal installer.

If kept, the README should clearly say which installer is recommended.

---

### 3. Add a short “choose your install path” section at the top of `README.md`

**Why it is needed:**  
The README is thorough but long. New users may not immediately know whether they should follow the Pi flow, the universal MCP flow, or the manual Python flow.

**Possible solution:**  
Add a short decision section near the top:

```md
## Which setup should I use?

- Using Pi? Use `/vision-inventory-setup` after `pi install ...`.
- Using Claude/Codex/OpenCode/Cursor? Use the universal installer.
- Using plain Python/manual MCP? Install `requirements.txt` and run `vision_inventory_mcp.py`.
```

This would reduce onboarding friction without removing detailed instructions later in the README.

---

### 4. Add a no-Cloudflare demo using sample raw JSON fixtures

**Why it is needed:**  
Currently, meaningful end-to-end testing requires Cloudflare credentials and real image processing. Users and contributors should be able to test CSV generation and datasheet-cache behavior without external API access.

**Possible solution:**  
Add a small fixture folder such as:

```text
examples/mock-output/raw/example_1.json
examples/mock-output/datasheet_cache.json
```

Then document a command such as:

```bash
python3 scripts/inventory_folder_to_csv.py ./examples/mock-photos ./examples/mock-output --skip-vision
```

Alternatively, add a dedicated script/test command that generates CSVs from fixture raw JSON directly.

---

### 5. Add a `--dry-run` or `--validate-setup` mode

**Why it is needed:**  
Users currently discover setup problems only when running the real workflow. A validation mode would help detect missing dependencies, missing credentials, unsupported image folders, and optional HEIC support before spending time on a batch run.

**Possible solution:**  
Add an option to `scripts/inventory_folder_to_csv.py`, for example:

```bash
python3 scripts/inventory_folder_to_csv.py ./photos ./output --validate-setup
```

It could check:

- Python imports
- Cloudflare credential presence
- image folder existence
- supported image count
- write access to output directory
- whether HEIC files are present without `pillow-heif`

---

### 6. Fail earlier when Cloudflare credentials are missing in batch workflow

**Why it is needed:**  
The batch script calls `process_image_impl()` for each image. If credentials are missing, each image can produce an error-shaped raw JSON result, and the workflow may continue into empty or misleading output files.

**Possible solution:**  
Before processing images, call the credential validation function once. If credentials are missing, exit immediately with a clear message:

```text
Missing Cloudflare credentials. Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_AUTH_TOKEN, or run /vision-inventory-setup.
```

This prevents users from interpreting empty CSVs as successful image analysis.

---

### 7. Improve messaging when no parts are extracted

**Why it is needed:**  
An empty `parts_to_lookup.json` can mean several different things: no supported images, unreadable markings, model/API failure, or no ICs detected. Users need help distinguishing these cases.

**Possible solution:**  
Add a summary at the end of the batch workflow:

```text
Processed images: 10
Images with errors: 0
IC markings extracted: 0
No parts were found. Check image focus/lighting or inspect output/raw/*.json.
```

Also include warnings in `parts_to_lookup.json` when no parts are extracted.

---

### 8. Align universal config examples with what `configure_mcp.py` actually writes, especially for OpenCode

**Why it is needed:**  
The static `.universal/configs/*.json.example` files currently look mostly identical, while `configure_mcp.py` writes a different OpenCode-specific format. Users may copy an example that does not match the installer-generated configuration.

**Possible solution:**  
Update `opencode.json.example` to match the OpenCode shape produced by `configure_mcp.py`, or update `configure_mcp.py` and the example files so they use the same documented format.

This reduces confusion and makes manual setup more reliable.

---

### 9. Use silent input for Cloudflare token in `quick-install.sh`

**Why it is needed:**  
The installer currently reads the Cloudflare token using normal shell input, which displays the token on screen. Tokens should not be visibly echoed during entry.

**Possible solution:**  
Use `read -rsp` for token input:

```bash
read -rsp "  Cloudflare API Token: " CF_TOKEN || true
echo
```

This provides a more secure and expected credential-entry experience.

---

### 10. Escape credentials properly in `quick-install.sh` instead of raw `sed` replacement

**Why it is needed:**  
The installer replaces placeholder values in `.env` using `sed`. If a token contains characters meaningful to `sed`, such as `/`, `&`, or backslashes, replacement can fail or corrupt the `.env` file.

**Possible solution:**  
Instead of using `sed`, write the `.env` file directly:

```bash
cat > "$ENV_FILE" <<EOF
CLOUDFLARE_ACCOUNT_ID=$CF_ID
CLOUDFLARE_AUTH_TOKEN=$CF_TOKEN
EOF
```

If preserving comments is important, use a small Python helper to safely update key-value pairs.

---

### 11. Warn users that some MCP configs may store credentials in plaintext

**Why it is needed:**  
Universal MCP configurations often place environment variables directly in JSON config files. This can store Cloudflare credentials in plaintext under directories like `~/.claude`, `~/.codex`, or `~/.cursor`.

**Possible solution:**  
Add a warning in the README and installer output:

```text
Warning: Some MCP clients store environment variables in plaintext config files. Prefer environment variables or secure secret storage if available.
```

Where possible, examples could show using shell environment variables instead of embedding secrets.

---

### 12. Warn users that web search/browser capability is needed, but do not attempt to check it automatically

**Why it is needed:**  
Datasheet enrichment requires a separate web-search or browser capability, but automatic detection is unreliable. Checking command/tool names for words like `search`, `browser`, or `web` can produce false positives and false negatives.

**Possible solution:**  
Remove or avoid automatic detection logic. Instead, always show a clear warning during setup and before `/vision-inventory-agent-bom`:

```text
Datasheet enrichment requires a separate web-search/browser tool. This package does not provide one. If your agent cannot search the web, stop after parts_to_lookup.json and fill datasheet_cache.json manually.
```

This communicates the requirement without blocking valid setups or misleading users.

---

### 13. Standardize terminology for “Cloudflare Auth Token”, “API Token”, and “Workers AI token”

**Why it is needed:**  
The docs and prompts use several names for the same credential. This may confuse users, especially those creating a token in the Cloudflare dashboard.

**Possible solution:**  
Pick one primary term, such as **Cloudflare Workers AI API token**, and use it consistently. When mentioning environment variables, clarify aliases:

```text
Set CLOUDFLARE_AUTH_TOKEN to your Cloudflare Workers AI API token.
CLOUDFLARE_API_TOKEN is also accepted as an alias.
```

---

### 14. Remove hardcoded `output/datasheet_cache.json` wording from generated `parts_to_lookup.json`

**Why it is needed:**  
`parts_to_lookup.json` currently includes an instruction like “Fill output/datasheet_cache.json”. However, users can choose any output directory. If the chosen output directory is not literally `output`, the instruction becomes inaccurate.

This matters because `parts_to_lookup.json` is intended to guide either a human or an agent. A hardcoded path can cause the user or agent to write `datasheet_cache.json` to the wrong location, especially in automated workflows.

**Possible solution:**  
Generate instructions using the actual selected output directory, or avoid naming a concrete directory in the JSON instruction.

Better generic wording:

```text
Fill datasheet_cache.json in the same output directory as this parts_to_lookup.json file, using datasheet_cache.template.json as the shape.
```

Even better, include explicit paths in the generated JSON:

```json
{
  "output_dir": "/absolute/path/to/user-output",
  "datasheet_cache_path": "/absolute/path/to/user-output/datasheet_cache.json",
  "datasheet_cache_template_path": "/absolute/path/to/user-output/datasheet_cache.template.json"
}
```

This would make the file safer for agent consumption and less dependent on assumptions.

---

### 15. Make the difference between `save_inventory()` CSV output and `inventory_folder_to_csv.py` output clearer

**Why it is needed:**  
The MCP tool `save_inventory()` can save an in-memory inventory result to CSV, but its CSV generation is intentionally simpler than the full batch workflow in `scripts/inventory_folder_to_csv.py`.

This creates a potential UX problem: users may assume that saving via `vision_inventory_save(..., format="csv")` produces the same enriched BOM as `/vision-inventory-bom` or `inventory_folder_to_csv.py`. It does not necessarily do so. The full batch workflow writes raw JSON files, builds `parts_to_lookup.json`, supports a datasheet cache workflow, creates `inventory_evidence.csv`, and performs more complete deduplication/evidence handling.

If this distinction is not explicit, users may use the save tool and wonder why they did not get the full enrichment workflow or evidence files.

**Possible solution:**  
Document the difference clearly in README and tool descriptions:

```text
vision_inventory_save(format="csv") is a quick export for already-returned tool results. For the full BOM workflow with raw evidence, parts_to_lookup.json, datasheet_cache.json, inventory.csv, and inventory_evidence.csv, use /vision-inventory-bom or scripts/inventory_folder_to_csv.py.
```

Possible implementation improvements:

- Rename the tool description to “quick CSV export”.
- Add a warning in the returned result when saving CSV:

```json
{
  "saved": true,
  "format": "csv",
  "note": "This is a quick export. Use inventory_folder_to_csv.py for the full BOM workflow."
}
```

- Consider adding a separate MCP tool for the full batch workflow if the intent is to expose full BOM generation through tools.

---

### 16. Remove unused `visible_ic_items()` from `vision_inventory_mcp.py`

**Why it is needed:**  
Unused functions add noise and make maintenance slightly harder. They can also mislead contributors into thinking the function participates in current behavior.

**Possible solution:**  
Remove `visible_ic_items()` unless it is planned for near-term use. If it is planned, add a comment explaining why it exists.

---

### 17. Add more structured diagnostics for invalid model JSON responses

**Why it is needed:**  
When the model returns invalid JSON, the server currently includes a warning and the raw response. This is useful, but a more structured diagnostic would help debugging and automated handling.

**Possible solution:**  
Return fields such as:

```json
{
  "parse_error": true,
  "parse_error_message": "Model returned invalid JSON.",
  "raw_response_preview": "...",
  "raw_response_length": 1234
}
```

This would let agents summarize failures more reliably without always inspecting the full raw response.

---

### 18. Add clearer error summaries when image processing returns API/credential errors

**Why it is needed:**  
Folder processing can produce per-image errors. In batch mode, repeated credential or API failures should be summarized clearly so users know the workflow failed for infrastructure reasons rather than because no components were found.

**Possible solution:**  
At the end of processing, count errors by type and print a summary:

```text
Processing completed with errors:
- Missing credentials: 12 images
- Cloudflare API errors: 0 images
- Image preprocessing errors: 1 image
```

For severe repeated errors, the script could exit non-zero.

---

### 19. Remove unused imports such as `Iterable` in `inventory_folder_to_csv.py`

**Why it is needed:**  
Unused imports are minor but easy cleanup. They reduce lint noise and keep the file tidy.

**Possible solution:**  
Remove `Iterable` from:

```python
from typing import Any, Dict, Iterable, List, Optional
```

leaving:

```python
from typing import Any, Dict, List, Optional
```

---

### 20. Improve amount/count estimation documentation or logic around `count_index`

**Why it is needed:**  
The workflow uses `count_index` to help estimate physical quantity. However, a model may use `count_index` as either an ordinal index or a grouped count. This can cause overcounting or undercounting.

**Possible solution:**  
Improve the prompt/schema to separate these concepts:

```json
{
  "count_index": 1,
  "visible_quantity": 1
}
```

Then update amount estimation to prefer `visible_quantity` when available. If keeping the current schema, document that quantity estimates are heuristic and should be reviewed.

---

### 21. Consider using a Python virtual environment for Pi dependency installation instead of global/user `pip`

**Why it is needed:**  
Installing dependencies with `python3 -m pip install -r requirements.txt` can affect the user’s global or user Python environment. This may cause dependency conflicts or require permissions depending on the system.

**Possible solution:**  
Have the Pi extension create and use a venv under something like:

```text
~/.pi/agent/vision-inventory/.venv
```

Then run the MCP server using that venv’s Python interpreter.

---

### 22. Clarify whether Pi credential/token prompts are masked

**Why it is needed:**  
Users entering API tokens need to know whether the token is hidden. If it is not hidden, they may accidentally expose credentials while screen sharing or recording.

**Possible solution:**  
If Pi supports secret/password inputs, use that for the Cloudflare token. If not, explicitly warn:

```text
Token input may be visible depending on your Pi UI. Avoid entering credentials while screen sharing.
```

---

### 23. Make `/vision-inventory-agent-bom` more structured/testable instead of relying mainly on a long generated prompt

**Why it is needed:**  
The command currently sends a long prompt asking the agent to run the workflow. This is flexible, but it is harder to test and can be less deterministic than a command that performs more steps directly.

**Possible solution:**  
Keep the agent prompt for datasheet search, but move deterministic parts into explicit command logic:

1. run the Python workflow,
2. verify `parts_to_lookup.json` exists,
3. ask the agent to enrich only the cache,
4. rerun with `--skip-vision`,
5. summarize outputs.

This would reduce the amount of behavior controlled only by prompt text.

---

### 24. Add sample expected output files to documentation

**Why it is needed:**  
Users benefit from seeing what successful output looks like before they run the tool. It helps them understand `inventory.csv`, `inventory_evidence.csv`, and `datasheet_cache.json`.

**Possible solution:**  
Add a small `examples/` section showing abbreviated examples of:

- `parts_to_lookup.json`
- `datasheet_cache.json`
- `inventory.csv`
- `inventory_evidence.csv`

Keep them short and clearly marked as examples.

---

## Deferred / do not implement for now

The following items were intentionally removed from the active implementation list. Leave them here for reference only unless priorities change.

### D1. Reduce duplicated workflow assets between `.pi/` and `.universal/`

Do not implement for now.

### D2. Add unit tests for parsing, normalization, part extraction, and CSV generation

Do not implement for now.

### D3. Add validation/test/lint scripts to `package.json`

Do not implement for now.

### D4. Add troubleshooting section for common failures: credentials, dependencies, no web search, no images, no readable markings

Do not implement for now.

### D5. Add CI to run Python compile/tests and possibly TypeScript checks

Do not implement for now.

### D6. Add a minimal changelog or release notes

Do not implement for now.
