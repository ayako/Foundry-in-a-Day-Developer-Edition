# Part 1: Foundry Agent を SDK/CLI で作る → MAF から呼び出す (70min)

## 🎯 このパートのゴール

- Azure CLI (`az`) で Foundry リソース（AI Services / プロジェクト / モデルデプロイ）を作成する
- Foundry SDK (`azure-ai-projects`) を使って **Prompt Agent** を作成する
- Microsoft Agent Framework (MAF) を使って **Agent X** を構築する
- Agent X にカスタムツール（Zava カスタマーサポート用）を実装する
- MAF から Foundry Agent を呼び出す方法を理解する

## 📋 前提条件

| 項目 | 要件 | 確認方法 |
|------|------|---------|
| Python | 3.11 以上 | `python --version` |
| Azure CLI | 2.60 以上 | `az version` |
| VS Code | Python 拡張機能インストール済み | 拡張機能パネルで確認 |
| Azure サブスクリプション | 有効なサブスクリプション | `az account show` |
| Azure CLI ログイン | 正しいテナントにログイン済み | 下記参照 |
| Azure RBAC ロール | 下記ロールが付与済み | 下記参照 |

### 必要な Azure RBAC ロール (IAM)

このワークショップでは以下のロールが必要です:

| ロール | スコープ | 用途 | 演習 |
|--------|---------|------|------|
| `Contributor` | サブスクリプション or リソースグループ | リソース作成 (RG, AI Services, Project, Model Deploy) | 演習 0 |
| `Azure AI Developer` | AI Services リソース or プロジェクト | エージェント作成・呼び出し・モデル推論 | 演習 1〜3 |

> 💡 **自分でリソースを作成する場合** (演習 0): サブスクリプションの `Contributor` があれば十分です。  
> 作成したユーザーには自動的にアクセス権が付きます。

> ⚠️ **他の人が作成したリソースを使う場合**: 管理者に依頼して、AI Services リソースまたはプロジェクトに  
> `Azure AI Developer` ロールを付与してもらう必要があります。

#### ロールの確認方法

```powershell
# 自分のロール割り当てを確認
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) --query "[].{Role:roleDefinitionName, Scope:scope}" -o table
```

#### ロールが不足している場合の付与方法 (管理者向け)

```powershell
# Azure AI Developer ロールを AI Services リソースに付与する例
$USER_ID = az ad signed-in-user show --query id -o tsv
$AI_RESOURCE_ID = az cognitiveservices account show --name <AI_SERVICES_NAME> --resource-group <RESOURCE_GROUP> --query id -o tsv

az role assignment create `
  --assignee $USER_ID `
  --role "Azure AI Developer" `
  --scope $AI_RESOURCE_ID
```

> 💡 **Azure Portal から付与する場合**:  
> AI Services リソース → アクセス制御 (IAM) → ロールの割り当ての追加 → `Azure AI Developer` を検索 → 対象ユーザーを選択

### Azure CLI ログインの確認

```powershell
# 現在のログイン状態を確認
az account show --query "{name:name, tenantId:tenantId}" -o table

# ログインしていない / テナントが違う場合:
az login --tenant <YOUR-TENANT-ID>
```

> ⚠️ **テナント ID の確認方法**: Azure Portal → Microsoft Entra ID → 概要 → テナント ID  
> または `az account list --query "[].{Name:name, TenantId:tenantId}" -o table` で一覧表示

## 🎬 ワークショップのシナリオ

このワークショップでは、架空の EC 企業「**Zava (ザバ)**」のカスタマーサポートを AI エージェントで自動化するシナリオで進めます。

| 項目 | 内容 |
|------|------|
| 企業 | Zava — イヤホン・スマートウォッチ等を販売する架空の EC サイト |
| 課題 | カスタマーサポートの問い合わせ量が増加し、人手では対応しきれない |
| ソリューション | AI エージェントが注文履歴検索・FAQ 回答・エスカレーション判定を自動化 |
| 構成 | Agent X (専門エージェント) を中心としたエージェント構成 |

> 💡 Zava はこのワークショップ用の架空の企業です。実在のサービスとは関係ありません。

---

## 演習 0: Azure CLI で Foundry リソースを作成する (15min)

この演習では Azure CLI を使って、ハンズオンに必要な Foundry リソースを作成します。

### 0.1 変数の設定

```powershell
# ---- お好みで変更してください ----
$RESOURCE_GROUP = "rg-foundry-workshop"
$LOCATION = "eastus2"
$AI_SERVICES_NAME = "ai-foundry-workshop-$(Get-Random -Maximum 9999)"  # 名前はグローバル一意
$PROJECT_NAME = "zava-support"
$MODEL_DEPLOYMENT_NAME = "gpt-4.1-mini"
```

> ⚠️ `$AI_SERVICES_NAME` はグローバルで一意な名前が必要です。`Get-Random` で自動生成していますが、万が一名前が被った場合は再実行してください。

### 0.2 リソースグループの作成

```powershell
az group create --name $RESOURCE_GROUP --location $LOCATION
```

### 0.3 AI Services (Foundry リソース) の作成

```powershell
az cognitiveservices account create `
  --name $AI_SERVICES_NAME `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --kind AIServices `
  --sku S0 `
  --yes
```

### 0.4 Foundry プロジェクトの作成

> ⚠️ `az ai` コマンドは拡張機能を動的インストールする必要があります。**初回のみ** 以下を実行してください:
> ```powershell
> az config set extension.dynamic_install_allow_preview=true
> ```

```powershell
az ai project create `
  --name $PROJECT_NAME `
  --resource-group $RESOURCE_GROUP `
  --ai-resource $AI_SERVICES_NAME
```

### 0.5 モデルのデプロイ

```powershell
az cognitiveservices account deployment create `
  --name $AI_SERVICES_NAME `
  --resource-group $RESOURCE_GROUP `
  --deployment-name $MODEL_DEPLOYMENT_NAME `
  --model-name "gpt-4.1-mini" `
  --model-version "2025-04-14" `
  --model-format OpenAI `
  --sku-name "GlobalStandard" `
  --sku-capacity 30
```

### 0.6 RBAC ロールの付与

演習 1〜3 でエージェント作成・推論を行うには、`Azure AI Developer` ロールが必要です。

```powershell
# 自分のユーザー ID を取得
$USER_ID = az ad signed-in-user show --query id -o tsv

# AI Services リソースの ID を取得
$AI_RESOURCE_ID = az cognitiveservices account show `
  --name $AI_SERVICES_NAME `
  --resource-group $RESOURCE_GROUP `
  --query id -o tsv

# Azure AI Developer ロールを付与
az role assignment create `
  --assignee $USER_ID `
  --role "Azure AI Developer" `
  --scope $AI_RESOURCE_ID
```

**✅ 期待される出力 (抜粋):**
```json
{
  "roleDefinitionName": "Azure AI Developer",
  "principalType": "User",
  "scope": "/subscriptions/.../Microsoft.CognitiveServices/accounts/ai-foundry-workshop-..."
}
```

> 💡 `--role "Azure AI Developer"` がこのワークショップのキーとなるロールです。  
> これがないとエージェントの作成・呼び出し・モデル推論で `Forbidden` エラーになります。  
> ⚠️ ロールの反映には **最大 5 分** かかる場合があります。エラーが出たら少し待ってリトライしてください。

### 0.7 エンドポイントとテナント ID の確認

```powershell
# プロジェクトエンドポイントの取得
$PROJECT_ENDPOINT = az ai project show `
  --name $PROJECT_NAME `
  --resource-group $RESOURCE_GROUP `
  --query "properties.endpoint" -o tsv

Write-Host "Project Endpoint: $PROJECT_ENDPOINT"

# テナント ID の取得
$TENANT_ID = az account show --query tenantId -o tsv
Write-Host "Tenant ID: $TENANT_ID"
```

> 💡 取得した **エンドポイント** と **テナント ID** を次の演習で `.env` に設定します。  
> メモ帳などに控えておいてください。

**✅ 期待される出力例:**
```
Project Endpoint: https://ai-foundry-workshop-1234.services.ai.azure.com/api/projects/zava-support
Tenant ID: 16b3c013-d300-468d-ac64-7eda0820b6d3
```

---

## 演習 1: Foundry SDK でエージェントを作成する (20min)

> ❗ **前提**: 演習 0 が完了していること。プロジェクトエンドポイントとテナント ID が手元にあることを確認してください。

### 1.1 環境セットアップ

リポジトリのルートディレクトリ（`Foundry-in-a-day-3/`）から実行してください:

```powershell
cd labs/lab1-sdk-cli
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

> ⚠️ `pip install` が完了するまで 1〜2 分かかります。エラーが出た場合は Python のバージョンを確認してください。

### 1.2 ライブラリのパッチ適用

現時点の `agent-framework-foundry-hosting` パッケージにはリクエスト処理のバグがあるため、パッチを適用します。

```powershell
python scripts/patch_responses.py
```

**✅ 期待される出力:**
```
パッチ対象: ...\agent_framework_foundry_hosting\_responses.py
✅ パッチ適用完了!
   空の ChatOptions がエージェントに渡されないように修正しました。
```

> 💡 既にパッチ適用済みの場合は「✅ パッチは既に適用済みです。」と表示されます。

### 1.3 環境変数の設定

`.env.template` をコピーして `.env` を作成し、値を設定します。

```powershell
Copy-Item .env.template .env
```

`.env` を VS Code で開いて編集します:

```env
# 演習 0.7 で取得したエンドポイント
FOUNDRY_PROJECT_ENDPOINT="https://<YOUR-RESOURCE-NAME>.services.ai.azure.com/api/projects/<YOUR-PROJECT-NAME>"

# そのまま (演習 0.5 でデプロイしたモデル名)
AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4.1-mini"

# そのまま
AZURE_AI_FOUNDRY_AGENT_NAME="zava-support-agent-x"

# 演習 0.7 で取得したテナント ID
AZURE_TENANT_ID="<YOUR-TENANT-ID>"
```

> ⚠️ **よくあるミス**: エンドポイントの末尾に `/` を付けないでください。  
> 💡 **テナント ID を設定しないとどうなる?**: 認証トークンのテナントが不一致となり、  
> `Token tenant ... does not match resource tenant` エラーが発生します。

### 1.4 Prompt Agent の作成 (SDK)

`src/agent_x/create_agent.py` を実行して Foundry 上に Prompt Agent を作成します。

```powershell
python src/agent_x/create_agent.py
```

**✅ 期待される出力:**
```
✅ Agent created successfully!
   Name:    zava-support-agent-x
   ID:      zava-support-agent-x:1
   Version: 1
   Model:   gpt-4.1-mini

💡 次のステップ: chat_with_agent.py でエージェントと対話してみましょう
```

**ポイント解説:**
- `AIProjectClient` — Foundry プロジェクトに接続するクライアント
- `AzureCliCredential(tenant_id=...)` — `az login` のトークンを使って認証
- `PromptAgentDefinition` — エージェントの定義（モデル・指示文）を設定
- `project.agents.create_version()` — バージョン管理されたエージェントを作成

### 1.5 エージェントとの対話テスト (SDK)

作成したエージェントに対して SDK 経由でメッセージを送信します。

```powershell
python src/agent_x/chat_with_agent.py
```

**✅ 期待される出力例:**
```
🔗 Conversation started (ID: conv_xxxxx...)
🤖 Agent: zava-support-agent-x
--------------------------------------------------

📤 User: 顧客ID C001 の最近の注文について教えてください
📥 Agent: かしこまりました。顧客ID C001様の最近のご注文内容を確認いたします...

📤 User: その注文のステータスを確認してもらえますか？
📥 Agent: 承知いたしました。...

📤 User: 返品ポリシーについて教えてください
📥 Agent: 返品ポリシーについてご案内いたします。...

--------------------------------------------------
✅ マルチターン会話のテスト完了!
```

**ポイント解説:**
- `project.get_openai_client()` — OpenAI 互換クライアントを取得
- `openai.conversations.create()` — マルチターン会話を開始（会話 ID で状態管理）
- `openai.responses.create(conversation=..., input=...)` — 会話 ID を指定してメッセージ送信
- `extra_body={"agent_reference": ...}` — 呼び出すエージェントを名前で指定

> 💡 **なぜ OpenAI 互換?**: Foundry は OpenAI API と互換のインターフェースを提供しています。  
> 既存の OpenAI SDK の知識がそのまま使えるため、学習コストが低いのがメリットです。

---

## 演習 2: MAF で Agent X を構築する (20min)

### 2.1 Agent X の概要

Agent X は **Zava カスタマーサポートの専門エージェント** です。以下のツールを持ちます:

| ツール | 説明 | 利用シーン |
|--------|------|-----------|
| `search_order_history` | 顧客の注文履歴を検索する | 「注文の状況を教えて」 |
| `search_faq` | FAQ データベースから回答を検索する | 「返品ポリシーは？」 |
| `check_escalation_needed` | エスカレーションが必要か判定する | 「不良品だ！返金しろ！」 |

> 💡 **MAF とは?**: Microsoft Agent Framework はエージェントの構築・ホスティングを行うフレームワークです。  
> ツール定義 + LLM クライアント + 指示文を一つの Agent オブジェクトにまとめ、HTTP サーバーとして公開できます。

### 2.2 コード解説: main.py

`src/agent_x/main.py` を VS Code で開いて構造を確認します。

```python
from agent_framework import Agent, tool          # MAF コア
from agent_framework.foundry import FoundryChatClient  # Foundry 接続
from agent_framework_foundry_hosting import ResponsesHostServer  # HTTP サーバー
```

**重要な構成要素:**

| コンポーネント | 役割 |
|----------------|------|
| `FoundryChatClient` | Foundry プロジェクトのモデルに接続するクライアント |
| `@tool` デコレータ | Python 関数を LLM が呼び出せるツールとして登録 |
| `Agent` | ツール + 指示文 + クライアントを束ねるエージェント定義 |
| `ResponsesHostServer` | Responses プロトコルで HTTP サーバーを起動 (port 8088) |

### 2.3 ツールの実装

各ツールは `@tool` デコレータで定義します:

```python
@tool(approval_mode="never_require")
def search_order_history(
    customer_id: Annotated[str, Field(description="顧客ID")],
) -> str:
    """顧客の注文履歴を検索します。"""
    # 実装...
```

**ツール定義のポイント:**
- `@tool(approval_mode="never_require")` — 人間の承認なしで自動実行
- `Annotated[str, Field(description="...")]` — LLM に引数の説明を伝える
- docstring — LLM がツール選択時に参照する説明文

> 💡 **ハンズオン**: `src/agent_x/main.py` のツール部分を確認し、追加のツールを実装してみましょう。

### 2.4 ローカルでの実行とテスト

**ターミナル 1** でサーバーを起動:

```powershell
python src/agent_x/main.py
```

**✅ 期待される出力:**
```
🚀 Agent X starting on http://localhost:8088
   POST /responses でリクエストを送信してください
   Microsoft Learn MCP: 有効
YYYY-MM-DD ... INFO __main__: Microsoft Learn MCP tool registered
YYYY-MM-DD ... INFO hypercorn.error: Running on http://0.0.0.0:8088 (CTRL + C to quit)
```

> 💡 `Running on http://0.0.0.0:8088` が表示されたらサーバー起動完了です。  
> この状態でターミナルはブロックされるので、**別のターミナルを開いて** テストしてください。

**ターミナル 2** (新しいターミナルを開く) でリクエスト送信:

> 💡 以下のコマンドは長いですが、そのままコピー＆ペーストしてください。

```powershell
# 注文履歴の検索テスト
$body = '{"input": "顧客ID: C001 の注文履歴を教えて", "model": "gpt-4.1-mini"}'
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
(Invoke-WebRequest -Uri http://localhost:8088/responses -Method POST -ContentType "application/json" -Body $bytes -TimeoutSec 60).Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

> 💡 日本語を含む JSON を送る際は `[System.Text.Encoding]::UTF8.GetBytes()` で変換が必要です。  
> これがないと文字化けしてエージェントが正しく応答できません。

**✅ 期待される出力 (抜粋):**
```json
{
  "status": "completed",
  "output": [
    { "type": "function_call", "name": "search_order_history", ... },
    { "type": "function_call_output", ... },
    { "type": "message", "content": [{ "text": "顧客ID C001 の注文履歴は..." }] }
  ]
}
```

> 💡 `status` が `"completed"` であれば成功です。`"failed"` の場合はトラブルシューティングを参照してください。

**ストリーミングのテスト:**

```powershell
$body = '{"input": "FAQ: 返品について", "model": "gpt-4.1-mini", "stream": true}'
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
(Invoke-WebRequest -Uri http://localhost:8088/responses -Method POST -ContentType "application/json" -Body $bytes -TimeoutSec 60).Content
```

SSE (Server-Sent Events) 形式でイベントが返ります。最後に `event: response.completed` が表示されれば成功です。

---

## 演習 3: MAF から Foundry Agent を呼び出す (10min)

### 3.1 呼び出しパターン

演習 1 で作成した Prompt Agent を、別の MAF エージェントから呼び出す方法:

```python
from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential

project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=AzureCliCredential(tenant_id=TENANT_ID),
)
openai = project.get_openai_client()

# 会話を開始
conversation = openai.conversations.create()

# Agent X を呼び出し
response = openai.responses.create(
    conversation=conversation.id,
    extra_body={"agent_reference": {"name": "zava-support-agent-x", "type": "agent_reference"}},
    input="顧客C001の注文履歴を検索して",
)
print(response.output_text)
```

**ポイント解説:**
- `agent_reference` — Foundry に登録済みのエージェントを名前で指定して呼び出す仕組み
- 呼び出し元は **エージェントのツール実装を知らなくても** 名前だけで利用できる
- これにより、エージェント間の疎結合な連携が実現できる

### 3.2 デモ: MAF Orchestrator からの呼び出し

`src/maf_orchestrator/call_agent_x.py` を実行:

```powershell
python src/maf_orchestrator/call_agent_x.py
```

**✅ 期待される出力例:**
```
============================================================
MAF Orchestrator → Agent X 呼び出しデモ
============================================================

--- シナリオ 1: 注文履歴 ---
Response: 申し訳ございませんが、顧客C001様の注文履歴を確認するには...
Conversation ID: conv_xxxxx...

--- シナリオ 2: フォローアップ ---
Response: ご注文の配送状況について...

--- シナリオ 3: FAQ ---
Response: 返品のルールについてご案内いたします...

--- シナリオ 4: エスカレーション ---
Response: ご連絡いただきありがとうございます。このたびは...

============================================================
✅ 全シナリオ完了
```

> ⚠️ **注意**: Prompt Agent (演習 1 で作成) はツールを持たないため、「注文履歴を検索して」と依頼しても  
> 実際にはデータベース検索は行わず、一般的な回答を返します。  
> ツール付きの Agent X (演習 2) をホストした場合は、実際にツールが呼ばれます。

---

## 📝 まとめ

| やったこと | 使った技術 |
|------------|-----------|
| Foundry リソース作成 | Azure CLI (`az`) |
| Prompt Agent の作成 | `azure-ai-projects` SDK |
| Agent X の構築 | Microsoft Agent Framework (MAF) |
| ツール実装 | `@tool` デコレータ |
| ローカルテスト | `ResponsesHostServer` (port 8088) |
| Agent 間連携 | `agent_reference` による呼び出し |

## 🔗 参考リンク

- [Foundry Samples (GitHub)](https://github.com/microsoft-foundry/foundry-samples)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [Foundry Hosted Agents Docs](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/hosted-agents)
- [Agent Framework Quick Start](https://learn.microsoft.com/agent-framework/tutorials/quick-start)

---

## 🚨 トラブルシューティング

### エラー: `Token tenant ... does not match resource tenant`

**原因**: `.env` の `AZURE_TENANT_ID` が未設定、または `az login` のテナントとリソースのテナントが異なる。

**解決方法**:
```powershell
# 正しいテナント ID を確認
az account show --query tenantId -o tsv

# .env に設定
# AZURE_TENANT_ID="<上記の値>"

# 必要なら正しいテナントで再ログイン
az login --tenant <TENANT-ID>
```

### エラー: `status: "failed"` / `An internal server error occurred.`

**原因**: `agent-framework-foundry-hosting` パッケージのバグ。空の options が渡されてエージェントがハングする。

**解決方法**:
```powershell
python scripts/patch_responses.py
# サーバーを Ctrl+C で停止して再起動
python src/agent_x/main.py
```

### エラー: `Invoke-WebRequest` でタイムアウト

**原因**: サーバーが起動していない、またはポート 8088 が使用中。

**解決方法**:
```powershell
# サーバーが起動しているか確認
Get-NetTCPConnection -LocalPort 8088 -ErrorAction SilentlyContinue

# ポートが使用中なら停止
Get-NetTCPConnection -LocalPort 8088 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# サーバーを再起動
python src/agent_x/main.py
```

### エラー: `az ai project create` が失敗する

**原因**: `az ai` 拡張機能がインストールされていない。

**解決方法**:
```powershell
# 動的インストールを有効化
az config set extension.dynamic_install_allow_preview=true

# 再実行
az ai project create --name $PROJECT_NAME --resource-group $RESOURCE_GROUP --ai-resource $AI_SERVICES_NAME
```

### エラー: `ModuleNotFoundError: No module named 'agent_framework'`

**原因**: 仮想環境が有効化されていない。

**解決方法**:
```powershell
# 仮想環境を有効化
.venv\Scripts\activate

# パッケージがインストールされているか確認
pip list | Select-String "agent-framework"
```

### リクエストが長時間応答しない (ハングする)

**原因**: パッチ未適用の可能性が高い。

**解決方法**:
1. Ctrl+C でサーバーを停止
2. `python scripts/patch_responses.py` を実行
3. サーバーを再起動: `python src/agent_x/main.py`

### エラー: `AuthorizationFailed` / `does not have authorization to perform action`

**原因**: 必要な RBAC ロールが付与されていない。

**解決方法**:
```powershell
# 自分の現在のロールを確認
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) --query "[].{Role:roleDefinitionName, Scope:scope}" -o table
```

必要なロール:
- リソース作成 (演習 0): サブスクリプションまたはリソースグループの `Contributor`
- エージェント作成・利用 (演習 1〜3): AI Services リソースの `Azure AI Developer`

管理者に以下を依頼してください:
```powershell
# 管理者が実行: Azure AI Developer ロールの付与
az role assignment create `
  --assignee <YOUR-USER-OBJECT-ID> `
  --role "Azure AI Developer" `
  --scope /subscriptions/<SUB-ID>/resourceGroups/<RG>/providers/Microsoft.CognitiveServices/accounts/<AI-SERVICES-NAME>
```

### エラー: `Forbidden` / `Principal does not have access to API/Operation`

**原因**: `Azure AI Developer` ロールが AI Services リソースに付与されていない（プロジェクトに対してのみ付与されている等）。

**解決方法**: ロールの割り当てスコープを確認。AI Services リソース（親リソース）に付与する必要があります。
```powershell
# AI Services リソース自体に対してロールを付与 (プロジェクトではなく)
$AI_RESOURCE_ID = az cognitiveservices account show --name <AI_SERVICES_NAME> --resource-group <RESOURCE_GROUP> --query id -o tsv
az role assignment create --assignee $(az ad signed-in-user show --query id -o tsv) --role "Azure AI Developer" --scope $AI_RESOURCE_ID
```
