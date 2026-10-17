# 初始化核验记录

核验日期：2026-10-17（Asia/Shanghai）。此文件仅供本次初始化追溯，不是日常 Session 的必读依赖，也不是业务 Task 或 ADR。

## 来源、基线与范围

- 工具包：Agent Project Bootstrap v0.5.0，仓库 `yankee-007/AgentBootstrapPrompt`，包路径 `agent-project-bootstrap/`。
- 原始 ref `main` 先经 `git ls-remote` 解析为完整 commit `6a4b1bffeb28c0ce3b880eb752ca9414683c100c`，随后重新读取[该提交入口](https://github.com/yankee-007/AgentBootstrapPrompt/blob/6a4b1bffeb28c0ce3b880eb752ca9414683c100c/agent-project-bootstrap/BOOTSTRAP.md)。协议及模板从同 SHA 的完整下载缓存读取；入口清单全部文件存在，按需读取，未读取未启用的观测模板正文。
- 目标为当前 TableFillingTool 项目目录，初始化前为空，不属于祖先 Git 仓库，无其他 VCS、适用祖先 AGENTS.md、已有规范或未提交修改。根目录不是符号链接/重解析点。此前中断没有留下项目文件。
- 本次仅新建治理文档和本地 Git；没有业务代码、依赖安装、业务命令、自动化服务、Task、ADR 或观测记录。没有真实技术栈依据，不添加猜测性的 `.gitignore`。用户随后提供 GitHub `yankee-007/TableFillingTool` 及 main 的 remote/push 指令，本次按该授权配置 origin、提交全部当前治理文档并同步 main；不重复追加 README 标题，不重建已有仓库或重命名其他分支。提交/同步最终结果单独报告。
- 新建文件：根目录 `AGENTS.md`、`PROJECT_CONTEXT.md`、`README.md`；`docs/architecture.md`；`docs/agent/` 下 `policy.md`、`workflow.md`、`git.md`、本记录；`docs/tasks/README.md`、`docs/decisions/README.md`。无既有文件需要复用或修改。

## 最低语义逐项核对

下表路径均相对于项目根；结论是已核对生成文档中的规则覆盖，不表示未来业务流程已经实际执行。

| 语义 | 实际目标文件 / 章节 | 结果 |
| --- | --- | --- |
| 入口与职责 | `AGENTS.md`；`PROJECT_CONTEXT.md`；`docs/agent/policy.md` 的“文档路径映射” | 入口短、路径明确、按需读取，长期规则在项目内自包含 |
| 策略条件 | `docs/agent/policy.md` 的“有效策略”和条件表；`workflow.md` 的“Session 与任务开始”；任务索引 | always/adaptive/disabled、提交与恢复禁令优先级、远端禁用与交接限制保留且一致 |
| 任务身份与状态 | `docs/agent/workflow.md` 的“标识、状态与最小记录” | 沿用 ID；日期加 12 位随机十六进制并查冲突；六种状态、时区、阻碍单列 |
| 任务最小记录 | `docs/agent/workflow.md` 的“标识、状态与最小记录”字段表 | 需求、范围、完成标准、修改边界、依赖、快照、验证缺口、恢复与结果限制齐全；不造真实 Task |
| 工作区保护 | `AGENTS.md`；`docs/agent/git.md` 的“基线与修改归属” | 核对真实文件和 Git、保护用户内容、混合归属不自动提交、单写入者；明确快照请求另按范围处理 |
| 任务隔离与集成 | `docs/agent/git.md` 的“任务分支与工作区”“串行集成与主线历史”“清理与恢复”；策略的分支约定 | 默认 task-worktree；补充/接力复用；main 串行 squash；保留初始化例外、依赖与内部历史边界 |
| 最小执行路径 | `docs/agent/workflow.md` 的“最小必要执行路径”；`git.md` 的“任务分支与工作区” | 修改前有限只读侦察、复用任务/环境/未变规则；轻量不豁免隔离，共享写入须明确许可 |
| 风险升级与针对性验证 | `docs/agent/workflow.md` 的“风险变化与升级”“验证与人工接受”；`git.md` 的集成章节 | 风险按实际影响；跟踪/隔离/检查分别调整；迁移前保存停写核对；最终内容必核对，证据变化后相关重验 |
| 按需观测 | `docs/agent/workflow.md` 的“执行耗时观测（按需）”；策略依据 | 默认关闭、不造空报告；显式采样时记录版本/环境、耗时、等待/重叠/未知、观测成本与质量结果，不自动上传或改变隔离 |
| 多工作区备份 | `docs/agent/git.md` 的“按请求保存项目快照”；策略的多 worktree 段落 | 协调写入者保存任务快照，按授权 refs 上传；未完成任务不为备份合入 main，分别说明覆盖 |
| Git 与敏感边界 | `docs/agent/git.md` 的“Commit 与恢复”“Secret 与上传范围”“Push”；策略条件表 | 按策略写入；推送请求保存整个当前项目；保留目标/分支/凭据检查，不伪造身份、不绕 hook、不擅自强推 |
| 恢复与落盘 | `docs/agent/workflow.md` 的“Session 与任务开始”“关键阶段与 checkpoint” | 重要修改前恢复摘要、核对快照偏差；启用跟踪时保存阶段快照，不承诺崩溃前收尾 |
| 验证与事实 | `PROJECT_CONTEXT.md` 的“事实边界”；`docs/agent/workflow.md` 的“验证与人工接受” | 事实/未知分开，证据绑定内容和环境；未运行不写通过、旧证据不自动延续 |
| 交付与授权 | `docs/agent/policy.md` 的“策略依据与操作范围”；`workflow.md` 的 checkpoint、交接章节；`git.md` 的 Push 章节 | 文档保存/本地快照/跨电脑取得分开；授权限定目标、分支、内容、阶段与副作用，不自行延伸 |
| 生命周期与维护 | `docs/agent/workflow.md` 的“文档维护与完成”；`docs/tasks/README.md`；`docs/decisions/README.md` | done 以完成标准判断；先更新 Task、再移除活动行、核对 ID 和原路径，仅更新受影响文档，不造历史 |

## 检查结论与限制

最低语义已逐项对照；入口、workflow、Git 与任务索引均采用同一有效策略。入口、workflow、Git 的规范正文与固定版本模板逐字核对保留；策略按真实项目填实，未扩大远端权限。后续独立任务在初始化提交形成基线后使用 task-worktree，本次不启动该流程。

本次文档检查包括：所有生成文件清单、相对 Markdown 链接可解析、适配占位符清除、入口规模、规范正文保留、规则一致性、路径范围、无既有内容覆盖、无业务变更、必要敏感内容检查及 Git 差异格式。没有业务代码，未运行业务测试、构建、UI 或生产验收；这些结果不被描述为通过。来源链接仅作追溯，日常工作无需读取工具包、临时缓存或私有 Session。

## 有效策略与后续启动

有效策略：detect-and-init、ask-once、adaptive、task-worktree、verified-owned-units、on-handoff、on-request、criteria-based、squash-on-completion；完整配置及优先级见 `policy.md`。远端目标已确认为 GitHub `yankee-007/TableFillingTool`、允许分支 main，本次初始化上传已获明确授权；目标读取成功且未返回已有 refs，本次内容无 CI/发布配置，外部集成副作用未知。产品需求、技术栈、业务运行/验证环境待后续任务确定，均不阻碍本次文档初始化。

后续从根目录 `AGENTS.md` 进入，再读 `PROJECT_CONTEXT.md`、`docs/agent/policy.md`；无 Task ID 时读任务索引，有 ID 时直接定位真实任务。修改、Git 写入及交接按阶段补读对应协议。不能证实自动加载本项目 AGENTS.md 的 Agent 或工具，须由使用者显式要求读取该入口。不因更换 Session 或电脑重跑初始化。

本地提交与远端同步以实际 Git 查询及本次最终交付报告为准；本地文件或 commit 不代表其他电脑已经取得。初始化完成后停止。

## 常规启动文本规模

以下为本次生成版本的 UTF-8 文件字节数及字符数，不是 token 数；不要求后续每次 Session 重测。实际 Task ID 已知时用对应任务替代索引；workflow/Git 按阶段补读。

| 文件 | UTF-8 字节数 | 字符数 |
| --- | --- | --- |
| `AGENTS.md` | 2327 | 945 |
| `PROJECT_CONTEXT.md` | 2677 | 1201 |
| `docs/agent/policy.md` | 12789 | 6051 |
| `docs/tasks/README.md` | 1414 | 626 |
| 合计 | 19207 | 8823 |
