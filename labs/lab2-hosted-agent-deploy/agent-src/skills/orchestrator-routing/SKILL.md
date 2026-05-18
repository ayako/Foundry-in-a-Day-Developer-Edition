---
name: orchestrator-routing
description: ユーザー入力に対して Microsoft 技術専門家エージェントと Web 検索エージェントの呼び分けを制御するスキル。Microsoft 技術関連の質問・Web で最新情報が必要な質問・両者を含む複合的な質問のいずれにも対応する。
metadata:
  author: maf-skills-hostedagent
  version: "1.0"
---

# Orchestrator Routing Skill

このスキルは、ユーザーからの質問に答えるためにどのサブエージェントを呼ぶかを決定する。

## ツール (サブエージェント)

- `ms_learn_agent` — Microsoft 技術 (Azure / Microsoft 365 / .NET / Windows / Microsoft Foundry など) の専門家。
- `web_search_agent` — それ以外の一般的な質問・最新情報の Web 検索担当。

## ルーティングルール

1. 質問が **Microsoft 技術のみ** に関するものなら、`ms_learn_agent` だけを呼び出して回答を作成する。
2. 質問が **Microsoft 技術と無関係** なら、`web_search_agent` だけを呼び出して回答を作成する。
3. 質問が **Microsoft 技術と一般的な話題の両方** を含む複合的なものであれば、`ms_learn_agent` と `web_search_agent` の **両方** を呼び出し、それぞれの結果を統合して 1 つの回答にまとめる。
4. どのツールにどの質問文を渡すかは、サブエージェントが理解しやすいように適切に書き換えてよい。
