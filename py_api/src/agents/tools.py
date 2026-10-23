import logging
import os
from typing import Any
from clickhouse_driver import Client as ChClient
from langchain.tools import ToolRuntime, tool
from models.domain import UserContext
import httpx
import re
import sqlglot
from sqlglot import exp
from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport
from langchain.mcp import MCPAdapter
import asyncio

logger = logging.getLogger("pyapi")


# HTTP client for growX MCP server
_GROWX_URL = os.getenv("GROWX_MCP_SERVER", "https://growx-dev.falcongames.com/grow-x/api/v1/mcp")
_GROWX_TOKEN = os.getenv("GROWX_MCP_TOKEN", "")
FALCON_DATA_MCP = os.getenv("FALCON_DATA_MCP_SERVER", "https://dwh-access.data4game.com/mcp")
FALCON_DATA_MCP_TOKEN = os.getenv("FALCON_DATA_MCP_TOKEN", "")
BYTEHOUSE_URL = os.getenv("BYTEHOUSE_URL", f"clickhouse://bytehouse:{os.getenv('BYTEHOUSE_KEY')}@gateway.aws-us-east-1.bytehouse.cloud:19000/?secure=true&max_execution_time=60")


dwh_docs_mcp_tools = []

async def load_dwh_docs_mcp():
    global dwh_docs_mcp_tools
    if len(dwh_docs_mcp_tools) != 0:
        return
    transport = StreamableHttpTransport(FALCON_DATA_MCP, headers={"Dev-Key": FALCON_DATA_MCP_TOKEN})
    adapter = MCPAdapter(Client(transport))
    dwh_docs_mcp_tools = await adapter.list_tools()
    logger.info("tools_init", extra={"dwh_mcp_tools": len(dwh_docs_mcp_tools)})


def extract_package_names(sql_query) -> list[str]:
    package_names = []
    
    # Parse câu SQL thành AST (Abstract Syntax Tree)
    parsed = sqlglot.parse_one(sql_query)
    
    # 1. Tìm các phép so sánh bằng (=)
    for eq in parsed.find_all(exp.EQ):
        # Kiểm tra nếu vế trái hoặc vế phải là cột package_name
        if isinstance(eq.left, exp.Column) and eq.left.name.lower() == "package_name":
            # Nếu vế còn lại là chuỗi hoặc biến
            package_names.append(eq.right.this)
        elif isinstance(eq.right, exp.Column) and eq.right.name.lower() == "package_name":
            package_names.append(eq.left.this)

    # 2. Tìm các phép kiểm tra IN
    for in_expr in parsed.find_all(exp.In):
        if isinstance(in_expr.this, exp.Column) and in_expr.this.name.lower() == "package_name":
            # Duyệt qua các giá trị trong danh sách IN
            for expression in in_expr.expressions:
                package_names.append(expression.this)

    return package_names


def _http_call(params: dict, growx_mcp_personal_key: str) -> dict:
    """Call growX MCP server via HTTP JSON-RPC and return parsed result."""
    tool_name = params.get("name", "unknown")
    with httpx.Client(verify=True, timeout=60) as client:
        headers = {
            "Authorization": f"Bearer {_GROWX_TOKEN}", 
            "Content-Type": "application/json",
            "x-growx-mcp-personal-key": growx_mcp_personal_key,
        }
        resp = client.post(
            _GROWX_URL,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params},
            headers=headers,
        )
        resp.raise_for_status()
        logger.debug("growx_mcp_call", extra={"tool": tool_name, "status": resp.status_code})
        return resp.json()


def _parse_tool_result(raw: dict) -> str:
    """Extract text content from MCP tool call response."""
    result = raw.get("result", {})
    content = result.get("content", [])
    if content:
        return content[0].get("text", "")
    return str(result)


# growX UA tools (HTTP-based, no MCP dependency)
@tool(parse_docstring=True)
def ua_list_apps(runtime: ToolRuntime[UserContext]) -> str:
    """List every game (app) in the user-acquisition system.

    Call this FIRST before any other UA tool: ua_list_campaigns requires an appId,
    and this is the only place to get one.

    Returns an array of objects with:
        - appId: Pass to ua_list_campaigns
        - name: Human-readable game name
        - bundleId: Store package (e.g. com.os.airforce) - match on this when a human
          names a game in plain words
        - storeId: App store identifier
        - platform: "ios" or "android"
        - active: True if game is live; False means archived but may still have
          historical campaigns

    Returns:
        JSON string of the apps array.
    """
    growx_mcp_personal_key = runtime.context.growx_mcp_personal_key
    raw = _http_call({"name": "ua_list_apps", "arguments": {}}, growx_mcp_personal_key)
    return _parse_tool_result(raw)


@tool(parse_docstring=True)
def ua_list_networks(runtime: ToolRuntime[UserContext]) -> str:
    """List every ad network available in the system.

    Returns objects with:
        - code: Lower-case value to pass as the network argument of ua_list_campaigns
          (e.g. unity, applovin, mintegral, moloco)
        - displayName: Human-readable network name
        - connectorCount: Number of ad accounts for this network; zero means there is
          nothing to query
        - supportsReporting: If false, the network's campaigns still list but every
          metric comes back absent and metricsSupported is false; this is expected,
          not an error

    Returns:
        JSON string of the networks array.
    """
    growx_mcp_personal_key = runtime.context.growx_mcp_personal_key
    raw = _http_call({"name": "ua_list_networks", "arguments": {}}, growx_mcp_personal_key)
    return _parse_tool_result(raw)


@tool(parse_docstring=True)
def ua_list_connectors(runtime: ToolRuntime[UserContext], network: str = "") -> str:
    """List the ad ACCOUNTS (connectors).

    One network usually holds several accounts, so "how is Unity doing overall"
    and "how is our Unity 259 account doing" are different questions: answer the
    first by passing network to ua_list_campaigns, the second by passing
    networkConnectorId.

    Args:
        network: Optional network code to narrow the list (e.g. "unity").

    Returns:
        JSON string of connectors array. Each object has:
            - connectorId: Pass as networkConnectorId to ua_list_campaigns
            - name: Human-readable account name
            - networkCode: The network this account belongs to
            - status: "ACTIVE" means the connector is polled; non-ACTIVE connectors
              have stale metrics
    """
    growx_mcp_personal_key = runtime.context.growx_mcp_personal_key
    args = {}
    if network:
        args["network"] = network
    raw = _http_call({"name": "ua_list_connectors", "arguments": args}, growx_mcp_personal_key)
    return _parse_tool_result(raw)


@tool(parse_docstring=True)
def ua_describe_metrics(runtime: ToolRuntime[UserContext]) -> str:
    """The metric dictionary. Call this ONCE before interpreting any number from ua_list_campaigns, and cache it.

    Each entry gives:
        - key: What to pass in the metrics argument of ua_list_campaigns
        - unit: Measurement unit (COUNT, RATIO_0_1, CURRENCY_USD, etc.)
        - kind: "RAW" = the network reported it; "DERIVED" = this server computed it
        - formula: For derived metrics, the computation formula
        - meaning: Explanation in user-acquisition terms
        - caveat: Warnings to avoid misinterpretation

    CRITICAL: ROAS and retention are percents on a 0..100 scale (85 means 85 percent,
    NOT 85 times), while CTR and IR are ratios on a 0..1 scale (0.03 means 3 percent).
    Two scales sit side by side in the same response object; never compare or average
    them without converting.

    Returns:
        JSON string of the metrics dictionary.
    """
    growx_mcp_personal_key = runtime.context.growx_mcp_personal_key
    raw = _http_call({"name": "ua_describe_metrics", "arguments": {}}, growx_mcp_personal_key)
    return _parse_tool_result(raw)


@tool(parse_docstring=True)
def ua_list_campaigns(
    runtime: ToolRuntime[UserContext],
    appId: str,
    networkConnectorId: str = "",
    network: str = "",
    status: str = "",
    name: str = "",
    days: int = 0,
    from_date: str = "",
    to_date: str = "",
    metrics: list = None,
    page: int = 1,
    pageSize: int = 20,
    getAll: bool = False,
) -> str:
    """List one game's ad campaigns with performance over a reporting window.

    The tool that answers "how is this game's user acquisition doing".
    Resolve appId with ua_list_apps first.

    Args:
        appId: Required. From ua_list_apps.
        networkConnectorId: Scope to ONE ad account. Wins over network when both
            are given.
        network: Scope to every account of one network (e.g. "unity"). A network
            code that matches no account returns zero campaigns.
        status: Campaign status filter: RUNNING, PAUSED, PREPARING, PENDING,
            OUT_OF_SYNC, UNKNOWN, or ALL for every status. Defaults to RUNNING
            when omitted or empty.
        name: Case-insensitive substring match on the campaign name.
        days: Reporting window counting back from today inclusive. days=1 is today
            alone, days=7 is today plus the six days before it. Defaults to 7.
            Mutually exclusive with from_date/to_date.
        from_date: Window start as YYYY-MM-DD, inclusive. Must be sent together
            with to_date; sending only one is refused.
        to_date: Window end as YYYY-MM-DD, inclusive. Must be sent together with
            from_date. Explicit dates win over days when both arrive.
        metrics: Metric keys from ua_describe_metrics (e.g. ["SPEND", "INSTALLS",
            "ROAS_D7"]). Omit for the default set: IMPRESSIONS, CLICKS, SPEND,
            INSTALLS.
        page: 1-based page number. Defaults to 1.
        pageSize: Rows per page, maximum 200. Defaults to 20.
        getAll: Skip pagination entirely. REFUSED above 1000 matching campaigns
            rather than truncated, so you never receive a partial answer believing
            it is complete - narrow the filters instead.

    Returns:
        JSON string containing:
            - window: The window actually used
            - status: The status filter applied
            - metricKeys: The metric keys resolved
            - paging: Page counts
            - campaigns: Array of campaign objects with performance metrics

    IMPORTANT RULES:
        1. A metric the network never reported is ABSENT from the metrics object -
           absent means unknown, never zero. Check metricsSupported before concluding
           a campaign earns nothing.
        2. ROAS and retention are percents 0..100; CTR and IR are ratios 0..1.
        3. ROAS and retention are COHORT metrics belonging to the users installed in
           the window, so a D7 value for a window that ended less than 7 days ago is
           still maturing and will rise - do not call a campaign bad on it.
        4. Numbers are served from a cache and this tool never triggers a live
           network fetch, so polling is cheap, but read metricsAsOf and
           metricsStale before reporting a number as current.
        5. Judge cost against value: a low CPI with poor D7 ROAS means cheap but
           worthless users.
        6. With no status argument ONLY RUNNING campaigns come back - a total or a
           spend sum from such a call covers the live campaigns, not everything the
           game ran in the window; pass status ALL for every campaign.
    """
    growx_mcp_personal_key = runtime.context.growx_mcp_personal_key
    args: dict[str, Any] = {"appId": appId}
    if networkConnectorId:
        args["networkConnectorId"] = networkConnectorId
    if network:
        args["network"] = network
    if status:
        args["status"] = status
    if name:
        args["name"] = name
    if days > 0:
        args["days"] = days
    if from_date:
        args["from"] = from_date
    if to_date:
        args["to"] = to_date
    if metrics:
        args["metrics"] = metrics
    if page > 1:
        args["page"] = page
    if pageSize > 20:
        args["pageSize"] = pageSize
    if getAll:
        args["getAll"] = True

    raw = _http_call({"name": "ua_list_campaigns", "arguments": args}, growx_mcp_personal_key)
    return _parse_tool_result(raw)


# ClickHouse query tool
@tool(parse_docstring=True)
def query_sql(sql: str, runtime: ToolRuntime[UserContext]) -> dict:
    """Query SQL on ClickHouse and return the result.

    Args:
        sql: SQL query string to execute against the ByteHouse/ClickHouse database.

    Returns:
        Dictionary with:
            - columns: List of column names
            - rows: List of rows, each row is a list of values
            - row_count: Total number of rows returned
            - error: Error message if query failed, None on success
    """
    games = runtime.context.games
    if not games:
        return {"columns": [], "rows": [], "row_count": 0, "error": "No games assigned to user"}
    
    # Extract allowed app_ids and package_names from the user's games list
    allowed_values = set()
    for game in games:
        allowed_values.add(game.app_id)
        allowed_values.add(game.package_name)
    
    # Find all potential game references in SQL:
    # 1. Package name patterns (most common): com.company.game (each segment starts with letter)
    # 2. UUID-like patterns (app_id): 8-4-4-4-12 hex digits
    # package_pattern = r"package_name\s*=\s*'([a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*)+)'"
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    
    # found_packages = set(re.findall(package_pattern, sql, re.IGNORECASE))
    found_packages = set(extract_package_names(sql))
    found_uuids = set(re.findall(uuid_pattern, sql, re.IGNORECASE))
    
    found_all = found_packages | found_uuids
    
    # If no game references found, allow query (might be a system/admin query)
    if found_all:
        # Every referenced game must be in the allowed list
        disallowed = found_all - allowed_values
        if disallowed:
            logger.warning("query_access_denied", extra={"disallowed_games": sorted(disallowed), "allowed_games": sorted(allowed_values)})
            return {
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": f"SQL query references games not assigned to user. Disallowed: {sorted(disallowed)}. Allowed: {sorted(allowed_values)}",
            }

    ch_client = ChClient.from_url(BYTEHOUSE_URL)
    logger.debug("query_sql_executing", extra={"sql": sql[:200]})
    try:
        data, info = ch_client.execute(sql, with_column_types=True)
        cols = [c[0] for c in info]
        row_count = len(data)
        logger.info("query_sql_success", extra={"rows": row_count, "columns": len(cols)})
        return {"columns": cols, "rows": [list(r) for r in data], "row_count": row_count, "error": None}
    except Exception as e:
        logger.warning("query_sql_error", extra={"error": str(e)})
        return {"columns": [], "rows": [], "row_count": 0, "error": str(e)}


# Exported tool list
# All growX tools as a flat list for passing to create_deep_agent
growX_tools = [ua_list_apps, ua_list_networks, ua_list_connectors, ua_describe_metrics, ua_list_campaigns]
