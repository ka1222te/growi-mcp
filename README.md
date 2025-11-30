# Growi MCP

Growi MCP is an MCP server designed for Growi, an open-source wiki tool that streamlines information sharing and knowledge management.

## Overview

This project provides an unofficial MCP server that acts as a proxy to perform various operations such as retrieving page lists, reading and writing pages, creating and updating pages, etc. Internally, it uses the Growi REST API.

## Features

- Tool List
  - get_page_list(path_or_id*, limit, offset)
    - Retrieve the list of pages under the specified page (or page ID)
  - read_page(path_or_id*)
    - Read the content of the specified page (or page ID)
  - create_page(path*, body)
    - Create a page at the specified path
  - update_page(path_or_id*, body*)
    - Update the content of the specified page (or page ID)
  - rename_page(path_or_id*, new_path*)
    - Rename or move a page (by path or page ID)
  - remove_page(path_or_id*, recursively)
    - Delete a page (by path or page ID)
  - search_pages(query*, path, limit, offset)
    - Search for pages that match the query
  - get_user_names(query*, limit, offset)
    - Retrieve user names that match the query
  - upload_attachment(page_id_or_path*, file_path*)
    - Upload and attach a file to a page (by page ID or path)
  - get_attachment_list(path_or_id*, limit, offset)
    - Retrieve the list of attachments on a page (by path or page ID)
  - get_attachment_info(attachment_id*)
    - Retrieve detailed information for a page attachment (by attachment ID)
  - download_attachment(attachment_id*, save_dir)
    - Download an attachment (by attachment ID) to a local directory
  - remove_attachment(attachment_id*)
    - Delete an attachment (by attachment ID)

- MCP Server Compliance
  - Conforms to the Model Context Protocol (MCP)
  - Exposes endpoints callable from AI tools like Cursor and Cline
  - Operates via JSON-RPC over stdio

## Installation

This section explains how to install uv.

### Install uv

```bash
# If uv is not installed, install it first
# On Windows (PowerShell)
Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing | Invoke-Expression

# On Linux/macOS (shell)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Usage

### Start the MCP server

Two ways to start the MCP server for use with Cline/Cursor are shown below.

#### Clone the GitHub repository and start the MCP server

If you want to clone from GitHub and run locally, clone the Growi MCP repository with the following commands:

```bash
# HTTPS
git clone https://github.com/ka1222te/growi-mcp.git
# SSH
git clone ssh://git@github.com/ka1222te/growi-mcp.git
```

After cloning, run `cd growi-mcp` to move into the repository directory, then resolve dependencies with:

```bash
uv sync
```

Next, copy `.env.sample` to `.env` and configure environment variables. Example:

```bash
GROWI_DOMAIN="http://growi.example.com"
GROWI_API_TOKEN="your_access_token_here"
# API version: "1" or "3"
GROWI_API_VERSION="3"

# Optional
# If your Growi server requires a session id, set connect.sid cookie value here
#GROWI_CONNECT_SID="your_connect_sid_here"
```

- GROWI_DOMAIN
  - The domain where your Growi server is hosted
- GROWI_API_TOKEN
  - API token; you can issue a token from “User Settings → API Settings”
- GROWI_API_VERSION
  - Version of the Growi REST API to use. Currently supported: "1" and "3"
- GROWI_CONNECT_SID
  - Session ID required for some features (e.g., download_attachment). Access Growi via a browser and set the value of `connect.sid` found in the REST API request headers.

Then, add the following configuration to the settings file (JSON) of your AI coding tool (Cline/Cursor/Claude Code, etc.):

```json
{
  "mcpServers": {
    "growi-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/growi-mcp",
        "run",
        "growi-mcp"
      ]
    }
  }
}
```

Replace `/path/to/growi-mcp` with the installation directory of Growi MCP.

#### Start the MCP server directly from the GitHub repository (HTTPS)

To run directly from the GitHub repository, add the following to the settings file (JSON) of your AI coding tool:

```json
{
  "mcpServers": {
    "growi-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/ka1222te/growi-mcp",
        "growi-mcp"
      ],
      "env": {
        "GROWI_DOMAIN": "http://growi.example.com",
        "GROWI_API_TOKEN": "your_access_token_here",
        "GROWI_API_VERSION": "3",
        "GROWI_CONNECT_SID": "your_connect_sid_here(Optional)" 
      }
    }
  }
}
```

Note that you must set each corresponding environment variable in the "env" section.

#### Start the MCP server directly from the GitHub repository (SSH)

If you access the GitHub repository via SSH, use `uvx --from git+ssh://github.com/ka1222te/growi-mcp growi-mcp` instead. 

```json
{
  "mcpServers": {
    "growi-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+ssh://github.com/ka1222te/growi-mcp",
        "growi-mcp"
      ],
      "env": {
        "GROWI_DOMAIN": "http://growi.example.com",
        "GROWI_API_TOKEN": "your_access_token_here",
        "GROWI_API_VERSION": "3",
        "GROWI_CONNECT_SID": "your_connect_sid_here(Optional)" 
      }
    }
  }
}
```

Note that you must set each corresponding environment variable in the "env" section.

#### Start the MCP server directly from the PyPI project

Use the `uvx` command to start the MCP server directly from the PyPI project.

```json
{
  "mcpServers": {
    "growi-mcp": {
      "command": "uvx",
      "args": [
        "growi-mcp"
      ],
      "env": {
        "GROWI_DOMAIN": "http://growi.example.com",
        "GROWI_API_TOKEN": "your_access_token_here",
        "GROWI_API_VERSION": "3",
        "GROWI_CONNECT_SID": "your_connect_sid_here(Optional)" 
      }
    }
  }
}
```

Note that you must set each corresponding environment variable in the "env" section.

### Examples: Using MCP Tools

Below are examples of using Growi MCP tools.

#### Retrieve user information

If you prompt your AI agent with the following, it can retrieve the list of users created in Growi:

```
List all users that exist in the wiki.
```

This will execute `get_user_names` and present the user list in alphabetical order or another structured format.

#### Summarize a user’s contributions

Pick one of the users obtained above and summarize their postings with a prompt like:

```
Summarize what the user: <username> has been writing.
```

This will execute tools like `search_pages` and `read_page`, collect relevant content written by the user, and then provide an LLM-generated summary.

## Disclaimer

The author assumes no responsibility for any damages arising from the use of this program.

### Handling of Private Information

Growi MCP executes tool/call (Function Call) requests generated by LLMs and returns responses. If your wiki is hosted in a private environment, internal information may be revealed to the LLM. Therefore, use caution when selecting which LLM to integrate. When handling confidential information, we recommend disabling the tool’s “Auto-approve” feature so that operations require explicit user approval. This helps prevent information leakage by allowing you to reject execution when accessing private pages.

### About Page Updates

If you enable “Auto-approve” for update operations, there is a risk of unintentionally modifying pages written by others. Suggested mitigations:

- Restrict the scope of editable pages
  - In your prompts or a configuration file like `rules.md`, describe rules such as “Do not edit pages outside your own user directory.” This guides the LLM to check page ownership and helps prevent overwriting someone else’s pages.
- Disable “Auto-approve”
  - By requiring explicit user approval for each operation, you can avoid pages becoming disorganized. Toggle this setting based on your use case.

## License

This project is released under the MIT License. For details, refer to the [LICENSE](LICENSE) file.
