# DeepSeek Harness series guide

本文件只适用于 `series = ["DeepSeek Harness"]` 的文章。它补充 Agent section 和通用技术写作规则，不替代 [archetypes/agent.md](../../archetypes/agent.md) 或 [technical-writing.md](technical-writing.md)。

## Scope and purpose

- 专栏用于解释 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 的架构、运行机制、扩展方式和工程取舍。
- 文章应帮助读者形成可验证的理解，不要把项目 README 改写成宣传文案。
- 使用 `content/agent/<slug>/index.md` 存放文章，并通过唯一的 `series_order` 归入专栏。

## Versioned facts

- 介绍项目当前行为时记录被测试的仓库版本或 commit、操作系统、运行时、依赖、模型和关键配置。
- 不要把未经验证的主分支行为写成稳定事实；开发预览、破坏性兼容变化和未验证能力要明确标注。
- 涉及性能、成本、延迟、准确率或模型能力的结论必须给出版本、环境、输入、方法、样本或数据集和结果。没有实测时明确写出未测量。

## Sources and boundaries

- 引用源码、架构和配置时链接到 DeepSeek Harness 的原始仓库、固定 commit、具体文档或代码位置。
- 不要复制一份会快速过期的包清单或 API 清单；需要列举时说明它对应的版本和用途。
- 明确区分仓库事实、实验测量、设计理由和作者判断。不要把文章的归纳名称写成 DeepSeek Harness 的官方术语。
- 代码示例通过真实项目入口验证，并记录依赖、命令、预期输出和已知失败条件；示例不得包含凭据、个人信息或私有路径。
