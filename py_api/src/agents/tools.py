"""Tool functions exposed to the AI agents.

All external calls (MCP servers, ClickHouse, HTTP) go through the
functions defined here so that agent logic stays focused on reasoning.
"""

import logging
import re
from typing import Any

import httpx
import sqlglot
from clickhouse_driver import Client as ChClient
from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport
from langchain.mcp import MCPAdapter
from langchain.tools import ToolRuntime, tool
from sqlglot import exp

from config import (
    BYTEHOUSE_URL,
    FALCON_DATA_MCP_SERVER,
    FALCON_DATA_MCP_TOKEN,
    GROWX_MCP_SERVER,
    GROWX_MCP_TOKEN,
)
from models.domain import UserContext

logger = logging.getLogger("pyapi")

# ---------------------------------------------------------------------------
# MCP document loader
# ---------------------------------------------------------------------------

dwh_docs_mcp_tools: list = []


async def load_dwh_docs_mcp():
    """Load MCP tools from the Falcon Data MCP server at startup."""
    global dwh_docs_mcp_tools
    if dwh_docs_mcp_tools:
        return
    transport = StreamableHttpTransport(
        FALCON_DATA_MCP_SERVER,
        headers={"Dev-Key": FALCON_DATA_MCP_TOKEN},
    )
    adapter = MCPAdapter(Client(transport))
    dwh_docs_mcp_tools = await adapter.list_tools()
    logger.info("tools_init", extra={"dwh_mcp_tools": len(dwh_docs_mcp_tools)})


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

def extract_package_names(sql_query: str) -> list[str]:
    """Extract *package_name* values referenced in a SQL statement.

    Parses the query into an AST with *sqlglot* and looks for equality
    and ``IN`` expressions that match ``package_name``.
    """
    package_names: list[str] = []

    parsed = sqlglot.parse_one(sql_query)

    # 1. Equality comparisons: package_name = '...' or '...' = package_name
    for eq in parsed.find_all(exp.EQ):
        if isinstance(eq.left, exp.Column) and eq.left.name.lower() == "package_name":
            package_names.append(eq.right.this)
        elif isinstance(eq.right, exp.Column) and eq.right.name.lower() == "package_name":
            package_names.append(eq.left.this)

    # 2. IN expressions: package_name IN (...)
    for in_expr in parsed.find_all(exp.In):
        if isinstance(in_expr.this, exp.Column) and in_expr.this.name.lower() == "package_name":
            for expression in in_expr.expressions:
                package_names.append(expression.this)

    return package_names


# ---------------------------------------------------------------------------
# HTTP helpers for growX MCP
# ---------------------------------------------------------------------------

def _http_call(params: dict, growx_mcp_personal_key: str) -> dict:
    """Call growX MCP server via HTTP JSON-RPC and return the parsed JSON body."""
    tool_name = params.get("name", "unknown")
    with httpx.Client(verify=True, timeout=60) as client:
        headers = {
            "Authorization": f"Bearer {GROWX_MCP_TOKEN}",
            "Content-Type": "application/json",
            "x-growx-mcp-personal-key": growx_mcp_personal_key,
        }
        resp = client.post(
            GROWX_MCP_SERVER,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": params,
            },
            headers=headers,
        )
        resp.raise_for_status()
        logger.debug("growx_mcp_call", extra={"tool": tool_name, "status": resp.status_code})
        return resp.json()


def _parse_tool_result(raw: dict) -> str:
    """Extract text content from an MCP tool-call response."""
    result = raw.get("result", {})
    content = result.get("content", [])
    if content:
        return content[0].get("text", "")
    return str(result)


# ---------------------------------------------------------------------------
# growX UA tools (HTTP-based, no MCP dependency)
# ---------------------------------------------------------------------------

@tool(parse_docstring=True)
def ua_list_apps(runtime: ToolRuntime[UserContext]) -> str:
    """List every game (app) in the user-acquisition system.

    Call this FIRST before any other UA tool: ``ua_list_campaigns``
    requires an ``appId``, and this is the only place to get one.

    Returns an array of objects with:
        - appId: Pass to ``ua_list_campaigns``
        - name: Human-readable game name
        - bundleId: Store package (e.g. com.os.airforce) - match on this
          when a human names a game in plain words
        - storeId: App store identifier
        - platform: "ios" or "android"
        - active: ``True`` if game is live; ``False`` means archived
          but may still have historical campaigns

    Returns:
        JSON string of the apps array.
    """
    raw = _http_call(
        {"name": "ua_list_apps", "arguments": {}},
        runtime.context.growx_mcp_personal_key,
    )
    return _parse_tool_result(raw)


@tool(parse_docstring=True)
def ua_list_networks(runtime: ToolRuntime[UserContext]) -> str:
    """List every ad network available in the system.

    Returns objects with:
        - code: Lower-case value to pass as the ``network`` argument of
          ``ua_list_campaigns`` (e.g. unity, applovin, mintegral, moloco)
        - displayName: Human-readable network name
        - connectorCount: Number of ad accounts for this network; zero
          means there is nothing to query
        - supportsReporting: If ``False``, the network's campaigns still
          list but every metric comes back absent and
          ``metricsSupported`` is ``False``; this is expected, not an error

    Returns:
        JSON string of the networks array.
    """
    raw = _http_call(
        {"name": "ua_list_networks", "arguments": {}},
        runtime.context.growx_mcp_personal_key,
    )
    return _parse_tool_result(raw)


@tool(parse_docstring=True)
def ua_list_connectors(runtime: ToolRuntime[UserContext], network: str = "") -> str:
    """List the ad accounts (connectors).

    One network usually holds several accounts, so "how is Unity doing
    overall" and "how is our Unity 259 account doing" are different
    questions: answer the first by passing ``network`` to
    ``ua_list_campaigns``, the second by passing ``networkConnectorId``.

    Args:
        network: Optional network code to narrow the list (e.g. "unity").

    Returns:
        JSON string of connectors array. Each object has:
            - connectorId: Pass as ``networkConnectorId`` to ``ua_list_campaigns``
            - name: Human-readable account name
            - networkCode: The network this account belongs to
            - status: "ACTIVE" means the connector is polled; non-ACTIVE
              connectors have stale metrics
    """
    args: dict[str, Any] = {}
    if network:
        args["network"] = network
    raw = _http_call(
        {"name": "ua_list_connectors", "arguments": args},
        runtime.context.growx_mcp_personal_key,
    )
    return _parse_tool_result(raw)


@tool(parse_docstring=True)
def ua_describe_metrics(runtime: ToolRuntime[UserContext]) -> str:
    """The metric dictionary. Call this ONCE before interpreting any number from ``ua_list_campaigns``, and cache it.

    Each entry gives:
        - key: What to pass in the ``metrics`` argument of ``ua_list_campaigns``
        - unit: Measurement unit (COUNT, RATIO_0_1, CURRENCY_USD, etc.)
        - kind: "RAW" = the network reported it; "DERIVED" = this server computed it
        - formula: For derived metrics, the computation formula
        - meaning: Explanation in user-acquisition terms
        - caveat: Warnings to avoid misinterpretation

    CRITICAL: ROAS and retention are percents on a 0..100 scale (85 means
    85 percent, NOT 85 times), while CTR and IR are ratios on a 0..1
    scale (0.03 means 3 percent). Two scales sit side by side in the
    same response object; never compare or average them without converting.

    Returns:
        JSON string of the metrics dictionary.
    """
    raw = _http_call(
        {"name": "ua_describe_metrics", "arguments": {}},
        runtime.context.growx_mcp_personal_key,
    )
    return _parse_tool_result(raw)


@tool(parse_docstring=True)
def ua_list_campaigns(
    runtime: ToolRuntime[UserContext],
    app_id: str,
    network_connector_id: str = "",
    network: str = "",
    status: str = "",
    name: str = "",
    days: int = 0,
    from_date: str = "",
    to_date: str = "",
    metrics: list | None = None,
    page: int = 1,
    page_size: int = 20,
    get_all: bool = False,
) -> str:
    """List one game's ad campaigns with performance over a reporting window.

    The tool that answers "how is this game's user acquisition doing".
    Resolve *app_id* with ``ua_list_apps`` first.

    Args:
        app_id: Required. From ``ua_list_apps``.
        network_connector_id: Scope to ONE ad account. Wins over
            ``network`` when both are given.
        network: Scope to every account of one network (e.g. "unity").
            A network code that matches no account returns zero campaigns.
        status: Campaign status filter: RUNNING, PAUSED, PREPARING,
            PENDING, OUT_OF_SYNC, UNKNOWN, or ALL for every status.
            Defaults to RUNNING when omitted or empty.
        name: Case-insensitive substring match on the campaign name.
        days: Reporting window counting back from today inclusive.
            ``days=1`` is today alone, ``days=7`` is today plus the
            six days before it. Defaults to 7. Mutually exclusive with
            ``from_date``/``to_date``.
        from_date: Window start as YYYY-MM-DD, inclusive. Must be sent
            together with ``to_date``.
        to_date: Window end as YYYY-MM-DD, inclusive. Must be sent
            together with ``from_date``. Explicit dates win over ``days``
            when both arrive.
        metrics: Metric keys from ``ua_describe_metrics`` (e.g.
            ["SPEND", "INSTALLS", "ROAS_D7"]). Omit for the default
            set: IMPRESSIONS, CLICKS, SPEND, INSTALLS.
        page: 1-based page number. Defaults to 1.
        page_size: Rows per page, maximum 200. Defaults to 20.
        get_all: Skip pagination entirely. Refused above 1000 matching
            campaigns rather than truncated, so you never receive a
            partial answer believing it is complete - narrow the filters
            instead.

    Returns:
        JSON string containing:
            - window: The window actually used
            - status: The status filter applied
            - metricKeys: The metric keys resolved
            - paging: Page counts
            - campaigns: Array of campaign objects with performance metrics

    IMPORTANT RULES:
        1. A metric the network never reported is ABSENT from the
           metrics object - absent means unknown, never zero. Check
           ``metricsSupported`` before concluding a campaign earns nothing.
        2. ROAS and retention are percents 0..100; CTR and IR are
           ratios 0..1.
        3. ROAS and retention are COHORT metrics belonging to the users
           installed in the window, so a D7 value for a window that
           ended less than 7 days ago is still maturing and will rise -
           do not call a campaign bad on it.
        4. Numbers are served from a cache and this tool never triggers
           a live network fetch, so polling is cheap, but read
           ``metricsAsOf`` and ``metricsStale`` before reporting a
           number as current.
        5. Judge cost against value: a low CPI with poor D7 ROAS means
           cheap but worthless users.
        6. With no ``status`` argument ONLY RUNNING campaigns come back -
           a total or a spend sum from such a call covers the live
           campaigns, not everything the game ran in the window; pass
           status ALL for every campaign.
    """
    growx_mcp_personal_key = runtime.context.growx_mcp_personal_key
    args: dict[str, Any] = {"appId": app_id}
    if network_connector_id:
        args["networkConnectorId"] = network_connector_id
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
    if page_size > 20:
        args["pageSize"] = page_size
    if get_all:
        args["getAll"] = get_all

    raw = _http_call(
        {"name": "ua_list_campaigns", "arguments": args},
        growx_mcp_personal_key,
    )
    return _parse_tool_result(raw)


# ---------------------------------------------------------------------------
# ClickHouse query tool
# ---------------------------------------------------------------------------

@tool(parse_docstring=True)
def query_sql(sql: str, runtime: ToolRuntime[UserContext]) -> dict:
    """Query SQL on ClickHouse and return the result.

    Enforces row-level security: only games assigned to the user are
    allowed in the query.

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
    allowed_values: set[str] = set()
    for game in games:
        allowed_values.add(game.app_id)
        allowed_values.add(game.package_name)

    # Find all potential game references in SQL:
    # 1. Package name patterns (most common): com.company.game
    # 2. UUID-like patterns (app_id): 8-4-4-4-12 hex digits
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    found_packages = set(extract_package_names(sql))
    found_uuids = set(re.findall(uuid_pattern, sql, re.IGNORECASE))
    found_all = found_packages | found_uuids

    # If no game references found, allow query (might be a system/admin query)
    if found_all:
        disallowed = found_all - allowed_values
        if disallowed:
            logger.warning(
                "query_access_denied",
                extra={
                    "disallowed_games": sorted(disallowed),
                    "allowed_games": sorted(allowed_values),
                },
            )
            return {
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": (
                    f"SQL query references games not assigned to user. "
                    f"Disallowed: {sorted(disallowed)}. "
                    f"Allowed: {sorted(allowed_values)}"
                ),
            }

    ch_client = ChClient.from_url(BYTEHOUSE_URL)
    logger.debug("query_sql_executing", extra={"sql": sql[:200]})
    try:
        data, info = ch_client.execute(sql, with_column_types=True)
        cols = [c[0] for c in info]
        row_count = len(data)
        logger.info(
            "query_sql_success",
            extra={"rows": row_count, "columns": len(cols)},
        )
        return {"columns": cols, "rows": [list(r) for r in data], "row_count": row_count, "error": None}
    except Exception as exc:
        logger.warning("query_sql_error", extra={"error": str(exc)})
        return {"columns": [], "rows": [], "row_count": 0, "error": str(exc)}


# ---------------------------------------------------------------------------
# Exported tool lists
# ---------------------------------------------------------------------------

# All growX tools as a flat list for passing to create_deep_agent
growx_tools = [
    ua_list_apps,
    ua_list_networks,
    ua_list_connectors,
    ua_describe_metrics,
    ua_list_campaigns,
]
