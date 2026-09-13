"""
🔌 MULTI-PROVIDER LLM ADAPTER
Hỗ trợ Gemini, OpenAI và Mock Offline cho bài Lab ReAct Agent.
"""

import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()


class BaseLLMProvider:
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
    ) -> Dict[str, Any]:
        raise NotImplementedError


def _split_agent_prompt(prompt: str) -> Tuple[str, List[Dict[str, Any]]]:
    marker = "\nOBSERVATION_HISTORY_JSON:\n"
    if marker not in prompt:
        return prompt, []
    user_query, raw_history = prompt.split(marker, 1)
    user_query = user_query.removeprefix("USER_QUERY:\n").strip()
    try:
        history = json.loads(raw_history.strip())
        if not isinstance(history, list):
            history = []
    except json.JSONDecodeError:
        history = []
    return user_query, history


def _extract_customer_id(text: str) -> str:
    match = re.search(r"\bKH\d{3,}\b", text, flags=re.IGNORECASE)
    return match.group(0).upper() if match else "KH001"


def _extract_money(text: str) -> float:
    # Bắt các mẫu như 5.000.000 đồng hoặc 5000000 đồng.
    match = re.search(r"([\d\.]{4,})\s*(?:đồng|vnd)", text, flags=re.IGNORECASE)
    if not match:
        return 0.0
    raw = match.group(1).replace(".", "")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _last_observation(history: List[Dict[str, Any]], tool_name: str = "") -> Dict[str, Any]:
    for item in reversed(history):
        if tool_name and item.get("tool_name") != tool_name:
            continue
        obs = item.get("observation")
        if isinstance(obs, dict):
            return obs
    return {}


def _format_profile(obs: Dict[str, Any]) -> str:
    data = obs.get("data", {})
    return (
        f"Khách hàng {obs.get('customer_id', '')} - {data.get('full_name', '')}; "
        f"thu nhập {data.get('monthly_income', 0):,.0f} VND/tháng; "
        f"chi tiêu {data.get('monthly_expense', 0):,.0f} VND/tháng; "
        f"trả nợ {data.get('monthly_loan_payment', 0):,.0f} VND/tháng; "
        f"dòng tiền khả dụng {data.get('monthly_free_cashflow', 0):,.0f} VND/tháng; "
        f"tiết kiệm hiện có {data.get('saving_balance', 0):,.0f} VND; "
        f"dư nợ {data.get('loan_balance', 0):,.0f} VND; "
        f"khẩu vị rủi ro: {data.get('risk_profile', '')}; "
        f"mục tiêu: {data.get('financial_goal', '')}."
    )


class MockOfflineProvider(BaseLLMProvider):
    """Mock có state thông qua Observation History để mô phỏng ReAct đa bước."""

    def __init__(self):
        self.model_name = "Offline-Mock-Finance-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return (
            "[Mock Chatbot Response]: Quỹ dự phòng là khoản tiền dành cho các sự kiện "
            "không lường trước. Thực tế thường được xây dựng theo nhiều tháng chi tiêu thiết yếu; "
            "mức cụ thể phụ thuộc hoàn cảnh và khả năng dòng tiền của mỗi người."
        )

    def generate_with_tools(
        self,
        prompt: str,
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
    ) -> Dict[str, Any]:
        user_query, history = _split_agent_prompt(prompt)
        query_lower = user_query.lower()
        customer_id = _extract_customer_id(user_query)

        plan_obs = _last_observation(history, "create_financial_plan")
        if plan_obs:
            if plan_obs.get("status") == "SUCCESS":
                warning = f" Cảnh báo: {plan_obs['warning']}" if plan_obs.get("warning") else ""
                return {
                    "type": "text",
                    "content": (
                        f"Đã tạo kế hoạch {plan_obs.get('plan_id')} cho {plan_obs.get('customer_id')}. "
                        f"Mục tiêu: {plan_obs.get('goal')}. "
                        f"Tiết kiệm đề xuất: {plan_obs.get('monthly_saving_target', 0):,.0f} VND/tháng. "
                        f"Khuyến nghị: {plan_obs.get('recommendation')}.{warning}"
                    ),
                    "thought": "Đã có Observation tạo kế hoạch thành công nên có thể kết thúc.",
                }
            return {
                "type": "text",
                "content": plan_obs.get("message") or plan_obs.get("error") or "Không thể tạo kế hoạch.",
                "thought": "Tool tạo kế hoạch trả lỗi nên dừng.",
            }

        profile_obs = _last_observation(history, "financial_profile_query")
        if profile_obs:
            if profile_obs.get("status") != "SUCCESS":
                return {
                    "type": "text",
                    "content": profile_obs.get("message") or profile_obs.get("error") or "Không tìm thấy hồ sơ tài chính.",
                    "thought": "Không có hồ sơ hợp lệ nên không được cá nhân hóa tư vấn.",
                }

            wants_plan = any(
                phrase in query_lower
                for phrase in ["kế hoạch", "xây dựng", "tư vấn", "mục tiêu", "mua nhà"]
            )
            is_multistep = any(phrase in query_lower for phrase in ["sau đó", "dựa trên", "rồi"])
            if wants_plan and is_multistep:
                data = profile_obs.get("data", {})
                free_cashflow = max(float(data.get("monthly_free_cashflow", 0)), 0.0)
                goal = data.get("financial_goal") or "Cải thiện an toàn tài chính"
                recommendation = (
                    "Ưu tiên duy trì quỹ dự phòng, kiểm soát chi tiêu và không tăng nghĩa vụ nợ mới; "
                    "phân bổ phần dòng tiền khả dụng đều đặn cho mục tiêu đã xác định."
                )
                return {
                    "type": "tool_call",
                    "tool_name": "create_financial_plan",
                    "arguments": {
                        "customer_id": profile_obs.get("customer_id", customer_id),
                        "goal": goal,
                        "monthly_saving_target": free_cashflow,
                        "recommendation": recommendation,
                    },
                    "thought": "Đã có hồ sơ; bước tiếp theo là tạo kế hoạch dựa trên dòng tiền khả dụng.",
                }

            return {
                "type": "text",
                "content": _format_profile(profile_obs),
                "thought": "Observation đã đủ để trả lời yêu cầu tra cứu.",
            }

        is_multistep = (
            any(phrase in query_lower for phrase in ["kiểm tra", "tra cứu"])
            and any(phrase in query_lower for phrase in ["sau đó", "dựa trên", "rồi"])
            and any(phrase in query_lower for phrase in ["kế hoạch", "tư vấn", "mua nhà"])
        )
        if is_multistep:
            return {
                "type": "tool_call",
                "tool_name": "financial_profile_query",
                "arguments": {"customer_id": customer_id},
                "thought": "Cần tra cứu hồ sơ tài chính trước khi lập kế hoạch cá nhân hóa.",
            }

        if "tạo kế hoạch" in query_lower or "kế hoạch tài chính" in query_lower:
            saving_target = _extract_money(user_query) or 5000000.0
            goal = "Xây dựng quỹ dự phòng 6 tháng chi tiêu" if "quỹ dự phòng" in query_lower else "Mục tiêu tài chính cá nhân"
            return {
                "type": "tool_call",
                "tool_name": "create_financial_plan",
                "arguments": {
                    "customer_id": customer_id,
                    "goal": goal,
                    "monthly_saving_target": saving_target,
                    "recommendation": "Duy trì mức tiết kiệm đều đặn, theo dõi ngân sách hàng tháng và đánh giá lại kế hoạch định kỳ.",
                },
                "thought": "Người dùng đã yêu cầu tạo kế hoạch và cung cấp mục tiêu/mức tiết kiệm.",
            }

        if "tra cứu" in query_lower or "tình hình tài chính" in query_lower or re.search(r"\bKH\d{3,}\b", user_query, flags=re.IGNORECASE):
            return {
                "type": "tool_call",
                "tool_name": "financial_profile_query",
                "arguments": {"customer_id": customer_id},
                "thought": "Yêu cầu cần dữ liệu tài chính riêng nên phải gọi công cụ tra cứu.",
            }

        return {
            "type": "text",
            "content": (
                "[Mock Agent Response]: Tôi có thể giải thích kiến thức tài chính chung; "
                "với dữ liệu khách hàng hoặc kế hoạch cá nhân hóa, tôi sẽ dùng Tool phù hợp."
            ),
            "thought": "Câu hỏi chung không cần Tool.",
        }


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return MockOfflineProvider().generate(prompt, system_prompt)
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                temperature=0.2,
            )
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception as exc:
            return f"[Gemini Exception]: {exc}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            declarations = [
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                }
                for tool in tools_schema
                if tool.get("name") and tool.get("parameters")
            ]
            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[types.Tool(function_declarations=declarations)] if declarations else None,
                temperature=0.2,
            )
            response = client.models.generate_content(model=self.model_name, contents=prompt, config=config)
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if getattr(call, "args", None) else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Chọn công cụ '{call.name}' vì cần dữ liệu hoặc hành động bên ngoài.",
                }
            return {
                "type": "text",
                "content": response.text or "",
                "thought": "Đã đủ thông tin để trả lời mà không cần gọi thêm Tool.",
            }
        except Exception as exc:
            print(f"⚠️ [Gemini API Warning]: {exc}. Fallback Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return MockOfflineProvider().generate(prompt, system_prompt)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as exc:
            return f"[OpenAI Exception]: {exc}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {}),
                    },
                }
                for tool in tools_schema
                if tool.get("name")
            ]
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools or None,
                tool_choice="auto" if tools else None,
            )
            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"Chọn công cụ '{call.function.name}' vì cần dữ liệu hoặc hành động bên ngoài.",
                }
            return {
                "type": "text",
                "content": msg.content or "",
                "thought": "Đã đủ thông tin để trả lời mà không cần gọi thêm Tool.",
            }
        except Exception as exc:
            print(f"⚠️ [OpenAI API Warning]: {exc}. Fallback Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


def get_llm_provider() -> BaseLLMProvider:
    provider_type = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        return GeminiProvider() if key and key != "your_gemini_api_key_here" else MockOfflineProvider()
    if provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        return OpenAIProvider() if key and key != "your_openai_api_key_here" else MockOfflineProvider()
    return MockOfflineProvider()
