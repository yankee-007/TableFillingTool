# TableFillingTool

当前为空项目，仅建立了项目记忆与协作基线。项目名称为 TableFillingTool；具体产品目标、用户场景和功能范围尚未确认，不根据名称推定需求。本次仅初始化，不开展业务开发。

## 使用与开发

目前没有安装、启动、测试、构建或部署命令，不安装依赖或虚构验证命令。当前仅可核对 Markdown 链接、占位符、规则一致性、文档影响与 Git 差异（`git diff --check`、`git status --short`）。后续确定技术栈后仅补充实际可用的入口及其副作用。

## 项目记忆与协作

- [Agent 工作入口](AGENTS.md)
- [当前项目上下文](PROJECT_CONTEXT.md)
- [当前架构](docs/architecture.md)
- [活动任务](docs/tasks/README.md)
- [设计决策](docs/decisions/README.md)

后续 Agent 从项目入口恢复工作；不自动读取入口的工具需显式要求读取。更换 Session 或电脑无需重新初始化项目记忆，仍需取得代码及配置必要环境。

后续修改按项目有效策略执行：默认独立任务先建分支和 worktree，补充消息沿用原任务；main 或既有集成分支仅接收成果，由一个执行者串行集成，默认 squash。初始化完成后停止，不自动开始下一任务或启动其他 Agent。
