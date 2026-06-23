# Vision Inventory MCP Server Spec

## 1. Goal

Build a simple local MCP server that lets an AI agent process electronics/PCB images using Cloudflare Workers AI Vision and produce structured inventory data.

The app should be easy to deploy locally and preferably contained in a single Python script.

The MCP server must expose three tools:

1. `process_image`
2. `process_image_folder`
3. `save_inventory`

The vision model should only extract visible inventory information from images. Final part lookup, datasheet search, and web-based identification should be handled separately by the calling agent.

---

## 2. Main Use Case

An agent receives a folder of PCB/electronics images and uses this MCP server to:

1. Analyze each image.
2. Count visible components, especially ICs.
3. Transcribe package markings when visible.
4. Return structured JSON.
5. Save the combined inventory to JSON or CSV.

Example user instruction to an agent:

```text
Use the vision inventory MCP server to process all images in this folder:

C:\Users\Lucas\Desktop\pcb_photos

Create an inventory of all visible ICs and components. Do not look up the parts yet. Mark uncertain readings for review.
```

---

## 3. Design Constraints

The implementation should prioritize:

- Local deployment.
- Minimal setup.
- Single Python script if possible.
- No database.
- No frontend.
- No background worker.
- No unnecessary framework beyond MCP SDK, Pillow, requests, and optional HEIC support.
- Clear structured JSON output.
- Safe handling of hallucination-prone part numbers.

The first version should not perform web searches or datasheet lookups.

---

## 4. Recommended File Layout

Minimum version:

```text
vision_inventory_mcp.py
.env.example
README.md
```

Optional later structure:

```text
vision_inventory/
  vision_inventory_mcp.py
  outputs/
  test_images/
  README.md
```

---

## 5. Environment Variables

The script must read these environment variables:

```bash
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id
CLOUDFLARE_AUTH_TOKEN=your_cloudflare_workers_ai_api_token
```

Also support this fallback token name:

```bash
CLOUDFLARE_API_TOKEN=your_cloudflare_workers_ai_api_token
```

The code should check for missing environment variables and return a clear tool error.

---

## 6. Dependencies

Use Python 3.10+.

Required packages:

```bash
pip install mcp requests pillow python-dotenv
```

Optional package for iPhone HEIC/HEIF images:

```bash
pip install pillow-heif
```

The script should attempt to import `pillow_heif`, but continue working if it is not installed.

---

## 7. MCP Transport

Default to local `stdio` transport.

The script should end with:

```python
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

Do not start with HTTP deployment. Keep the first version local and simple.

---

## 8. Cloudflare Workers AI Model

Default model:

```text
@cf/meta/llama-4-scout-17b-16e-instruct
```

The model should be configurable through a constant:

```python
DEFAULT_MODEL = "@cf/meta/llama-4-scout-17b-16e-instruct"
```

Optional environment override:

```bash
WORKERS_AI_MODEL=@cf/meta/llama-4-scout-17b-16e-instruct
```

---

## 9. Cloudflare API Endpoint

Use the Workers AI REST endpoint:

```text
https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}
```

Authentication:

```http
Authorization: Bearer <CLOUDFLARE_AUTH_TOKEN>
Content-Type: application/json
```

---

## 10. Image Handling

The script must support:

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

Image preprocessing rules:

1. Open image with Pillow.
2. Apply EXIF orientation correction.
3. Resize while preserving aspect ratio.
4. Default `max_side` should be `2500`.
5. Default JPEG quality should be `94`.
6. Convert to RGB.
7. Convert transparent images to white background.
8. Encode as JPEG.
9. Base64 encode the JPEG bytes.
10. Send as a data URL.

Default image settings:

```python
DEFAULT_MAX_SIDE = 2500
DEFAULT_JPEG_QUALITY = 94
```

For very small IC markings, the agent may call the tool with:

```python
max_side=3000
jpeg_quality=95
```

---

## 11. Prompting Strategy

The model must be instructed to extract visible information only.

Important principles:

- Do not invent part numbers.
- Do not infer missing letters or numbers.
- Use `[?]` for unclear characters.
- Mark low-confidence readings for review.
- Do not perform external lookup.
- Do not claim exact identity unless the marking is clearly visible.
- Prefer uncertainty over guessing.

Use a system message like:

```text
You are a careful electronics image-analysis assistant.

Your job is to inspect electronics/PCB images and extract visible inventory information.

Do not perform web lookup.
Do not invent part numbers.
Do not infer missing letters or numbers.
For package markings, transcribe only what is visible.
Use [?] for unclear characters.
If text is blurry or partially hidden, set marking_confidence to "low" or "unreadable".
Prefer uncertainty over guessing.
Return only valid JSON.
```

Use a user prompt like:

```text
Analyze this electronics image and return an inventory of visible components.

Focus especially on IC packages and readable package markings.

Return only valid JSON using this schema:

{
  "image": "filename.jpg",
  "items": [
    {
      "item_type": "IC | connector | passive | module | switch | sensor | display | mechanical | unknown",
      "count_index": 1,
      "package_marking": "exact visible marking, unclear, unreadable, or [?]-marked partial text",
      "marking_confidence": "high | medium | low | unreadable",
      "likely_part": "visible part marking only, or unknown",
      "description": "short visual description, not web lookup",
      "position_hint": "top-left / center / near USB connector / etc.",
      "needs_review": true
    }
  ],
  "warnings": []
}

Rules:
- Return JSON only.
- Do not wrap the JSON in markdown.
- Do not identify parts from memory unless the marking is clearly visible.
- Do not use web lookup.
- If a marking is not readable, write "unreadable".
- If a component is visible but not identifiable, item_type should be "unknown".
- needs_review must be true when marking_confidence is "low" or "unreadable".
```

---

## 12. Required Output Schema

Each `process_image` call should return at minimum:

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
  ]
}
```

The full schema should be:

```json
{
  "image": "string",
  "items": [
    {
      "item_type": "IC | connector | passive | module | switch | sensor | display | mechanical | unknown",
      "count_index": 1,
      "package_marking": "string",
      "marking_confidence": "high | medium | low | unreadable",
      "likely_part": "string",
      "description": "string",
      "position_hint": "string",
      "needs_review": true
    }
  ],
  "warnings": ["string"]
}
```

The implementation should normalize missing fields when possible.

If JSON parsing fails, return:

```json
{
  "image": "board_01.jpg",
  "items": [],
  "warnings": ["Model returned invalid JSON."],
  "raw_response": "..."
}
```

---

## 13. Tool 1: process_image

### Name

```text
process_image
```

### Purpose

Analyze one image and return structured inventory data.

### Parameters

```python
image_path: str
max_side: int = 2500
jpeg_quality: int = 94
```

Optional:

```python
custom_prompt: str | None = None
```

### Behavior

1. Validate that the image exists.
2. Validate that it is a supported image extension.
3. Prepare image as base64 data URL.
4. Call Cloudflare Workers AI.
5. Parse model response as JSON.
6. Normalize output schema.
7. Return a Python dict.

### Return Example

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

---

## 14. Tool 2: process_image_folder

### Name

```text
process_image_folder
```

### Purpose

Process all supported images in a folder and return a combined inventory object.

### Parameters

```python
folder_path: str
recursive: bool = False
max_side: int = 2500
jpeg_quality: int = 94
```

Optional:

```python
limit: int | None = None
```

### Behavior

1. Validate that the folder exists.
2. Find supported image files.
3. Sort files alphabetically for deterministic behavior.
4. Process each image using `process_image`.
5. Continue processing even if one image fails.
6. Return all image results in a combined structure.

### Return Schema

```json
{
  "source_folder": "C:/Users/Lucas/Desktop/pcb_photos",
  "image_count": 3,
  "processed_count": 3,
  "failed_count": 0,
  "results": [
    {
      "image": "board_01.jpg",
      "items": [],
      "warnings": []
    }
  ],
  "errors": []
}
```

### Error Handling

If one image fails, do not fail the entire folder operation.

Instead include:

```json
{
  "image": "bad_image.jpg",
  "error": "Error message here"
}
```

inside `errors`.

---

## 15. Tool 3: save_inventory

### Name

```text
save_inventory
```

### Purpose

Save inventory results to disk as JSON or CSV.

### Parameters

```python
inventory: dict
output_path: str
format: str = "json"
```

Allowed formats:

```text
json
csv
```

### Behavior

For JSON:

1. Save full inventory object.
2. Pretty-print with indentation.
3. Use UTF-8 encoding.

For CSV:

Flatten all image results into rows.

CSV columns:

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

### Return Schema

```json
{
  "saved": true,
  "output_path": "inventory.json",
  "format": "json",
  "row_count": 12
}
```

---

## 16. Cloudflare Request Payload

Use a chat-style multimodal payload.

The image should be sent as a data URL.

Example:

```python
payload = {
    "messages": [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_prompt,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_data_url,
                    },
                },
            ],
        },
    ],
    "max_tokens": 1600,
    "temperature": 0.05,
    "top_p": 0.8,
}
```

Recommended defaults:

```python
max_tokens = 1600
temperature = 0.05
top_p = 0.8
```

---

## 17. JSON Parsing and Cleanup

The model may return JSON wrapped in markdown despite instructions.

Implement a helper:

```python
def extract_json_object(text: str) -> dict:
    ...
```

It should handle:

```text
{ ... }
```

and:

````text
```json
{ ... }
````

````

If parsing fails, return a structured error with `raw_response`.

---

## 18. Schema Normalization

Implement a helper:

```python
def normalize_inventory_result(result: dict, image_name: str) -> dict:
    ...
````

It should ensure:

- `image` exists.
- `items` is a list.
- `warnings` is a list.
- Each item has all required fields.
- `count_index` is an integer.
- `needs_review` is boolean.
- If `marking_confidence` is `low` or `unreadable`, set `needs_review = true`.

Default item values:

```python
{
    "item_type": "unknown",
    "count_index": 1,
    "package_marking": "unknown",
    "marking_confidence": "unreadable",
    "likely_part": "unknown",
    "description": "unknown",
    "position_hint": "unknown",
    "needs_review": True,
}
```

---

## 19. Error Handling Requirements

The server should return clean JSON-like errors instead of crashing.

Handle:

- Missing image file.
- Unsupported image extension.
- Missing Cloudflare credentials.
- Cloudflare API HTTP errors.
- Cloudflare success=false response.
- Invalid JSON from model.
- Folder does not exist.
- No images found in folder.
- CSV/JSON write errors.

Example error return:

```json
{
  "error": true,
  "message": "Missing CLOUDFLARE_ACCOUNT_ID environment variable."
}
```

---

## 20. Security and Safety

Since this is a local MCP server, avoid unnecessary filesystem access.

Rules:

- The server may read image files only from paths provided by the user/agent.
- The server may write inventory files only to paths provided through `save_inventory`.
- Do not delete files.
- Do not modify source images.
- Do not execute shell commands.
- Do not perform web requests except to Cloudflare Workers AI.
- Do not log API tokens.
- Do not include API tokens in tool responses.

---

## 21. Suggested Single-Script Structure

The script should be organized like this:

```python
"""
vision_inventory_mcp.py
Simple local MCP server for processing electronics images into inventory JSON.
"""

# imports

# optional HEIC support

# constants
DEFAULT_MODEL = "@cf/meta/llama-4-scout-17b-16e-instruct"
DEFAULT_MAX_SIDE = 2500
DEFAULT_JPEG_QUALITY = 94
SUPPORTED_EXTENSIONS = {...}

SYSTEM_PROMPT = "..."

# FastMCP init
mcp = FastMCP("Vision Inventory")

# utility functions
def get_cloudflare_credentials(): ...
def validate_image_path(image_path): ...
def guess_mime_type(path): ...
def prepare_image_data_url(path, max_side, jpeg_quality): ...
def call_workers_ai(image_data_url, image_name, prompt): ...
def extract_json_object(text): ...
def normalize_inventory_result(result, image_name): ...
def flatten_inventory_for_csv(inventory): ...

# MCP tools
@mcp.tool()
def process_image(...): ...

@mcp.tool()
def process_image_folder(...): ...

@mcp.tool()
def save_inventory(...): ...

# main
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

---

## 22. Example MCP Client Configuration

For an MCP-compatible local client, use a config similar to:

```json
{
  "mcpServers": {
    "vision-inventory": {
      "command": "python",
      "args": ["C:/path/to/vision_inventory_mcp.py"],
      "env": {
        "CLOUDFLARE_ACCOUNT_ID": "your-account-id",
        "CLOUDFLARE_AUTH_TOKEN": "your-token"
      }
    }
  }
}
```

The exact config file location depends on the MCP client.

---

## 23. Example Agent Workflow

The agent should use the tools like this:

1. Call `process_image_folder` with the folder path.
2. Review returned items.
3. Use its own web search capabilities to look up readable `package_marking` values.
4. Add confirmed part details outside this MCP tool.
5. Call `save_inventory` to save the raw extracted inventory.
6. Optionally create a second enriched inventory after web lookup.

Important: the MCP server should produce a raw visual inventory, not a final validated BOM.

---

## 24. Example Tool Call Results

### process_image

Input:

```json
{
  "image_path": "C:/Users/Lucas/Desktop/pcb_photos/board_01.jpg"
}
```

Output:

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
    },
    {
      "item_type": "IC",
      "count_index": 2,
      "package_marking": "unreadable",
      "marking_confidence": "unreadable",
      "likely_part": "unknown",
      "description": "Small black IC package",
      "position_hint": "center-right area of board",
      "needs_review": true
    }
  ],
  "warnings": [
    "Some markings are blurry; cropped close-up images may improve results."
  ]
}
```

### process_image_folder

Input:

```json
{
  "folder_path": "C:/Users/Lucas/Desktop/pcb_photos",
  "recursive": false
}
```

Output:

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

### save_inventory

Input:

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

Output:

```json
{
  "saved": true,
  "output_path": "C:/Users/Lucas/Desktop/inventory.json",
  "format": "json",
  "row_count": 0
}
```

---

## 25. Acceptance Criteria

The project is complete when:

1. The MCP server starts locally with `python vision_inventory_mcp.py`.
2. An MCP-compatible agent can discover three tools:
   - `process_image`
   - `process_image_folder`
   - `save_inventory`

3. `process_image` accepts a local image path and returns structured JSON.
4. `process_image_folder` processes multiple images and continues after individual failures.
5. `save_inventory` writes JSON and CSV.
6. Missing credentials produce a clear error.
7. Invalid image paths produce a clear error.
8. The server does not perform part lookup or web search.
9. The server does not hallucinate certainty; uncertain markings are marked with `needs_review: true`.
10. The implementation is contained in one simple Python script.

---

## 26. Future Improvements

Do not implement these in version 1, but keep the design open for them:

- Add OCR-specific preprocessing.
- Add automatic image cropping around ICs.
- Add duplicate component merging.
- Add part-number lookup tool.
- Add confidence scoring from multiple model passes.
- Add output to Excel.
- Add local cache by image hash.
- Add HTTP transport.
- Add a small GUI wrapper.
- Add support for enriched BOM generation after web lookup.
