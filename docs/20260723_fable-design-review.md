# Fable × codex-build 設計確認 引き継ぎ資料

- 日付: 2026-07-23
- 作業者: Claude (Fable 5) — 設計確認のみ。コード変更・コミット・push・PR作成は未実施
- 作業フォルダー: `/Users/k.cross/Documents/10_Apps/fable-orchestrator`
- ブランチ: `codex/fable-bootstrap`
- ベース: https://github.com/cathrynlavery/codex-build (`main`)
- 本資料の目的: 設計判断の記録と、Codex への最初の実装計画（T1〜T3）の引き継ぎ

---

## 0. 前提となる重要事実（リポジトリ実調査の結果）

- **codex-build はプログラムではなく Claude Code のスキル**。実体は
  `skills/codex-build/SKILL.md`（手順書 v2.1）と `skills/codex-build/scripts/check_scope.py`（ファイルスコープ検査）。
- 「Fable → codex-build へ渡す」は API 呼び出しではなく、**計画ファイル（Markdown）の受け渡しとスキル起動**。
- 計画の入力形式は `skills/codex-build/references/plan-example.md` に定義済み
  （Context / Branch & PR / Guardrails / Test commands / Tasks T1..Tn）。
- 実行状態は `$GIT_DIR/codex-build/runs/<run-id>/`（run.md / tasks.md / interfaces.md / allowlists/）に永続化され、
  compaction・再起動後に再読込される（durable state が正本）。
- 主要レール（SKILL.md 明記）:
  - オーケストレーターは product code を書かない（例外は5行以下の些末修正のみ）
  - すべての `codex exec` に `< /dev/null` 必須
  - テストゲートはコミット前に必ず実行。赤ならコミット禁止
  - 1タスク=1コミット、1計画=1PR
  - 3回失敗で STOP して人間に返す（勝手に引き取らない）
  - MODEL/EFFORT は run 先頭で一度だけ解決（計画単位ピン）
  - AI 帰属表記（Co-Authored-By 等）は一切禁止

## 1. 結論

- **判定: MODIFY**（骨格は妥当、下記 CAO 指摘の7点を修正して採用）
- **推奨構成**: codex-build 無改造。同リポジトリに新規スキル `skills/fable/` を追加。
  Fable は前工程（Issue分析→計画→人間承認）と後工程（受入判定→報告）のみ担当。実行中は介入しない。

## 2. CAO（反証役）監査で確定した修正点

当初案に対して CAO エージェントによる反証レビューを実施。以下が確定修正:

1. **【最重大】push前承認ゲートの根拠が不成立**
   - SKILL.md の「ユーザー指示が計画に勝つ」レールの user は人間であり、Fable（peer agent）ではない。
   - チャット上の指示は compaction 後に消える。codex-build の Step 3 は push→PR を無条件に実行する手順。
   - → 対策: 承認ゲートを**計画ファイルの Guardrails に定型文として明記**する
     （計画は run.md にハッシュ付きで永続化されるため compaction 耐性あり）。
     グローバル CLAUDE.md の「push前に必ずdiff要約提示・承認」ルールと二重化。
2. **【重大】「3回失敗→Fable自動再計画」は codex-build の STOP レールと正面衝突**
   - 同一セッションでは同じ Claude が「STOPせよ」と「再計画せよ」を両方抱え、挙動が非決定的になる。
   - → 対策: STOP 後は必ず人間に返す。**再計画は人間の明示指示で開始する別ターン**に固定。
3. **【重大】再計画時に既存 run state（`current`）と衝突して停止する**
   - 途中失敗 run の `current` が生きたまま新計画を渡すと、codex-build は resume/new の判定で停止しうる。
   - → 対策: 再計画手順に run state 初期化（`current` の退避、新 run-id 採番、base の明示、部分コミットの扱い）を必須化。
4. **【中】1 Issue = 1 PR と「大Issueは複数計画に分割」は自己矛盾**（1計画=1PRのため）
   - → 不変条件を「**1 Issue = 1 計画 = 1 PR。割れる Issue は GitHub 上でサブIssueに分解してから**」に修正。
5. **【中】Fable の PR レビューは同一モデル（Claude）ゆえコード正誤の検出力を足さない**
   - → Fable の最終レビューは「Issue 受入条件の充足判定」に純化。
     コードの独立検証は既存の `codex exec review`（別ベンダーモデル第2パス）に寄せる。
6. **【中】実行判断に効く承認情報が codex-build の読まない場所に置かれる問題**
   - → push 可否等の承認フラグは計画ファイル経由で run.md（正本）に届くようにする。
     「二重保持しない」原則の唯一の例外。
7. **【中】層が増えるほど Claude が product code を直接編集する誘惑が増す**
   - → 「product code の変更は必ず codex exec 経由」を Fable 手順の不変条件として明記。

## 3. 役割分担（確定案）

| 工程 | Fable | codex-build | Codex | 人間 |
|---|---|---|---|---|
| Issue 分析・要件/完了条件/リスク整理 | ◎ | — | — | 確認 |
| 大Issue のサブIssue分解 | 提案 | — | — | ◎ 承認 |
| タスク分解・依存整理・計画作成 | ◎ | — | — | — |
| モデル/effort 決定 | 提案（計画に記載） | 計画通りピン | — | 高コスト時承認 |
| 計画承認 | 依頼提示 | — | — | ◎ 決定 |
| 実行（ブリーフ・スコープ検査・行レベルdiffレビュー・テストゲート・コミット） | 介入しない | ◎ | 実装のみ | — |
| 3回失敗時の停止・報告 | — | ◎ STOP | — | 把握 |
| 再計画の開始判断 | 再計画案作成 | — | — | ◎ 指示 |
| push・PR作成 | diff要約提示 | push直前で停止 | — | ◎ 承認 |
| PR 最終レビュー | ◎ 受入判定 | — | `codex exec review` | ◎ マージ |
| 知見の記録 | ◎ | 実行証跡 | — | — |

## 4. 推奨ワークフロー（11ステップ）

1. 人間が Issue を指定して起動（`/fable:run <issue番号>`）。`gh` が利用できない場合は Issue URL と本文も渡す
2. Fable は `gh` が利用できる場合は `gh issue view` で Issue を取得し、利用できない場合は人間から Issue URL と本文を必須入力として受け取る。`gh` はハード依存にしない。要件・完了条件・影響範囲・リスクを整理
3. リスク判定。高リスク領域（認証・課金・データ削除・秘密情報・外部公開）は人間へエスカレーション。
   大きすぎる Issue はサブIssue分解を提案し人間の承認を得る
4. 計画ファイル作成（plan-example.md 形式 + 拡張ヘッダー。Guardrails に「push/PR作成は人間承認後のみ」を明記）
5. validate_plan.py で計画の形式検査
6. 人間が計画を承認（承認記録を計画ファイルに追記 → run.md に永続化される）
7. codex-build スキル起動。タスクループは codex-build のレール通り。Fable は介入しない
8. 全タスク完了後、フルスイートゲート → push 直前で停止 → 人間に diff 要約提示 → 承認後 push・PR作成
9. 失敗時（STOP）: 人間が判断 → 再計画は人間の明示指示で開始（run state 退避手順込み）
10. Fable が Issue 受入チェックリストで PR 最終レビュー → 判定と根拠を提示 → 人間がマージ
11. 決定ログ・失敗知見を記録して完了

## 5. データ受け渡し契約

### Fable → codex-build（計画ファイル: plan-example.md 準拠 + 拡張）

必須: Issue リンク / Context / 受入条件（検証可能な Done 条件） / Branch & PR /
Guardrails（**push承認ゲート定型文を必ず含む**） / Test commands / Tasks（Files・Do・Depends on・Done when） /
モデル・effort / リスクレベルと根拠 / 承認記録（承認者・日時）
任意: ロールバック方針（fix-forward 前提の注記）

### codex-build → Fable（`$GIT_DIR/codex-build/runs/<run-id>/` が正本）

- run.md: 実行ステータス（completed / blocked）、PR URL
- tasks.md: タスクごとの状態・コミットハッシュ・テスト証跡・反復回数、allowlist 拡張と理由（逸脱記録）
- interfaces.md: 公開インターフェース台帳
- blocked 時: 停止タスク・diff・診断
- 完了報告: 積み残し・フォローアップ

## 6. 設計上の決定事項（質問項目への回答）

- モデル振り分け: **計画単位**（codex-build の設計に一致）。タスク単位は技術的には容易（各 codex exec が個別フラグを取る）だが、再現性・コスト管理の複雑化を理由に後回し
- 直列実行: **維持**。interfaces ledger・1ブランチ・スコープ検査がすべて直列前提
- 並列実行: MVP 外。必要になったら「複数 Issue の同時進行（別 worktree + 別計画 = 別PR）」で対応
- PR 粒度: **1 Issue = 1 計画 = 1 PR**。割れる Issue はサブIssue に分解してから
- エスカレーション責任: codex-build（3回失敗でSTOP）→ 人間（判断）→ Fable（人間の指示で再計画）
- 状態の正本: 実行状態 = codex-build（`$GIT_DIR/codex-build/`）、計画・承認・レビュー記録 = Fable 側。
  例外として push 承認フラグのみ計画ファイル経由で run.md に届ける
- 変更方針: **プラグイン/スキルとして拡張**（新規ファイルのみ追加、upstream 改造ゼロ）。
  触らないもの: `skills/codex-build/**`、`.claude-plugin/**`、`.codex-plugin/**`、`README.md`、`LICENSE`

## 7. 後回しにする機能

| 機能 | 理由 | 導入条件 |
|---|---|---|
| タスク単位モデル振り分け | 再現性・コスト管理の複雑化 | 計画単位運用で必要事例が3件以上 |
| 独立タスクの並列実行 | 直列前提の設計と衝突 | 直列でスループットが実際にボトルネック化 |
| 複数コーダー対応（Claude実装役等） | 「別モデル検証」の核前提が崩れる | 実装役と検査役が常に別ベンダーになる設計の確立 |
| Issue自動トリアージ・自動マージ・メトリクス | MVP 検証に不要 | MVP が5件以上の Issue を安定処理 |

## 8. 未確定事項（人間の判断待ち）

1. **セッション分離方針（解決済み）**: MVP は Fable と codex-build を同一セッション内でフェーズ分離して実行する。
   Fable が計画作成と人間承認を完了した後に codex-build へ制御を渡し、実行中は介入しない
2. 対象リポジトリと Issue のソース（このツール自体の開発用か、他プロジェクトか）
3. Codex CLI の契約・使用可能モデル・課金上限。デフォルトで pin するモデル
4. 高リスク判定の追加領域（note 公開コンテンツ等、環境固有のもの）
5. upstream 取り込み運用（`upstream` リモート + 定期 merge か、必要時のみか）

---

## 9. Codex への実装計画（設計確定後に codex-build で実行する）

> この計画は plan-example.md の形式に沿って清書し、人間の承認を得てから実行すること。

### 共通

- **Branch**: `codex/fable-bootstrap`（現ブランチ）/ PR target: `main`
- **Guardrails（全タスク共通の変更禁止）**:
  - `skills/codex-build/**`、`.claude-plugin/**`、`.codex-plugin/**`、`README.md`、`LICENSE`、`THIRD_PARTY_LICENSES.md` に触れない
  - push・PR作成は人間承認後のみ
  - AI 帰属表記なし
- **Test commands（ゲート）**: `python3 -m unittest discover -s skills/fable/tests -v`

### T1 — 計画スキーマ + バリデータ

- **目的**: Fable→codex-build の受け渡し契約を機械検証可能にする
- **変更対象**: `skills/fable/references/plan-template.md`、`skills/fable/scripts/validate_plan.py`、
  `skills/fable/tests/test_validate_plan.py`
- **変更禁止**: 共通 Guardrails の通り
- **依存**: なし
- **テスト**: unittest（必須フィールド欠落・ファイル未宣言タスク・テストコマンド欠落・承認ゲート文言欠落の各ケース）
- **完了条件**: plan-template.md が §5 の全必須フィールド（push承認ゲート定型文含む）を持ち、
  バリデータが正例 PASS・欠陥例 FAIL、テスト全 green

### T2 — Fable スキル本体

- **目的**: Issue分析→計画→承認→codex-build起動→受入判定→報告の手順書
- **変更対象**: `skills/fable/SKILL.md`、`skills/fable/references/escalation.md`、
  `skills/fable/references/result-contract.md`
- **変更禁止**: 共通 + `skills/fable/scripts/**`（T1 成果物）
- **依存**: T1
- **テスト**: unittest 回帰 + レビュー観点チェック（起動条件・承認ゲート・STOP後の順序固定・run state 退避手順の記載）
- **完了条件**: SKILL.md に §4 の全11ステップ、escalation.md に「STOP→人間→明示指示で再計画」の順序と
  run state 初期化手順（`current` 退避・新 run-id・base 明示）、
  「product code は必ず codex exec 経由」の不変条件が明記されている

### T3 — 起動コマンドと結線

- **目的**: `/fable:run <issue番号>` で §4 ステップ1〜6（Issue取得→計画→承認）を起動。
  `gh` が利用できない場合は、人間に Issue URL と本文を要求して続行する
- **変更対象**: `commands/fable.md`、`FABLE.md`（リポジトリ直下）
- **変更禁止**: 共通 + `skills/fable/**`（T1・T2 成果物）
- **依存**: T2
- **テスト**: unittest 回帰 + コマンド定義フロントマター検査（allowed-tools に Bash・Read・Write・AskUserQuestion）
- **完了条件**: fable.md が引数なし時に Issue 指定を要求、SKILL.md を正本参照（ループ再実装しない）、
  `gh` が利用できる場合は `gh issue view` を使用し、利用できない場合は人間に Issue URL と本文を要求して
  `gh` をハード依存にせず、FABLE.md にインストール（シンボリックリンク）と upstream 取り込み手順が記載

---

## 付記

- 本ファイルは `docs/` 配下の**未追跡ファイル**。codex-build の scope check は非ignore の未追跡ファイルで失敗するため、
  実行開始前に本ファイルをコミットするか、`.gitignore` に `docs/` を追加するか、各タスクの allowlist に含めること。
- CAO 監査の詳細（反証7項目と検証方法）は本資料 §2 に要約済み。
