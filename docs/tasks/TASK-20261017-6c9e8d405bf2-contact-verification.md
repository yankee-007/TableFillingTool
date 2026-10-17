# 联系人验证与画像式筛选

- Identity: TASK-20261017-6c9e8d405bf2；状态 done（实现及自动检查完成，真实企微指定联系人验收另列）；2026-10-17 Asia/Shanghai。
- Requirement: 只读参考 StudentManagement 画像验证/筛选。验证可指定搜索及可选结果字段、前缀默认空、完整/包含匹配默认包含；表头多选/条件筛选、冻结结果、过期提示和连续选择。仅确认成功写“是”，其余保留原值；不发消息、不改备注。
- Baseline: main `4d71d4b97362ee04a0d4c6e99bb5c195b6dcf39c`；起点干净，main 尚有上一任务未推送提交。
- Workspace: Git 注册 worktree contact-verification，分支 `task/TASK-20261017-6c9e8d405bf2-contact-verification`；单写入者，完成后串行 squash 到 main。用户后续明确要求完成后推送，沿用已确认 origin/main，包含上一 UI 任务尚未推送成果；无任务依赖。
- Findings: 参考 profile_wechat.py、ProfileFilterDialog.qml、profile_module.py、table_query.py 及 ADR-007；源项目只读，不访问真实数据、不执行源模块。查询冻结只影响显示，批量验证排除过期行，零匹配不回退全表。当前导出仍明确包含全部行。
- Snapshot: 已实现表头选项/条件筛选、自然排序、冻结/过期提示、连续选择、按真实匹配集批量验证及暂停/继续/结束。用户已确认分别指定搜索字段与可选结果字段。结果仅成功写“是”，原值变化/删除防覆盖；默认空前缀、包含匹配，同表同字段结构保留本轮日志。README、上下文、架构和 UI 说明已更新。任务代码提交 `8a14f65f8039ea4ad69c2342b56db60aa52f4362`；已串行整理至干净 main，最终代码/测试/预览内容与该通过检查的版本一致，仅收尾 Task/活动索引。
- Verification: Windows/Python 3.14.7、PySide6 6.11.2、openpyxl 3.1.5；临时 SQLite/模拟企微 63 项回归通过且 Python 正常退出，覆盖原 43 项以及组合/空值筛选、筛选范围、排序身份、暂停/停止、剪贴板恢复及用户复制保护、匹配模式、字段校验、并发原值变化、磁盘失败与 F11 冲突。`python -m compileall -q app main.py tools tests` 与 `git diff --check` 通过，无新增运行依赖。Qt 离屏渲染并查看新验证框 800×650 / 680×560、选项/条件框 410×560、980×620 过期筛选状态；原主表/浮窗预览保持。新增测试初次断言通过但退出时因 Qt 测试对象清理顺序异常，补齐剪贴板与对象销毁后正常退出；未将该次当成功证据。源 app/qml 125 个 Python/QML 文件与本次读取基线 SHA-256 一致。真实企微兼容性仍需用户指定联系人验收，本轮未对真实联系人执行自动化。
- Recovery: 按上述分支及 Git worktree 关系恢复，依赖和启动见 README；禁止改动 StudentManagement。
- Closure: 按项目策略 squash 集成到 main，通过提交正文 `Task: TASK-20261017-6c9e8d405bf2` 可定位成果；活动索引移除本任务。用户已授权完成后推送 origin/main（含此前 UI 优化）；实际同步结果以 Git 查询及交付报告为准。忽略的虚构截图保存至主目录 `artifacts/contact-verification/`，任务 worktree 在集成后可归档以恢复内部历史；不删除未知工作区。
