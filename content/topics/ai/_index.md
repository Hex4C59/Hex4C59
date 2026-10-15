+++
title = "AI 与 Agent"
description = "理解 Agent 怎样围绕目标调用工具、维护状态，再动手实现，并沿源码追踪它的运行过程。"
date = 2026-10-15
weight = 10
topic_key = "ai"
topic_label = "机制 · 实战 · 源码分析"
topic_start = "/agent/what-is-agent/"
include_categories = ["ai"]
include_series = ["agent-engineering", "DeepSeek Harness", "智能体工程模式", "ai-papers"]

[[reading_routes]]
title = "先理解执行机制"
description = "从 Agent 与工作流的区别开始，再看模型怎样调用工具、保存上下文和分解目标。"
series = "agent-engineering"
pages = ["/agent/what-is-agent/", "/agent/react-paradigm/", "/agent/tool-use-core-of-agent/", "/agent/context-memory-state-management/", "/agent/planning-plan-and-execute/"]

[[reading_routes]]
title = "把机制接成可运行的程序"
description = "选择一个实战，把工具、外部服务、记忆和任务分工接到执行循环里。"
series = "agent-engineering"
pages = ["/agent/build-cli-coding-agent/", "/agent/build-mcp-agent/", "/agent/build-persistent-memory-agent/", "/agent/build-research-agent/", "/agent/build-multi-agent-code-review/"]

[[reading_routes]]
title = "沿着请求追踪真实源码"
description = "先认识 DeepSeek Harness 的职责，再沿请求链路进入应用入口、服务和插件运行时。"
series = "DeepSeek Harness"
pages = ["/agent/deepseek-harness-agent-engineering/", "/articles/deepseek-harness-request-lifecycle/", "/articles/deepseek-harness-source-map/", "/articles/deepseek-harness-cordis-context-services/"]

[[further_reading]]
ref = "/posts/practical_guide_to_major_LLM/"
reason = "比较模型、接入方式与实际选型条件。"

[[further_reading]]
ref = "/translations/demystifying-evals-for-ai-agents/"
reason = "从试验结果与执行记录理解 Agent 评测。"

[[further_reading]]
ref = "/translations/harness-design-long-running-apps/"
reason = "了解长期任务的运行环境怎样组织。"
+++
