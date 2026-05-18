"""Foundry Hosted Agent 用エントリポイント。

``ResponsesHostServer`` でオーケストレータをラップし、
ポート 8088 で Responses プロトコル (POST /responses) を提供する。
Foundry プラットフォームが ``FOUNDRY_PROJECT_ENDPOINT`` などの
環境変数を自動注入するため、ここでは追加設定不要。
"""

from __future__ import annotations

from agent_framework_foundry_hosting import ResponsesHostServer
from dotenv import load_dotenv

from orchestrator import build_orchestrator


def main() -> None:
    load_dotenv()  # ローカル動作確認用。Hosted では実質 no-op。
    agent = build_orchestrator()
    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
