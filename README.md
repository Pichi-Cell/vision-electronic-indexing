# Vision Inventory MCP Server

A simple local MCP server for turning electronics / PCB images into structured visual inventory JSON using Cloudflare Workers AI.

This is version 1 of the project. It is intentionally small: one Python file, local `stdio` MCP transport, no database, no GUI, and no part-number web lookup.

## What it does

The server exposes three MCP tools:

| Tool | Purpose |
|---|---|
| `process_image` | Analyze one image and return visible inventory data. |
| `process_image_folder` | Analyze all supported images in a folder. |
| `save_inventory` | Save inventory output to JSON or CSV. |

The vision model extracts visible component information such as IC markings, confidence, approximate position, and whether human review is needed.

It does **not** perform datasheet lookup, web search, part validation, or BOM enrichment. Those steps should be handled by the calling agent after this tool returns raw visual inventory data.

## Model

Default Cloudflare Workers AI model:

```text
@cf/meta/llama-4-scout-17b-16e-instruct
```

You can override it with:

```bash
WORKERS_AI_MODEL=@cf/meta/llama-4-scout-17b-16e-instruct
```

## Requirements

Python 3.10 or newer is recommended.

Install required dependencies:

```bash
pip install mcp requests pillow python-dotenv
```

Optional, but recommended for iPhone `.heic` / `.heif` photos:

```bash
pip install pillow-heif
```

## Setup

Download or copy the server file:

```text
vision_inventory_mcp.py
```

Create a `.env` file in the same folder:

```env
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id
CLOUDFLARE_AUTH_TOKEN=your_cloudflare_workers_ai_token
```

The script also accepts this token variable name:

```env
CLOUDFLARE_API_TOKEN=your_cloudflare_workers_ai_token
```

## Running locally

Run the MCP server with:

```bash
python vision_inventory_mcp.py
```

The server uses MCP `stdio` transport, so it is meant to be launched by an MCP-compatible client or agent.

## MCP client configuration

Example configuration shape:

```json
{
  "mcpServers": {
    "vision-inventory": {
      "command": "python",
      "args": [
        "C:/path/to/vision_inventory_mcp.py"
      ],
      "env": {
        "CLOUDFLARE_ACCOUNT_ID": "your_cloudflare_account_id",
        "CLOUDFLARE_AUTH_TOKEN": "your_cloudflare_workers_ai_token"
      }
    }
  }
}
```

Use the exact config location and format required by your MCP client.

## Supported image formats

The server supports:

```text
.jpg
.jpeg
.png
.webp
.bmp
.gif
.heic
.heif
```

HEIC/HEIF support requires `pillow-heif`.

## Image preprocessing

Before sending an image to Cloudflare Workers AI, the server:

1. Opens the image with Pillow.
2. Applies EXIF orientation correction.
3. Resizes while preserving aspect ratio.
4. Converts transparency to a white background.
5. Converts the image to RGB.
6. Encodes it as JPEG.
7. Sends it as a base64 image data URL.

Default image settings:

```text
max_side: 2500
jpeg_quality: 94
```

For cropped close-ups of small IC markings, try:

```text
max_side: 3000
jpeg_quality: 95
```

## Tool: process_image

Analyze one electronics / PCB image and return structured visual inventory data.

### Parameters

```json
{
  "image_path": "C:/Users/Lucas/Desktop/pcb_photos/board_01.jpg",
  "max_side": 2500,
  "jpeg_quality": 94,
  "custom_prompt": null
}
```

### Output example

```json
{
  "image": "board_01.jpg",
  "items": [
    {
      "item_type": "IC",
      "count_index": 1,
      "package_marking": "AMS1117-3.3",
      "marking_confidence": "high",
      "likely_part": "AMS1117-3.3",
      "description": "Visible IC package with readable marking",
      "position_hint": "top-left area of board",
      "needs_review": false
    }
  ],
  "warnings": []
}
```

### Notes

`likely_part` should only contain the visible part marking or `unknown`. The server is intentionally not responsible for validating the part number online.

`needs_review` is automatically forced to `true` when `marking_confidence` is `low` or `unreadable`.

## Tool: process_image_folder

Analyze every supported image in a folder.

### Parameters

```json
{
  "folder_path": "C:/Users/Lucas/Desktop/pcb_photos",
  "recursive": false,
  "max_side": 2500,
  "jpeg_quality": 94,
  "limit": null
}
```

### Output example

```json
{
  "source_folder": "C:/Users/Lucas/Desktop/pcb_photos",
  "image_count": 2,
  "processed_count": 2,
  "failed_count": 0,
  "results": [
    {
      "image": "board_01.jpg",
      "items": [],
      "warnings": []
    },
    {
      "image": "board_02.jpg",
      "items": [],
      "warnings": []
    }
  ],
  "errors": []
}
```

If one image fails, the folder process continues and adds the failure to `errors`.

## Tool: save_inventory

Save a `process_image` or `process_image_folder` result to disk.

### Save as JSON

```json
{
  "inventory": {
    "source_folder": "C:/Users/Lucas/Desktop/pcb_photos",
    "results": []
  },
  "output_path": "C:/Users/Lucas/Desktop/inventory.json",
  "format": "json"
}
```

### Save as CSV

```json
{
  "inventory": {
    "source_folder": "C:/Users/Lucas/Desktop/pcb_photos",
    "results": []
  },
  "output_path": "C:/Users/Lucas/Desktop/inventory.csv",
  "format": "csv"
}
```

### CSV columns

```text
image
item_type
count_index
package_marking
marking_confidence
likely_part
description
position_hint
needs_review
warnings
```

### Output example

```json
{
  "saved": true,
  "output_path": "C:/Users/Lucas/Desktop/inventory.json",
  "format": "json",
  "row_count": 12
}
```

## Suggested agent workflow

1. Call `process_image_folder` on a folder of board photos.
2. Inspect `items` and `warnings`.
3. Ask for better close-up images where `needs_review` is `true`.
4. Use separate web search / datasheet lookup tools to validate readable markings.
5. Call `save_inventory` to save the raw extracted inventory.
6. Optionally save a second enriched inventory after lookup.

Example instruction to an agent:

```text
Use the vision-inventory MCP server to process all images in:
C:\Users\Lucas\Desktop\pcb_photos

Create a raw visual inventory. Do not look up part numbers yet. Mark uncertain readings for review, then save the result as JSON and CSV.
```

## Error handling

The server returns structured errors instead of crashing when possible.

Example:

```json
{
  "error": true,
  "message": "Missing CLOUDFLARE_ACCOUNT_ID environment variable."
}
```

Handled cases include:

- Missing Cloudflare credentials.
- Invalid image path.
- Unsupported image extension.
- Failed image preprocessing.
- Cloudflare API errors.
- Invalid JSON from the model.
- Missing or invalid folder path.
- Save/write failures.

## Important limitations

- Vision models can misread small or blurry IC markings.
- Full-board photos are useful for counting and locating parts, but cropped close-ups are better for reading markings.
- The server does not verify part numbers.
- The server does not deduplicate components across multiple photos.
- The server does not create a final validated BOM by itself.

For best results, use this two-step image workflow:

```text
1. Full board photo -> count and locate components.
2. Cropped IC photos -> transcribe package markings.
```

Then let the agent perform web lookup separately.

## Version 1 scope

Included:

- Single-file Python MCP server.
- Local `stdio` transport.
- Cloudflare Workers AI vision call.
- Single image processing.
- Folder processing.
- JSON and CSV saving.
- Basic schema normalization.
- Optional `.env` loading.
- Optional HEIC/HEIF support.

Not included:

- Web lookup.
- Datasheet lookup.
- Part validation.
- GUI.
- Database.
- HTTP server.
- Automatic component cropping.
- Duplicate merging.
- Excel export.
