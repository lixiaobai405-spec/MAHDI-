# MAHID 双版本与评分改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 完成1019的R1–R4/R10并保留既有完整版能力。
**Architecture:** 单份题库JSON；服务端评分与保存；不可变版本选择快照；浏览器展示权威结果。
**Tech Stack:** FastAPI, SQLite, Python, 单HTML/JavaScript。
**Spec:** ../specs/2026-10-26-mahid-lite-scoring-design.md

## Global Constraints
- 44题文本、选项、五类定义不变；lite10–20题默认12可配置。
- 新算法分数20–90；legacy_v1可切换；结果保存version/algorithm_version/generated_at。
- 30组对照≥70%；100条极差中位数≥25且强度三档齐；合成与真实样本证据分开。
- lite四块/3特征/1建议；full所有既有模块保留；升级同题不重复。
- 使用隔离数据库及测试账号；不改生产数据、不部署。

## Review Focus
- 稀疏题目系数不得产生NaN；非法答案/未知ID须拒绝。
- 模式/算法切换不得让进行中的测评与保存结果不一致。
- 相同提交重试不得生成重复结果；未保存不得展示为成功。
- 升级不得跨用户引用结果或重复询问已有题。
- 近分/PDF/历史记录/讲师列表不得各自给出矛盾类型。

## Task 1 评分与共享题库
Files: backend/assessment_bank.json, backend/assessment_config.json, backend/assessment.py, tests/test_assessment_scoring.py
Interfaces: load_bank(); get_config(); select_question_ids(config); score_answers(answers, version, config); classify_scores(scores, config).
- [x] 写配置/选题/旧算法/新标准化/强度/混合/非法输入失败测试。
- [x] 运行unittest确认失败。
- [x] 原样迁移题库并实现纯评分、结构化结论、完整辅助指标。
- [x] 测试通过；用100条/30组诊断验证数值门槛并保存可复现输出。

## Task 2 选择与保存API
Files: backend/storage.py, backend/app.py, tests/test_assessment_api.py
Interfaces: GET /api/assessment/config; POST /api/assessment/selections; POST /api/assessment/evaluate; GET /api/instructor/version-stats.
- [x] 写选择落库/快照/鉴权/继承/重试/不信任客户端评分的失败测试。
- [x] 运行确认失败；实现选择与结果权威逻辑。
- [x] API测试和原测试通过。

## Task 3 双版页面与PDF
Files: MAHDI五类人才模型测评工具(1).html, backend/pdf_export.py, tests/test_frontend_html.py, tests/test_pdf_export.py
- [x] 写lite四块、混合PDF、版本元信息和full模块保留测试。
- [x] 实现模式选择、稳定ID答案、服务端评分、lite结果、升级、full结论及统计展示。
- [x] 运行单元/API测试；检查JS语法并浏览器走两版及错误恢复。

## Task 4 验收与交付
Files: scripts/validate_assessment.py, docs/acceptance/2026-10-26-mahid.md, README.md
- [x] 支持真实答案JSON输入的30组/100条验收命令；固定种子合成诊断明确标记。
- [x] 隔离运行服务与浏览器，检查两版、升级、元信息、讲师统计、PDF、移动布局与计时。
- [x] 审查git diff及逐项需求，更新证据与剩余项，只在证据支持时宣告完成。

用户后续明确按等规模模拟数据验收；不要求本轮收集真人样本。证据和局限见 docs/acceptance/2026-10-26-mahid.md。
