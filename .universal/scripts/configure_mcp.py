#!/usr/bin/env python3
"""Configure MCP server entry in agent harness config file."""

import json
import sys

config_path = sys.argv[1]
harness = sys.argv[2]
server_python = sys.argv[3]
server_script = sys.argv[4]
cf_account = sys.argv[5]
cf_token = sys.argv[6]

mcp_entry = {
    "command": server_python,
    "args": [server_script],
    "env": {
        "CLOUDFLARE_ACCOUNT_ID": cf_account,
        "CLOUDFLARE_AUTH_TOKEN": cf_token,
    },
}

with open(config_path) as f:
    cfg = json.load(f)

if harness == "opencode":
    cfg.setdefault("mcp", {})["vision-inventory"] = {
        "type": "local",
        "command": [server_python, server_script],
        "enabled": True,
        "env": mcp_entry["env"],
    }
else:
    cfg.setdefault("mcpServers", {})["vision-inventory"] = mcp_entry

with open(config_path, "w") as f:
    json.dump(cfg, f, indent=2)

print(f"  MCP configured for {harness}: {config_path}")
