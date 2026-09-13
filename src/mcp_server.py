"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE
Mô phỏng MCP Server cho Trợ lý Tra cứu & Tư vấn Tài chính.
"""

import json
import sys
from typing import Any, Dict, List

from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class MCPFinanceServer:
    """MCP Server mô phỏng, trả phản hồi theo cấu trúc JSON-RPC 2.0."""

    def __init__(self, server_name: str = "personal-finance-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"

    def list_tools(self) -> List[Dict[str, Any]]:
        return TOOLS_SCHEMA

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raw_content = dispatch_tool_call(tool_name, arguments)
        try:
            content = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            content = {
                "status": "MCP_PARSE_ERROR",
                "error": f"Tool trả về JSON không hợp lệ: {exc}",
                "raw": raw_content,
            }

        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": content,
        }


if __name__ == "__main__":
    print("==========================================================")
    print("🔌 KIỂM THỬ MCP SERVER - PERSONAL FINANCE")
    print("==========================================================")

    server = MCPFinanceServer()
    tools = server.list_tools()
    print(f"✅ [MCP SERVER] Khởi tạo: {server.server_name} (Version: {server.version})")
    print(f"📦 Số lượng Tools công bố qua MCP: {len(tools)}")
    print("🛠️ Tools:", ", ".join(tool["name"] for tool in tools))

    test_result = server.call_tool("financial_profile_query", {"customer_id": "KH001"})
    if test_result.get("result", {}).get("status") == "SUCCESS":
        print("✅ Test financial_profile_query thành công.")
        print(json.dumps(test_result, ensure_ascii=False, indent=2))
    else:
        print("❌ MCP test thất bại:")
        print(json.dumps(test_result, ensure_ascii=False, indent=2))
