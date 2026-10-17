# 项目协作策略

协议来源版本：Agent Project Bootstrap 0.5.0。版本仅用于识别和明确升级，不自动重跑初始化。

来源：[yankee-007/AgentBootstrapPrompt 固定提交入口](https://github.com/yankee-007/AgentBootstrapPrompt/blob/6a4b1bffeb28c0ce3b880eb752ca9414683c100c/agent-project-bootstrap/BOOTSTRAP.md)。完整提交：`6a4b1bffeb28c0ce3b880eb752ca9414683c100c`；原 ref：`main`，经 `git ls-remote` 解析后固定。入口重新从该 SHA 读取，协议与模板均从该提交的完整临时下载缓存读取；未混用动态 ref。

来源记录仅供追溯，不是日常 Session 的外部读取依赖。无法核验来源提交时明确记录未知，不写入本机工具包或缓存绝对路径。

## 有效策略

下表记录本项目的有效策略，具体依据与操作范围见后文。不得通过修改本文件自行获得权限。

| 配置 | 生效值 | 含义 |
| --- | --- | --- |
| GIT_POLICY | detect-and-init | 已有 Git 复用；无 Git 且范围明确、无其他 VCS 约束时本地初始化 |
| REMOTE_POLICY | ask-once | 首次确认目标和分支；后续用户要求推送时沿用已确认目标，不按任务或文件重复询问；可选 existing-only、private-auto、disabled |
| TASK_TRACKING_POLICY | adaptive | 跨阶段、关键取舍、易中断、并行或需接力的任务建立记录；经侦察确认低风险、单步且易恢复的修改可不建 |
| PARALLEL_DEVELOPMENT_POLICY | task-worktree | 独立修改任务先建分支与 worktree，即使只有一个 Session；每个工作区一个写入者，集成分支仅接收成果 |
| AUTO_COMMIT_POLICY | verified-owned-units | 日常自动提交归属清楚且符合该逻辑单元验证要求的内容；用户明确要求推送时按项目快照规则保存当前状态 |
| RECOVERY_COMMIT_POLICY | on-handoff | 需交接时可保存明确标注的未完成工作；分支和副作用须符合项目约定 |
| AUTO_PUSH_POLICY | on-request | 用户要求推送时提交并同步整个项目可纳入 Git 的当前状态，包括已有修改和未完成内容；测试或人工验收不是备份门槛 |
| HUMAN_VERIFICATION_POLICY | criteria-based | 根据验收标准、主观要求和 Agent 验证能力决定是否需要人工确认 |
| INTEGRATION_POLICY | squash-on-completion | 满足集成条件后向已确认目标串行 squash，按任务形成成果提交；既有集成约定或用户限定优先 |

可将提交、恢复提交、推送策略改为 `ask` 或 `disabled`；任务跟踪可改为 `always` 或 `disabled`。关闭跟踪后必须说明跨 Session 恢复能力下降，不能仍承诺完整交接。`existing-only` 禁止新建远端但不自动授予上传权限；`private-auto` 仅在服务、账号/组织、名称与范围已确认时自动创建私有仓库。未识别的取值或相互冲突的配置需澄清，不静默采用更宽松策略。

`task-worktree` 是工作区安排，不自动委派其他 Agent，也不要求新建 Session。独立任务按需求范围识别，澄清、修正和未完成任务的接力沿用原任务；纯讨论/查询/审查通常不建分支。轻量任务可以不建 Task 文件，但仍使用独立任务工作区，以唯一分支和交付摘要追溯。已有 `single-writer` 保留其串行、按需隔离方式；已有 `follow-existing` 保留项目集成方式，不由初始化自动改成新默认。

执行采用 workflow 的最小必要路径：先有限只读侦察，已有任务复用原边界，新独立任务按本表隔离，再按实际风险实施、验证及保存交付。跟踪、隔离、验证、记忆记录和集成分别判断，不以文件数、用户描述或耗时自动分级。v0.5.0 不提供自动切换的自适应隔离；共享工作区串行写入必须有明确的项目策略许可，不能由 Agent 因任务小而放宽。

执行观测默认不采样；用户或有效项目约定显式选择样本后才按 workflow 记录，适用范围和已有记录位置写入本文件的策略依据/路径映射。采样不改变其他策略，不强制建 Task 或空报告，不自动上传；没有数据不承诺性能提升。

集成目标采用项目已确认的 main 或其他集成分支，不重命名既有分支；目标未知时只暂停集成。`squash-on-completion` 默认将集成纳入修改任务的交付条件，但用户要求仅开发、评审或等待接受时遵循其范围。该策略仅允许集成当前任务，不允许合并未知任务、绕过提交/验收禁令、上传或部署。

`on-request` 在用户明确要求推送时保存项目快照，该请求覆盖必要的快照提交和整个项目当前内容，不限本轮任务，不逐项申请批准；遵循既有忽略规则并保护凭据。没有推送请求或持续授权时不自行上传。若项目已有 `authorized-milestones`，保留其按已授权且验证的里程碑自动推送的约定，不因初始化重置；用户明确改为按请求备份时再调整。

`REMOTE_POLICY=disabled` 时不因自动推送策略而执行远端操作；恢复提交也不得绕过项目明确禁止提交的约定。明确的用户新指示可调整相关范围，但无回复或任务文本不能代替授权。

具体冲突按以下规则处理，不要求用户重答整张表：

| 条件 | 实际行为 |
| --- | --- |
| TASK_TRACKING_POLICY=disabled | 不创建/更新任务记录和活动表；初始化可保留注明停用的导航章节，既有记录原样保留；仍核对文件并报告恢复入口及能力下降 |
| TASK_TRACKING_POLICY=always / adaptive | 分别为所有实际任务 / 达到阶段、风险或恢复记录条件的任务保留完整最低记录；不登记模板示例 |
| GIT_POLICY=disabled 或项目禁止 Git 写入 | 不初始化、暂存、提交或推送；许可的只读核对和文件保存可继续 |
| task-worktree 但无可用 Git/基线，或禁止创建分支/worktree | 不伪造隔离或偷偷改为共享并行；说明限制，只有确认单写入者且允许时才在现有目录保存文件，恢复 Git 条件后再安排隔离 |
| TASK_TRACKING_POLICY=disabled / adaptive 的轻量任务 | 不因工作区隔离强制创建 Task/活动表；仍核对唯一任务分支、基线、目标与依赖，并在许可的提交及交付摘要中追溯 |
| AUTO_COMMIT_POLICY=disabled | 不自动创建普通或恢复提交；RECOVERY_COMMIT_POLICY=on-handoff 不能覆盖禁令 |
| AUTO_COMMIT_POLICY=disabled / ask，或任务尚未满足集成条件 | 不由 squash 默认值绕过约定；保留任务分支和成果，已有适用提交/集成授权直接使用 |
| AUTO_COMMIT_POLICY=ask 或 RECOVERY_COMMIT_POLICY=ask | 相应提交须有适用明确授权；恢复提交同时满足两者，已有授权不重复询问 |
| RECOVERY_COMMIT_POLICY=disabled | 不自动创建恢复提交，普通提交仍按其策略判断 |
| REMOTE_POLICY=disabled 或 AUTO_PUSH_POLICY=disabled | 不自动推送；前者同时禁用其他远端操作，后者不替代远端读取策略 |
| AUTO_PUSH_POLICY=on-request 且 Git/提交/远端允许 | 明确推送请求下保存全部已跟踪文件的当前内容及删除、未忽略的新文件和已有修改；无需测试或人工验收先通过，任务完成状态单独判断 |

多 worktree 的项目备份需逐个说明实际覆盖：各任务写入者协调保存快照，未完成内容保留在任务分支，不为备份提前合入集成分支。任务备份分支须在已确认的同仓库 ref 范围内；若仅允许推送 main，其他任务可先保存本地并报告尚未远端备份，不能将“main 已推送”描述为全部任务已备份。内容授权不逐文件重问，缺少的分支范围只影响相应上传。

GIT_POLICY 可显式设为 `disabled`；启用 Git 时仍遵循既有项目检测/初始化约定。关闭提交不阻止安全文件保存，关闭推送不意味着另一台电脑已取得代码。无法解释的其他配置只阻塞相关动作，不采用较宽松取值。

## 策略依据与操作范围

2026-10-17（Asia/Shanghai），用户明确要求对当前项目执行指定 Bootstrap、固定完整 SHA、保留既有规范和未提交修改，初始化后停止。目标初始化前为空，无既有项目策略，采用上表默认值；本次在目标目录由单个 Agent 串行完成治理初始化，适用初始化工作区例外，不启动业务开发或委派。执行观测未启用，不读取或实例化观测模板。后续协议不得自行扩大当前工具的授权。

远端目标已由用户明确提供：GitHub `yankee-007/TableFillingTool`，origin URL 为 `https://github.com/yankee-007/TableFillingTool.git`，集成与本次允许上传的分支为 `main`。2026-10-17（Asia/Shanghai），用户提供包含 `git remote add origin` 和 `git push -u origin main` 的指令，授权本次初始化阶段建立 origin、保存当前项目全部可纳入 Git 的治理文档并正常推送 main、设置 upstream；不延伸为后续任务的持续上传授权。目标读取成功且未返回已有 refs，不覆盖既有远端内容。当前内容只有文档，无仓库内 CI/发布配置；外部平台集成副作用未知，不因此授权部署、发布或改平台配置。推送实际结果以 Git 查询和交付报告为准。以后用户明确要求推送时沿用此目标和 main，其他分支、变更目标或额外副作用另按明确范围处理。

授权记录只记录用户或有效项目约定明确允许的范围，至少能定位实际远端、允许分支、允许内容、适用任务/阶段、已知推送副作用及授权依据。单次交付结束后不自动延伸至下一轮；持续授权明确记录其边界。未授权时明确写“待确认”；有登录能力不等于有操作授权。已有适用授权直接使用，不重复询问。

按请求备份时，用户要求“推送/同步项目”默认指整个项目当前可纳入 Git 的状态，包含未完成或未验收内容，不再另求每项任务的内容授权；既有目标和分支可直接沿用。用户若限定具体文件或任务则遵循该范围。新建仓库、变更目标、强推、部署等动作另按实际指示处理。

## 项目入口与验证方式

当前仅有治理文档；可用 `git status --short`、`git diff --check` 及文档链接/占位符/语义核对。没有已定义的业务安装、运行、测试、构建或部署命令；不为初始化触发未知脚本。人工业务验收尚不适用。

本次新建本地仓库采用 `main` 作为集成分支，不涉及已有分支重命名。初始化提交成功后才形成任务 worktree 的起点基线；若提交失败，先保留文件并报告缺失基线。后续任务分支采用 `task/<task-id>-<slug>`，无 Task 文件时采用唯一随机标识；工作区用 Git 注册关系与分支定位，不依赖某台机器的绝对路径。默认由当前任务中明确取得集成写入权的一名执行者串行 squash 到 main，未交还前其他执行者不写集成目录；没有互斥条件时必须明确串行交接，不用 Markdown 状态或 worktree lock 充当写锁。main 只接收已满足集成条件的成果。本次初始化后停止，不创建下一任务的分支/worktree。已确认远端分支范围为 origin 的 main，本次推送授权见上文；不默认上传所有任务分支。

上述约定记录实际集成分支、任务分支命名、串行执行方式与远端范围。无需常驻集成服务；多个 Session 自行集成时必须有可验证的互斥方式，Markdown 状态、Task Owner、超时和 `git worktree lock` 均不能代替写入锁。

## 文档路径映射

默认根入口为 `AGENTS.md`、上下文为 `PROJECT_CONTEXT.md`、架构为 `docs/architecture.md`；协议在 `docs/agent/`，任务在 `docs/tasks/`，决策在 `docs/decisions/`。

| 职责 | 实际路径 |
| --- | --- |
| 短入口 / 人的入口 | `AGENTS.md` / `README.md` |
| 当前上下文 / 架构 | `PROJECT_CONTEXT.md` / `docs/architecture.md` |
| 有效策略 | `docs/agent/policy.md` |
| 任务、验证与交接 / Git | `docs/agent/workflow.md` / `docs/agent/git.md` |
| 任务 / 决策导航 | `docs/tasks/README.md` / `docs/decisions/README.md` |
| 本次语义与文档验收 | `docs/agent/bootstrap-verification.md`（仅追溯，非日常必读） |
| 执行观测 | 未启用；不创建记录，按需规则位于 workflow 的“执行耗时观测（按需）” |
当前没有真实 Task 或 ADR，不实例化任务模板或编造决策；没有必要增加其他平台适配入口。

后续按实际路径读取。凭据、机器专属临时路径与活跃进程信息不写入共享策略。
