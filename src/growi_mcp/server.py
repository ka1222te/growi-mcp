#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Growi MCP Server (growi_mcp.server: FastMCP)

Tools:
  - get_page_list(path_or_id*, limit, offset)
  - read_page(path_or_id*)
  - create_page(path*, body)
  - update_page(path_or_id*, body*)
  - rename_page(path*, new_path*)
  - remove_page(path_or_id*, recursively)
  - search_pages(query*, path, limit, offset)
  - get_user_names(query*, limit, offset)
  - register_user(name*, username*, email*, password*)
  - upload_attachment(path_or_page_id*, file_path*)
  - get_attachment_list(path_or_id*, limit, offset)
  - get_attachment_info(attachment_id*)
  - download_attachment(attachment_id*, save_dir)
  - remove_attachment(attachment_id*)

Environment variables (.env supported via dotenv):
- GROWI_DOMAIN* (e.g. http://growi.example.com)
- GROWI_API_TOKEN*
- GROWI_API_VERSION* (e.g. "3")
- GROWI_CONNECT_SID (session id for connection)
"""

import asyncio
import json
import os,sys
from typing import Any,Dict,List,Optional,Tuple

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP,Context
from pathlib import Path
import base64
import mimetypes

"MIME types"
mimetypes.add_type("text/markdown",".md") # markdown
mimetypes.add_type("application/json",".json") # json
mimetypes.add_type("application/x-yaml",".yml") # yml
mimetypes.add_type("application/toml",".toml") # toml
mimetypes.add_type("text/csv",".csv") # csv
mimetypes.add_type("text/x-python",".py") # python
mimetypes.add_type("application/javascript",".js") # js
mimetypes.add_type("application/typescript",".ts") # ts
mimetypes.add_type("text/jsx",".jsx") # jsx
mimetypes.add_type("text/tsx",".tsx") # tsx
mimetypes.add_type("application/x-sh",".sh") # sh
mimetypes.add_type("image/webp",".webp") # webp
mimetypes.add_type("image/avif",".avif") # avif
mimetypes.add_type("audio/flac",".flac") # flac
mimetypes.add_type("audio/opus",".opus") # opus
mimetypes.add_type("video/webm",".webm") # webm
mimetypes.add_type("application/wasm",".wasm") # wasm
mimetypes.add_type("application/x-sqlite3",".sqlite3") # sqlite3

"env settings"
def _require_env(name: str) -> str:
    """Get required environment variable or raise."""
    val = os.getenv(name,"").strip()
    if not val: raise ValueError(f"Environment variable '{name}' is required")
    return val

def _optional_env(name: str) -> Optional[str]:
    """Get optional environment variable or raise."""
    val = os.getenv(name)
    if val is None: return None
    val = val.strip()
    return val if val else None

def _normalize_domain(domain: str) -> str:
    """Convert the domain to a format usable by GrowiMCP"""
    return domain[:-1] if domain.endswith("/") else domain

"growi client"
class GrowiClient:
    """Growi REST API client with API key (v1/v3 compatible)."""

    def __init__(
        self,
        domain: str,
        access_token: str,
        version: str = "3",
        connect_sid: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.domain = _normalize_domain(domain)
        self.token = access_token
        self.version = str(version).strip()
        if self.version not in {"1","3"}: raise RuntimeError("Failed to resolve version for Growi REST API")
        cookies = {}
        if connect_sid:
            cookies["connect.sid"] = connect_sid
        self._client = httpx.AsyncClient(
            base_url=self.domain,
            timeout=timeout,
            headers={"Accept": "application/json"},
            cookies=cookies,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    def _with_token(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        merged = dict(params or {})
        merged["access_token"] = self.token
        return merged

    @staticmethod
    def _extract_page_id(page_json: Dict[str, Any]) -> Optional[str]:
        try:
            if "_id" in page_json:
                return str(page_json["_id"])
            if "page" in page_json and "_id" in page_json["page"]:
                return str(page_json["page"]["_id"])
            if "data" in page_json and "page" in page_json["data"]:
                pj = page_json["data"]["page"]
                if "_id" in pj:
                    return str(pj["_id"])
        except Exception:
            pass
        return None

    @staticmethod
    def _extract_revision_id(page_json: Dict[str, Any]) -> Optional[str]:
        candidates: List[Optional[str]] = []
        try:
            p = page_json.get("page") or page_json
            if isinstance(p, dict):
                rev = p.get("revision")
                if isinstance(rev, str):
                    candidates.append(rev)
                elif isinstance(rev, dict) and "_id" in rev:
                    candidates.append(str(rev["_id"]))
                if "revisionId" in p:
                    candidates.append(str(p["revisionId"]))
        except Exception:
            pass
        for c in candidates:
            if c:
                return c
        return None

    async def _resolve_page_id(self, path_or_page_id: str) -> str:
        """Resolve page id from path or return given id."""
        if path_or_page_id.startswith("/"):
            pj = await self.get_page(path_or_page_id)
            pid = self._extract_page_id(pj)
            if not pid:
                raise RuntimeError("Failed to resolve pageId")
            return pid
        return path_or_page_id

    async def get_page_list(self, path_or_page_id: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """List multiple pages under a path or around a page id."""
        if self.version == "1":
            url = "/_api/pages.list"
            if path_or_page_id.startswith("/"):
                params = {"path": path_or_page_id, "limit": limit, "offset": offset, "page": offset//limit+1}
            else:
                params = {"page_id": path_or_page_id, "limit": limit, "offset": offset, "page": offset//limit+1}
        elif self.version == "3":
            url = "/_api/v3/pages/list"
            if path_or_page_id.startswith("/"):
                params = {"path": path_or_page_id, "limit": limit, "page": offset//limit+1}
            else:
                # Some servers accept "pageId" for v3 list fallback
                params = {"pageId": path_or_page_id, "limit": limit, "page": offset//limit+1}
        else:
            raise RuntimeError(f"Your Growi REST API version '{self.version}' is not available for get_page_list")
        res = await self._client.get(url, params=self._with_token(params))
        if res.status_code in {400, 401, 403, 404, 409, 422}: raise RuntimeError(f"Growi API error ({res.status_code}): {res.text}")
        return res.json()

    async def get_page(self, path_or_id: str) -> Dict[str, Any]:
        """Get Growi page"""
        if self.version == "1":
            url = "/_api/pages.get"
            if path_or_id.startswith("/"):
                params = {"path": path_or_id}
            else:
                params = {"page_id": path_or_id}
        elif self.version == "3":
            url = "/_api/v3/page"
            if path_or_id.startswith("/"):
                params = {"path": path_or_id}
            else:
                params = {"pageId": path_or_id}
        else:
            raise RuntimeError(f"Your Growi REST API version '{self.version}' is not available for get_page")
        res = await self._client.get(url, params=self._with_token(params))
        res.raise_for_status()
        data = res.json()
        return data

    async def create_page(self, path: str, body: str) -> Dict[str, Any]:
        if self.version == "1":
            url = "/_api/pages.create"
            data = {"path": path, "body": body}
            res = await self._client.post(url, params=self._with_token(), data=data)
        elif self.version == "3":
            url = "/_api/v3/page"
            data = {"path": path, "body": body}
            res = await self._client.post(url, params=self._with_token(), data=data)
        else:
            raise RuntimeError(f"Your Growi REST API version '{self.version}' is not available for create_page")
        res.raise_for_status()
        return res.json()

    async def update_page_by_id(self, page_id: str, body: str) -> Dict[str, Any]:
        page_json = await self.get_page(page_id)
        rev_id = self._extract_revision_id(page_json)
        if not rev_id:
            pj = (
                page_json.get("page")
                or page_json.get("data", {}).get("page")
                or page_json
            )
            rev_id = self._extract_revision_id({"page": pj})
        if not rev_id:
            raise RuntimeError("Failed to resolve revisionId for the target page")

        if self.version == "1":
            url = "/_api/pages.update"
            data = {"page_id": page_id, "revision_id": rev_id, "body": body}
            res = await self._client.post(url, params=self._with_token(), data=data)
        elif self.version == "3":
            url = "/_api/v3/page"
            data = {"pageId": page_id, "revisionId": rev_id, "body": body}
            res = await self._client.put(url, params=self._with_token(), data=data)
        else:
            raise RuntimeError(f"Your Growi REST API version '{self.version}' is not available for update_page_by_id")
        res.raise_for_status()
        return res.json()

    async def update_page_by_path(self, path: str, body: str) -> Dict[str, Any]:
        page_json = await self.get_page(path)
        pid = self._extract_page_id(page_json)
        if not pid:
            raise RuntimeError("Failed to resolve pageId by path")
        return await self.update_page_by_id(pid, body)

    async def rename_page(self, path: str, new_path: str) -> Dict[str, Any]:
        """Move (rename) a page to a new path."""
        pid = await self._resolve_page_id(path)
        page_json = await self.get_page(path)
        revisionid = self._extract_revision_id(page_json)
        if self.version == "3":
            url = "/_api/v3/pages/rename"
            data = {"pageId": pid, "revisionId": revisionid, "newPagePath": new_path, "isRenameRedirect": False, "updateMetadata": True, "isRecursively": True}
        else:
            raise RuntimeError(f"Your Growi REST API version '{self.version}' is not available for rename_page")
        res = await self._client.put(url, params=self._with_token(), json=data)
        if res.status_code in {400, 401, 403, 404, 409, 422}: raise RuntimeError(f"Growi API error ({res.status_code}): {res.text}")
        return res.json()

    async def remove_page(self, path_or_page_id: str, recursively: bool = True) -> Dict[str, Any]:
        """Remove (delete) a page."""
        pid = await self._resolve_page_id(path_or_page_id)
        if self.version in {"1", "3"}:
            url = "/_api/pages.remove"
            data = {"page_id": pid, "recursively": recursively}
        else:
            raise RuntimeError(f"Your Growi REST API version '{self.version}' is not available for remove_page")
        res = await self._client.post(url, params=self._with_token(), data=data)
        if res.status_code in {400, 401, 403, 404, 409, 422}: raise RuntimeError(f"Growi API error ({res.status_code}): {res.text}")
        return res.json()

    async def search_pages(self, query: str, path: str = "/", limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        attempts: List[Tuple[str, Dict[str, Any]]] = []
        if self.version in {"1","3"}:
            url = "/_api/search"
            params = {"q": query, "path": path, "limit": limit, "offset": offset}
        else:
            raise RuntimeError(f"Your Growi REST API version '{self.version}' is not available for search_pages")
        res = await self._client.get(url, params=self._with_token(params))
        if res.status_code in {400, 401, 403, 404, 409, 422}: raise RuntimeError(f"Growi API error ({res.status_code}): {res.text}")
        return res.json()

    async def get_user_names(self, query: str, limit: Optional[int] = 10, offset: Optional[int] = 0) -> Dict[str, Any]:
        if self.version == "3":
            url = "/_api/v3/users/usernames"
            params = {"q": query, "limit": limit, "offset": offset}
        else:
            raise RuntimeError(f"Your Growi REST API version '{self.version}' is not available for get_user_info")
        res = await self._client.get(url, params=self._with_token(params))
        if res.status_code in {400, 401, 403, 404, 409, 422}: raise RuntimeError(f"Growi API error ({res.status_code}): {res.text}")
        return res.json()

    async def register_user(self, name: str, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register a user to wiki."""
        if self.version == "1":
            url = "/_api/register"
            data = {
                "registerForm[name]": name,
                "registerForm[username]": username,
                "registerForm[email]": email,
                "registerForm[password]": password,
            }
        elif self.version == "3":
            url = "/_api/v3/register"
            data = {
                "registerForm[name]": name,
                "registerForm[username]": username,
                "registerForm[email]": email,
                "registerForm[password]": password,
            }
        else:
            raise RuntimeError(f"Your Growi REST API version '{self.version}' is not available for register_user")
        res = await self._client.post(url, params=self._with_token(), data=data)
        if res.status_code in {400, 401, 403, 404, 409, 422}: raise RuntimeError(f"Growi API error ({res.status_code}): {res.text}")
        return res.json()

    async def upload_attachment(
        self,
        path_or_page_id: str,
        file_path: Optional[str],
    ) -> Dict[str, Any]:
        """Upload an attachment to a page via file path."""
        pid = await self._resolve_page_id(path_or_page_id)

        with open(file_path, "rb") as f:
            content = f.read()
        mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        fname = os.path.basename(file_path)

        files = {"file": (fname, content, mime)}
        data = {"page_id": pid}

        if self.version == "1":
            url = "/_api/attachments.add"
        elif self.version == "3":
            url = "/_api/v3/attachment"
        else:
            raise RuntimeError(f"Your Growi REST API version '{self.version}' is not available for upload_attachment")
        res = await self._client.post(url, params=self._with_token(), data=data, files=files)
        if res.status_code in {400, 401, 403, 404, 409, 422}: raise RuntimeError(f"Growi API error ({res.status_code}): {res.text}")
        return res.json()

    async def get_attachment_list(self, path_or_page_id: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """List uploaded attachments for a page."""
        pid = await self._resolve_page_id(path_or_page_id)
        if self.version == "1":
            url = "/_api/attachments.list"
            params = {"page_id": pid, "limit": limit, "offset": offset}
        elif self.version == "3":
            url = "/_api/v3/attachment/list"
            params = {"pageId": pid, "limit": limit, "pageNumber": offset//limit+1}
        else:
            raise RuntimeError(f"Your Growi REST API version '{self.version}' is not available for get_attachment_list")
        res = await self._client.get(url, params=self._with_token(params))
        if res.status_code in {400, 401, 403, 404, 409, 422}: raise RuntimeError(f"Growi API error ({res.status_code}): {res.text}")
        return res.json()
    
    async def get_attachment_info(self, attachment_id: str) -> Dict[str, Any]:
        """Get information of attachment file by its id."""
        if self.version == "3":
            url = f"/_api/v3/attachment/{attachment_id}"
        else:
            raise RuntimeError(f"Your Growi REST API version '{self.version}' is not available for get_attachment")
        res = await self._client.get(url, params=self._with_token())
        if res.status_code in {400, 401, 403, 404, 409, 422}: raise RuntimeError(f"Growi API error ({res.status_code}): {res.text}")
        return res.json()

    async def download_attachment(self, attachment_id: str, save_dir: str = "./attachment") -> Dict[str, Any]:
        """Download an attachment by its download path (e.g., '/attachment/...')."""
        res = await self.get_attachment_info(attachment_id)
        original_name = res["attachment"]["originalName"]
        file_name = res["attachment"]["fileName"]
        file_format = res["attachment"]["fileFormat"]
        file_path_proxied = res["attachment"]["filePathProxied"]

        url = f"{self.domain}{file_path_proxied}"
        res = await self._client.get(url)
        session_error_msg = (f"This endpoint requires a valid session cookie (connect.sid). Set GROWI_CONNECT_SID if your Growi server enforces session for {file_path_proxied}.")
        if res.status_code != 200: raise RuntimeError(f"Growi API error ({res.status_code}): {session_error_msg}")
        content = res.content
        if len(content) == 0: raise RuntimeError(f"Growi API error ({res.status_code}): {session_error_msg}")
        if isinstance(save_dir, str): save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        with open(save_dir/original_name, "wb") as f:
            f.write(content)
        return {
            "ok": True,
            "originalName": original_name,
            "fileName": file_name,
            "fileFormat": file_format,
            "filePathProxied": file_path_proxied
        }

    async def remove_attachment(self, attachment_id: str) -> Dict[str, Any]:
        """Remove an attachment by id."""
        if self.version in {"1", "3"}:
            url = "/_api/attachments.remove"
        else:
            raise RuntimeError(f"Your Growi REST API version '{self.version}' is not available for remove_attachment")
        data = {"attachment_id": attachment_id}
        res = await self._client.post(url, params=self._with_token(), data=data)
        if res.status_code in {400, 401, 403, 404, 409, 422}: raise RuntimeError(f"Growi API error ({res.status_code}): {res.text}")
        return res.json()

def build_client_from_env() -> GrowiClient:
    """Build GrowiClient from environment variables."""
    load_dotenv()
    domain = _require_env("GROWI_DOMAIN")
    token = _require_env("GROWI_API_TOKEN")
    version = os.getenv("GROWI_API_VERSION", "3").strip() or "3"
    connect_sid = _optional_env("GROWI_CONNECT_SID")
    return GrowiClient(domain=domain, access_token=token, version=version, connect_sid=connect_sid)

"MCP server"
def create_server() -> FastMCP:
    """Create FastMCP server and register tools."""
    server = FastMCP("growi-mcp-server")
    client_holder: Dict[str, GrowiClient] = {}  # Reuse resources

    async def get_client() -> GrowiClient:
        if "client" not in client_holder:
            client_holder["client"] = build_client_from_env()
        return client_holder["client"]

    @server.tool()
    async def get_page_list(ctx: Context, path_or_id: str, limit: Optional[int] = 10, offset: Optional[int] = 0) -> str:
        """
            Get list of pages under a path. If you don't know structures of directory tree of wiki, use this tool to find out overall them.
        
            Args:
                path_or_id (str): Page path or its ID.
                limit (int): Maximum number of items received per request. (Attention: Must keep within the limit of 100.)
                offset (int): The number of top results to skip.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"get_page_list({path_or_id}, limit={max(1, int(limit or 10))}, offset={max(0, int(offset or 0))})")
            data = await client.get_page_list(path_or_id, limit=max(1, int(limit or 10)), offset=max(0, int(offset or 0)))
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)

    @server.tool()
    async def read_page(ctx: Context, path_or_id: str) -> str:
        """
            Get a page by path or its id.
        
            Args:
                path_or_id (str): Page path or its ID.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"read_page({path_or_id})")
            data = await client.get_page(path_or_id)
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)

    @server.tool()
    async def create_page(ctx: Context, path: str, body: Optional[str] = None) -> str:
        """
            Create a page at given path with optional markdown body.
        
            Args:
                path (str): Page path.
                body (str): Updated content.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"create_page({path}, body={body or ''})")
            data = await client.create_page(path, body or "")
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)

    @server.tool()
    async def update_page(ctx: Context, path_or_id: str, body: str) -> str:
        """
            Update an existing page by path or id with new body.
        
            Args:
                path_or_id (str): Page path or its ID.
                body (str): Updated content.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"update_page({path_or_id}, body={body})")
            if path_or_id.startswith("/"):
                data = await client.update_page_by_path(path_or_id, body)
            else:
                data = await client.update_page_by_id(path_or_id, body)
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)

    @server.tool()
    async def rename_page(ctx: Context, path: str, new_path: str) -> str:
        """
            Rename or move a page to new path.
        
            Args:
                path (str): Current page path.
                new_path (str): New page path.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"rename_page({path}, new_path={new_path})")
            data = await client.rename_page(path, new_path)
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)

    @server.tool()
    async def remove_page(ctx: Context, path_or_id: str, recursively: bool = True) -> str:
        """
            Remove a page.
        
            Args:
                path_or_id (str): Page path or its ID.
                recursively (bool): Whether to remove recursively.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"remove_page({path_or_id}, recursively={recursively})")
            data = await client.remove_page(path_or_id, recursively)
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)
        
    @server.tool()
    async def search_pages(ctx: Context, query: str, path: str = "/", limit: Optional[int] = 10, offset: Optional[int] = 0) -> str:
        """
            Search Growi pages by keyword.
        
            Args:
                query (str): Search query.
                path (str): Search Top.
                limit (int): Maximum number of items received per request. (Attention: Must keep within the limit of 100.)
                offset (int): The number of top results to skip.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"search_pages({query}, path={path}, limit={max(1, int(limit or 10))}, offset={max(0, int(offset or 0))})")
            data = await client.search_pages(query, path=path, limit=max(1, int(limit or 10)), offset=max(0, int(offset or 0)))
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)

    @server.tool()
    async def get_user_names(ctx: Context, query: str, limit: Optional[int] = 10, offset: Optional[int] = 0) -> str:
        """
            Get Growi user names by keyword.
        
            Args:
                query (str): Search query.
                limit (int): Maximum number of items received per request. (Attention: Must keep within the limit of 20.)
                offset (int): The number of top results to skip.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"get_user_names({query}, limit={limit}, offset={offset})")
            data = await client.get_user_names(query, limit=limit, offset=offset)
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)

    @server.tool()
    async def register_user(ctx: Context, name: str, username: str, email: str, password: str) -> str:
        """
            Register a user to wiki.
        
            Args:
                name (str): Name for a user. This name is used for display.
                username (str): User name for a user. This name is used for login.
                email (str): Email for a user.
                password (str): Password for a user. Password minimum character should be more than 8 characters.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"register_user(name={name}, username={username}, email={email}, password={password})")
            data = await client.register_user(name=name, username=username, email=email, password=password)
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)

    @server.tool()
    async def upload_attachment(ctx: Context, path_or_page_id: str, file_path: Optional[str]) -> str:
        """
            Upload an attachment to a page.
        
            Args:
                path_or_id (str): Page path or its ID.
                file_path (str): Source file path for upload.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"upload_attachment({path_or_page_id}, file_path={file_path})")
            data = await client.upload_attachment(
                path_or_page_id=path_or_page_id,
                file_path=file_path,
            )
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)

    @server.tool()
    async def get_attachment_list(ctx: Context, path_or_id: str, limit: Optional[int] = 10, offset: Optional[int] = 0) -> str:
        """
            Get list of attachments for a page.
        
            Args:
                path_or_id (str): Page path or its ID.
                limit (int): Maximum number of items received per request. (Attention: Must keep within the limit of 100.)
                offset (int): The number of top results to skip.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"get_attachment_list({path_or_id}, limit={max(1, int(limit or 10))}, offset={max(0, int(offset or 0))})")
            data = await client.get_attachment_list(path_or_id, limit=max(1, int(limit or 10)), offset=max(0, int(offset or 0)))
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)

    @server.tool()
    async def get_attachment_info(ctx: Context, attachment_id: str) -> str:
        """
            Get an attachment by its id. Use this tool when you want to get information such as the attachment's creation date, author, or original filename.
        
            Args:
                attachment_id (str): ID for the attachment.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"get_attachment_info({attachment_id})")
            data = await client.get_attachment_info(attachment_id)
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)

    @server.tool()
    async def download_attachment(ctx: Context, attachment_id: str, save_dir: str = "./attachment") -> str:
        """
            Download an attachment by its id. The downloaded file is saved to a local directory according to arguments.
        
            Args:
                attachment_id (str): ID for the attachment.
                save_dir (str): Save to directory.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"download_attachment({attachment_id}, save_dir={save_dir})")
            data = await client.download_attachment(attachment_id, save_dir)
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)

    @server.tool()
    async def remove_attachment(ctx: Context, attachment_id: str) -> str:
        """
            Remove an attachment by its id.
        
            Args:
                attachment_id (str): ID for the attachment.
            Returns:
                JSON string.
        """
        client = await get_client()
        try:
            await ctx.info(f"remove_attachment({attachment_id})")
            data = await client.remove_attachment(attachment_id)
        except Exception as e:
            await ctx.error(str(e))
            raise e
        return json.dumps(data, ensure_ascii=False, indent=2)
    return server

"main"
def main() -> None:
    server = create_server()
    server.run()

if __name__ == "__main__":
    main()
