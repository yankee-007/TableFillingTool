# 项目上下文：TableFillingTool

## 目标与当前阶段

Windows 本地表格填写工具，参考用户的 StudentManagement 代码，将联系人打开、聊天跟随填写独立出来。已实现 XLSX/CSV 导入导出、可编辑表格、独立本地保存和置顶跟随浮窗；不包含学习平台采集、学员库或群发。真实企业微信版本的操作兼容性仍待用户以指定测试联系人验收。

## 技术形态与核心能力

Python 3.10+、PySide6 Qt Widgets、SQLite 与 openpyxl；Windows 企微适配使用 ctypes 调用 Win32 API，无 pywin32/PyAutoGUI 运行依赖。启动为 `python main.py` 或 `start.bat`，依赖见 `requirements.txt`。本次验证为 Python 3.14.7、PySide6 6.11.2、openpyxl 3.1.5。

## 核心模块与入口

- `main.py`：专用应用身份、数据目录与单实例锁、窗口入口。
- `app/data.py`、`app/service.py`：表/记录/字段稳定身份、SQLite 事务与共享保存路径。
- `app/files.py`：只读导入、另存导出、文本/编码/容量边界。
- `app/ui.py`、`app/models.py`：主表、字段填写、联系人设置、浮窗与异步文件操作。
- `app/matching.py`、`app/wecom.py`：备注/前缀/唯一姓名匹配，企微进程识别及只打开联系人。
- `tests/`：临时数据与模拟窗口回归；`tools/render_preview.py`：虚构数据布局渲染。
- `AGENTS.md`、`docs/agent/`、任务/决策索引：协作入口与后续工作规则。

当前结构详见 [架构](docs/architecture.md)。这里只保留导航与摘要。

## 业务规则、持久化与长期约束

StudentManagement 为只读参考，禁止修改、启动其应用/数据库或在其中执行会写文件的命令；不读取真实用户数据，不将其作为运行时依赖。新工具使用自己的 Qt AppLocalDataLocation 下的 `tables.sqlite3`，也支持 `--data-dir`。Excel/CSV 仅导入值表，原文件不被自动修改；导出不保留原样式/宏/公式计算，CSV 公式前缀转义。当前表导出包含全部行、按原始顺序，不受显示筛选影响。

主表和浮窗以表/记录/字段 ID 保存，浮窗独立于主表选择；切换和关闭前保存失败时保留输入并阻止切换。多条同名/同备注不自动选人。企微只搜索/打开，不发送、不改备注；检查进程、前台窗口、查询剪贴板及标题。共享记忆不得包含真实数据和凭据。远端 `yankee-007/TableFillingTool`、集成分支 main 已确认；初始化授权不延伸为本次功能的自动推送授权。

## 已知问题与易回归区域

真实企业微信需 Windows 客户端、一个主窗口及默认 Ctrl+F/Ctrl+O/Ctrl+W 快捷键，当前回归为模拟窗口，未实测真实联系人。Windows 画面抓取服务超时，布局改由 Qt 渲染检查；原生应用启动/事件循环已验证。导入上限 50 MB、每张表 50,000 行/200 列/单元格 32,000 字；不是原格式 Excel 编辑器。主表排序/搜索与编辑身份、输入法和保存失败、跨聊天切换是重点回归区域。

具体任务进度见 [任务索引](docs/tasks/README.md)，长期决策理由见 [决策索引](docs/decisions/README.md)。已解决问题不持续堆积在本文件。

## 开发与验证入口

首次环境准备：`python -m pip install -r requirements.txt`；日常启动：`python main.py`。测试：设置 `QT_QPA_PLATFORM=offscreen` 后运行 `python -m unittest discover -s tests -v`。布局检查：`python tools/render_preview.py`，仅产生虚构数据截图到忽略的 `artifacts/preview/`。检查语法：`python -m compileall -q app main.py tools tests`；差异检查：`git diff --check`。这些命令不得在 StudentManagement 中执行。尚无发布/部署流水线或打包可执行文件。

## 事实边界

2026-10-17（Asia/Shanghai）基于当前代码、临时数据的 35 项回归及布局渲染核验。只读参考源项目 app/qml 共 124 个 Python/QML 文件，结束复核与读取前 SHA-256 全部一致；未运行源项目应用/测试/数据库。原生入口以临时独立数据目录启动并正常退出；真实企微消息/联系人未被自动化验证。代码与数据保存在何处、是否提交/推送分别以实际 Git 与目录为准，不把模拟结果称为实机验收。

本文描述当前检出版本的已知情况，不自动代表其他分支或生产部署。修改相关行为时检查本文是否需更新；不要仅刷新日期。
