+++
title = "软件设计与工程"
description = "用逐步变化的小程序比较抽象、契约与模块边界，再用测试、重构和持久化检查设计判断。"
date = 2026-10-15
weight = 20
topic_key = "software-design"
topic_label = "设计取舍 · 测试 · 重构"
topic_start = "/articles/software-design-00-reading-guide/"
include_series = ["software-design", "智能体工程模式"]
include_pages = ["/translations/optimize-code-performance-quickly/", "/translations/build-responsive-web-layouts/", "/translations/how-we-made-claude-ai-faster/"]

[[reading_routes]]
title = "先形成可检查的设计判断"
description = "沿着同一个待办程序，观察一层抽象、一个接口和一次模块划分怎样影响修改范围。"
series = "software-design"
pages = ["/articles/software-design-00-reading-guide/", "/articles/software-design-01-abstraction/", "/articles/software-design-02-contracts/", "/articles/software-design-04-module-boundaries/"]

[[reading_routes]]
title = "管理状态、失败与异步工作"
description = "明确谁能修改数据，操作失败后留下什么，以及等待怎样影响成功与错误的传递。"
series = "software-design"
pages = ["/articles/software-design-05-state-effects/", "/articles/software-design-06-async-errors/"]

[[reading_routes]]
title = "用行为检查支持后续演化"
description = "从约定推导测试，在重构中保持行为，再把数据保存、重新读取和格式迁移接起来。"
series = "software-design"
pages = ["/articles/software-design-07-testability/", "/articles/software-design-08-refactoring/", "/articles/software-design-09-persistence/"]

[[further_reading]]
ref = "/translations/optimize-code-performance-quickly/"
reason = "从分析与测量进入性能优化。"

[[further_reading]]
ref = "/translations/how-we-made-claude-ai-faster/"
reason = "观察真实应用怎样建立基准并防止性能回退。"
+++
