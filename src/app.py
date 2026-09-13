x   """
🚀 CORE AGENT APPLICATION - FINANCIAL ADVISORY REACT AGENT
So sánh Chatbot Baseline (Cấp 2) và ReAct Agent + MCP (Cấp 3).
"""

import json
import os
import sys
import time
from typing import Any, Dict, List

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from mcp_server import MCPFinanceServer
from prompts import CHATBOT_BASELINE_PROMPT, MAX_ITERATIONS, REACT_AGENT_SYSTEM_PROMPT
from providers import get_llm_provider

load_dotenv()


def project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_test_cases() -> List[Dict[str, Any]]:
    config_path = os.path.join(project_root(), "config", "test_cases.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(project_root(), "config", "test_cases.example.json")
    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_waterfall_trace(trace_data: list) -> str:
    docs_dir = os.path.join(project_root(), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as file:
        json.dump(trace_data, file, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện tại '{trace_path}'.")
    return trace_path


def run_baseline_chatbot(user_query: str, provider) -> str:
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")
    return response


def _build_agent_prompt(user_query: str, history: List[Dict[str, Any]]) -> str:
    return (
        f"USER_QUERY:\n{user_query}\n"
        "OBSERVATION_HISTORY_JSON:\n"
        f"{json.dumps(history, ensure_ascii=False)}"
    )


def _fallback_answer(observation: Dict[str, Any]) -> str:
    status = observation.get("status")
    if status == "SUCCESS" and observation.get("message"):
        return observation["message"]
    if status == "SUCCESS" and "data" in observation:
        d = observation["data"]
        return (
            f"Khách hàng {observation.get('customer_id', '')}: thu nhập {d.get('monthly_income', 0):,.0f} VND/tháng, "
            f"chi tiêu {d.get('monthly_expense', 0):,.0f} VND/tháng, "
            f"trả nợ {d.get('monthly_loan_payment', 0):,.0f} VND/tháng, "
            f"dòng tiền khả dụng {d.get('monthly_free_cashflow', 0):,.0f} VND/tháng."
        )
    return observation.get("message") or observation.get("error") or json.dumps(observation, ensure_ascii=False)


def run_react_agent(user_query: str, provider, mcp_server: MCPFinanceServer) -> list:
    """ReAct loop: LLM -> Action -> MCP Observation -> LLM ... -> Final Answer."""
    print(f"\n🤖 [FINANCIAL REACT AGENT] Câu hỏi: {user_query}")
    trace_logs: List[Dict[str, Any]] = []
    observation_history: List[Dict[str, Any]] = []
    executed_calls = set()
    tools_list = mcp_server.list_tools()
    provider_name = provider.__class__.__name__

    for step in range(1, MAX_ITERATIONS + 1):
        print(f"\n--- 🔄 ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")
        step_start = time.perf_counter()
        agent_prompt = _build_agent_prompt(user_query, observation_history)
        llm_response = provider.generate_with_tools(
            agent_prompt,
            tools_list,
            system_prompt=REACT_AGENT_SYSTEM_PROMPT,
        )
        latency_ms = round((time.perf_counter() - step_start) * 1000, 2)
        thought = llm_response.get("thought", "Đang xác định bước xử lý tiếp theo.")
        print(f"🧠 [Thought]: {thought}")

        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "").strip()
            if not final_content and observation_history:
                final_content = _fallback_answer(observation_history[-1]["observation"])
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "provider": provider_name,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": latency_ms,
            })
            return trace_logs

        if llm_response.get("type") != "tool_call":
            final_content = "LLM trả về định dạng không hợp lệ; không thể tiếp tục ReAct Loop."
            trace_logs.append({
                "step": step,
                "query": user_query,
                "provider": provider_name,
                "action_type": "FINAL_ANSWER",
                "thought": "Phản hồi LLM không đúng schema ứng dụng.",
                "output": final_content,
                "latency_ms": latency_ms,
            })
            return trace_logs

        tool_name = llm_response.get("tool_name", "")
        arguments = llm_response.get("arguments") or {}
        call_signature = (tool_name, json.dumps(arguments, ensure_ascii=False, sort_keys=True))
        print(f"🛠️ [Action]: {tool_name}({arguments})")

        if call_signature in executed_calls:
            last_obs = observation_history[-1]["observation"] if observation_history else {}
            final_content = _fallback_answer(last_obs)
            print("⚠️ [LOOP GUARD]: Tool call bị lặp; dừng để tránh vòng lặp vô hạn.")
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "provider": provider_name,
                "action_type": "FINAL_ANSWER",
                "thought": "Phát hiện Tool call lặp lại với cùng tham số.",
                "output": final_content,
                "latency_ms": latency_ms,
            })
            return trace_logs

        executed_calls.add(call_signature)
        tool_start = time.perf_counter()
        mcp_result = mcp_server.call_tool(tool_name, arguments)
        tool_latency_ms = round((time.perf_counter() - tool_start) * 1000, 2)
        observation = mcp_result.get("result", {})
        print(f"👁️ [Observation]: {json.dumps(observation, ensure_ascii=False)}")

        trace_logs.append({
            "step": step,
            "query": user_query,
            "provider": provider_name,
            "action_type": "TOOL_EXECUTION",
            "thought": thought,
            "tool_name": tool_name,
            "arguments": arguments,
            "observation": observation,
            "latency_ms": round(latency_ms + tool_latency_ms, 2),
        })
        observation_history.append({
            "tool_name": tool_name,
            "arguments": arguments,
            "observation": observation,
        })

    last_obs = observation_history[-1]["observation"] if observation_history else {}
    final_content = _fallback_answer(last_obs) if last_obs else "Đã đạt MAX_ITERATIONS nhưng chưa có kết quả cuối cùng."
    trace_logs.append({
        "step": MAX_ITERATIONS + 1,
        "query": user_query,
        "provider": provider_name,
        "action_type": "FINAL_ANSWER",
        "thought": "Đã đạt giới hạn số vòng ReAct.",
        "output": final_content,
        "latency_ms": 0.0,
    })
    print(f"🏁 [Final Answer]: {final_content}")
    return trace_logs


def main() -> None:
    print("==========================================================")
    print("💰 DAY 03 LAB: FINANCIAL ADVISORY REACT AGENT")
    print("==========================================================")

    provider = get_llm_provider()
    mcp_server = MCPFinanceServer()
    tests = load_test_cases()

    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}")
    print(f"✅ Đã tải {len(tests)} Test Cases.\n")

    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Gõ 'exit' hoặc 'quit' để thoát.")
        while True:
            try:
                user_input = input("👤 Người dùng hỏi: ").strip()
                if not user_input or user_input.lower() in {"exit", "quit"}:
                    print("👋 Kết thúc phiên trò chuyện.")
                    break
                logs = run_react_agent(user_input, provider, mcp_server)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
        return

    if "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Chạy toàn bộ Test Cases:")
        all_traces = []
        completed = 0
        todo = 0
        for tc in tests:
            print("\n==================================================")
            print(f"🧪 [{tc['id']}] {tc['type']} | Complexity: {tc['complexity']}")
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")
            question = tc["question"].strip()
            if question.startswith("TODO"):
                print(f"⏸️ Chưa kích hoạt: {question}")
                todo += 1
                continue
            logs = run_react_agent(question, provider, mcp_server)
            all_traces.extend(logs)
            completed += 1

        print("\n==================================================")
        print(f"📊 [KẾT QUẢ TEST SUITE]: {completed}/{len(tests)} đã chạy | {todo} TODO")
        if all_traces:
            save_waterfall_trace(all_traces)
        return

    print("ℹ️ Cách chạy:")
    print("  python src/app.py --all")
    print("  python src/app.py --interactive")
    print("\n--- DEMO TC02 ---")
    logs = run_react_agent("Hãy tra cứu tình hình tài chính hiện tại của khách hàng KH001.", provider, mcp_server)
    save_waterfall_trace(logs)


if __name__ == "__main__":
    main()
