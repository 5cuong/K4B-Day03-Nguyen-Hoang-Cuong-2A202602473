"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
"""

import json
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    {
        "name": "financial_profile_query",
        "description": (
            "Tra cứu hồ sơ tài chính cá nhân của khách hàng theo mã khách hàng. "
            "Dùng khi cần biết thu nhập, chi tiêu, tiết kiệm, dư nợ, nghĩa vụ trả nợ, "
            "khẩu vị rủi ro và mục tiêu tài chính."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Mã khách hàng cần tra cứu, ví dụ KH001."
                }
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "create_financial_plan",
        "description": (
            "Tạo và lưu một kế hoạch tư vấn tài chính cá nhân dựa trên hồ sơ, "
            "mục tiêu và mức tiết kiệm hàng tháng đã xác định."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Mã khách hàng, ví dụ KH001."
                },
                "goal": {
                    "type": "string",
                    "description": "Mục tiêu tài chính, ví dụ: Mua nhà sau 5 năm."
                },
                "monthly_saving_target": {
                    "type": "number",
                    "description": "Số tiền mục tiêu tiết kiệm mỗi tháng, đơn vị VND."
                },
                "recommendation": {
                    "type": "string",
                    "description": "Khuyến nghị tài chính ngắn gọn dựa trên dữ liệu hiện có."
                }
            },
            "required": [
                "customer_id",
                "goal",
                "monthly_saving_target",
                "recommendation"
            ]
        }
    }
]


MOCK_DATABASE: Dict[str, Dict[str, Any]] = {
    "KH001": {
        "full_name": "Nguyễn Văn An",
        "monthly_income": 30000000,
        "monthly_expense": 18000000,
        "saving_balance": 120000000,
        "loan_balance": 200000000,
        "monthly_loan_payment": 6000000,
        "risk_profile": "Trung bình",
        "financial_goal": "Mua nhà sau 5 năm"
    },
    "KH002": {
        "full_name": "Trần Thị Bình",
        "monthly_income": 20000000,
        "monthly_expense": 15000000,
        "saving_balance": 40000000,
        "loan_balance": 0,
        "monthly_loan_payment": 0,
        "risk_profile": "Thận trọng",
        "financial_goal": "Xây dựng quỹ dự phòng 6 tháng chi tiêu"
    }
}


CREATED_PLANS: Dict[str, Dict[str, Any]] = {}


def execute_financial_profile_query(customer_id: str) -> str:
    """Tra cứu hồ sơ tài chính theo mã khách hàng."""
    normalized_id = (customer_id or "").strip().upper()
    if not normalized_id:
        return json.dumps(
            {"status": "VALIDATION_ERROR", "message": "customer_id không được để trống."},
            ensure_ascii=False,
        )

    customer = MOCK_DATABASE.get(normalized_id)
    if not customer:
        return json.dumps(
            {
                "status": "NOT_FOUND",
                "customer_id": normalized_id,
                "message": f"Không tìm thấy dữ liệu tài chính của khách hàng '{normalized_id}'."
            },
            ensure_ascii=False,
        )

    data = dict(customer)
    data["monthly_free_cashflow"] = (
        data["monthly_income"]
        - data["monthly_expense"]
        - data["monthly_loan_payment"]
    )
    return json.dumps(
        {
            "status": "SUCCESS",
            "customer_id": normalized_id,
            "data": data
        },
        ensure_ascii=False,
    )


def execute_create_financial_plan(
    customer_id: str,
    goal: str,
    monthly_saving_target: float,
    recommendation: str,
) -> str:
    """Tạo kế hoạch tài chính mock và trả về mã kế hoạch."""
    normalized_id = (customer_id or "").strip().upper()
    if normalized_id not in MOCK_DATABASE:
        return json.dumps(
            {
                "status": "NOT_FOUND",
                "customer_id": normalized_id,
                "message": f"Không thể tạo kế hoạch vì không tồn tại khách hàng '{normalized_id}'."
            },
            ensure_ascii=False,
        )

    if monthly_saving_target is None or float(monthly_saving_target) < 0:
        return json.dumps(
            {
                "status": "VALIDATION_ERROR",
                "message": "monthly_saving_target phải là số không âm."
            },
            ensure_ascii=False,
        )

    profile = MOCK_DATABASE[normalized_id]
    free_cashflow = (
        profile["monthly_income"]
        - profile["monthly_expense"]
        - profile["monthly_loan_payment"]
    )
    target = float(monthly_saving_target)

    plan_id = f"PLAN-{normalized_id}-{len(CREATED_PLANS) + 1:03d}"
    CREATED_PLANS[plan_id] = {
        "customer_id": normalized_id,
        "goal": goal,
        "monthly_saving_target": target,
        "recommendation": recommendation,
    }

    warning = None
    if target > free_cashflow:
        warning = (
            f"Mức tiết kiệm đề xuất {target:,.0f} VND/tháng cao hơn dòng tiền khả dụng "
            f"{free_cashflow:,.0f} VND/tháng; cần điều chỉnh chi tiêu hoặc mục tiêu."
        )

    result = {
        "status": "SUCCESS",
        "plan_id": plan_id,
        "customer_id": normalized_id,
        "goal": goal,
        "monthly_saving_target": target,
        "monthly_free_cashflow": free_cashflow,
        "recommendation": recommendation,
        "message": f"Đã tạo kế hoạch tài chính {plan_id} cho khách hàng {normalized_id}."
    }
    if warning:
        result["warning"] = warning
    return json.dumps(result, ensure_ascii=False)


TOOL_ROUTER = {
    "financial_profile_query": execute_financial_profile_query,
    "create_financial_plan": execute_create_financial_plan,
}


def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Router thực thi Tool và luôn trả về chuỗi JSON."""
    if tool_name not in TOOL_ROUTER:
        return json.dumps(
            {"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại."},
            ensure_ascii=False,
        )
    try:
        return TOOL_ROUTER[tool_name](**arguments)
    except TypeError as exc:
        return json.dumps(
            {"status": "VALIDATION_ERROR", "error": str(exc)},
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps(
            {"status": "EXECUTION_ERROR", "error": str(exc)},
            ensure_ascii=False,
        )
