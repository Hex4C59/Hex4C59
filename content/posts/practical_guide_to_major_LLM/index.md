+++
title = "主流大语言模型全景指南：比较与实战选型（2026 年 10 月更新）"
date = 2025-09-28T12:21:41+08:00
lastmod = 2026-10-14T00:00:00+08:00
draft = false
author = "Hex4C59"
description = "截至 2026 年 10 月 14 日，比较 GPT-6、Claude 5.5、Gemini 4 Argon、Grok 4.7 及 DeepSeek、Qwen、Kimi、GLM 等主流模型，说明 API 成本、部署限制与实际选型方法。"
summary = "从聊天产品、API 和开放权重三个层面梳理 12 家主要厂商，结合最新型号、官方定价与真实任务评估方法，选择适合自己的模型。"
tags = ["LLM", "模型选型"]
categories = ["ai"]
ShowToc = true
source_kind = "original"
article_type = "review"
+++

如果你准备订阅一个 AI 助手，或者给自己的应用接入大语言模型（Large Language Model，LLM），先确定它要完成什么任务，再比较型号。同样是“写代码”，解释一个函数、修改现有仓库和连续操作终端，对模型和工具的要求差别很大。

截至 **2026 年 10 月 14 日**，OpenAI 的公开模型指南已经转向 GPT-6 系列；Claude 的公开产品线包含 Fable 5.1 和 Opus、Sonnet、Haiku 5.5；Google 已提供 Gemini 4 Argon；Grok 当前主推 4.7。[^openai-guide][^claude-models][^gemini-models][^grok]

国内模型也已经推进到 DeepSeek V4.1 Flash、Qwen3.8、Kimi K3 和 GLM-5.3 等型号。[^deepseek-updates][^qwen-models][^kimi][^glm]

对普通用户和应用开发者而言，值得比较的是：任务能否完成、结果是否可核对、需要多少人工返工，以及完成一次任务实际花了多少钱。本文的候选建议是基于公开规格和产品定位的判断，**没有经过同一环境下的横向实测**；厂商发布的能力与成绩也不能直接当作你的业务结果。

> 型号、价格和开放状态的核对截止日期为 2026 年 10 月 14 日。预览版本、促销价格和后续发布计划会单独标明；使用前仍应检查文末对应的官方页面。

## 1. 先按任务缩小候选范围

如果让我从头选，我会先用下面这组候选做小规模试用。表中的顺序不表示排名。

| 主要任务 | 我会先试的候选 | 决定是否留下它的指标 |
| --- | --- | --- |
| 日常写作、资料整理、办公 | ChatGPT、Claude、Gemini；中文产品可比较豆包、Kimi、千问 | 能否遵循格式、保留事实、给出可核对的依据 |
| 修改现有代码仓库 | GPT-6.1 Sol、Claude Sonnet 5.5；再加入 Kimi K3、GLM-5.3、MiniMax M3 | 测试是否通过、是否改错范围、人工返工量 |
| 难度较高的推理与研究 | GPT-6 Astra、Claude Fable 5.1、Gemini 4 Argon | 正确率、证据质量、完成时间和总费用 |
| 批量分类、抽取、短文本处理 | GPT-6 Luna、DeepSeek Flash、Qwen Flash 系列 | 单条成功成本、格式稳定性、延迟 |
| 图片、视频与文档混合分析 | Gemini；也可比较 Qwen 多模态、Kimi K3、Seed2.1 | 具体型号支持的输入类型、识别与引用是否准确 |
| 搜索新闻、研究 X 上的公开信息 | 带 Web Search / X Search 的 Grok，以及其他带搜索工具的助手 | 来源是否真实、事件日期是否正确、引用是否支持结论 |
| 本地或私有部署 | 按机器容量选择 Qwen 开放权重型号；有足够算力再评估 Kimi 等大模型 | 内存、吞吐量、许可证、运维成本 |

如果只是个人使用，先拿自己经常做的几件事试两个产品就够了。写作时看修改量，读论文时查页码和原句，写代码时运行测试。只看回答是否流畅，很容易选中一个解释好听、交付却不合格的助手。

## 2. 先分清聊天产品、API 和开放权重

讨论模型时，至少要区分三个层面。

**聊天产品**提供完整的使用界面。文件上传、搜索、记忆、代码执行、连接外部应用等功能，会共同影响最终体验。ChatGPT、Claude、Gemini、豆包和 Kimi 都属于用户可以直接使用的产品入口。

**应用程序接口（Application Programming Interface，API）**让程序调用一个指定型号。你需要处理提示词、工具、错误、重试和计费。模型的输入类型、输出上限、接口支持和账户额度，要逐项核对。

**开放权重**允许你下载模型参数并自行运行。是否能商用、修改、分发，以及是否有额外条件，由具体许可证决定。仓库公开、权重公开和完整训练过程公开是不同的事情。Qwen 与 Kimi 的官方仓库就分别提供了模型、部署和授权说明。[^qwen-weights][^kimi]

一个聊天产品的订阅费用，不能拿来和 API 的每百万 token 单价直接比较。一个产品可以调用多种模型和工具；一个 API 型号也不一定包含该产品里的全部功能。以 Gemini 4 Argon 为例，当前官方定价页明确说明，它不提供 API 免费层，也不包含在 Google AI Pro 计划中。[^gemini-pricing]

下面列的是当前应关注的产品和模型，不表示它们拥有相同的访问条件。

| 厂商 / 模型家族 | 常见产品或开发入口 | 截止日期内值得核对的型号与状态 |
| --- | --- | --- |
| OpenAI | ChatGPT、Codex、OpenAI API | GPT-6 Astra、GPT-6.1 Sol、GPT-6 Luna；官方按能力、成本与速度分档[^openai-guide] |
| Anthropic | Claude、Claude Code、Claude API | Fable 5.1、Opus 5.5、Sonnet 5.5、Haiku 5.5[^claude-models] |
| Google | Gemini、Google AI Studio、Gemini API | Gemini 4 Argon；需区分旗舰模型与其他速度、成本档位[^gemini-models] |
| Grok | Grok、API Console | Grok 4.7；搜索、语音和媒体生成有各自的工具或接口[^grok] |
| DeepSeek | DeepSeek 网页 / App、API | `deepseek-flash` 当前对应 V4.1 Flash；`deepseek-v4-pro` 对应 V4 Pro 0813[^deepseek-pricing] |
| Qwen / 通义千问 | 千问、阿里云百炼、模型仓库 | API 包含 Qwen3.8 Max、Qwen3.7 Plus、Qwen3.8 Flash；另有 Qwen3.8 开放权重[^qwen-models][^qwen-weights] |
| Moonshot / Kimi | Kimi、Kimi Code、开放平台 | Kimi K3；官方已发布原生多模态模型及开放权重[^kimi] |
| 智谱 / Z.ai | GLM 产品、开放平台、Coding Plan | GLM-5.3；当前旗舰 API 支持文本输入[^glm] |
| 字节 / Seed | 豆包、火山方舟 | Seed2.1；Seedance、Seedream 分别是视频和图像方向的产品线[^seed] |
| MiniMax | MiniMax Agent、MiniMax Code、API | M3；M3.1-Flash-Preview 当前仅通过 M Plan 和 MiniMax Code 提供[^minimax-models] |
| Mistral | Mistral Studio、Mistral Vibe、API | Mistral Large 4 公开预览；权重计划于 2026 年 10 月底发布[^mistral] |
| Meta | Meta AI、Muse | 官方首页当前展示 Muse Wonder / Wonder Full；部署与接入条件应另查开发者文档[^meta] |

## 3. 这些模型现在各自值得看什么

### OpenAI：按照任务难度选择 GPT-6 档位

OpenAI 的当前指南将 **Astra** 放在最复杂的推理、编码与专业工作档位，将 **GPT-6.1 Sol** 定位为速度、成本和能力之间的平衡选择，将 **Luna** 用于更集中、调用量更大的任务。这是厂商定位，不意味着所有任务都应该使用最贵的型号。[^openai-guide]

对开发者来说，接口兼容性同样会影响选择。GPT-6.1 Sol 的官方模型页明确要求：**工具调用使用 Responses API，Chat Completions 支持不带工具的请求**。如果你的现有程序依赖 Chat Completions 的工具调用，只替换 `model` 字段可能不够。其 API 也不支持 `none` 和 `minimal` 推理档位。[^openai-sol]

我的做法会是先用 Sol 评估主要工作，再把它反复失败的困难任务交给 Astra；分类和短文本抽取则单独评估 Luna。这样能看到能力升级究竟减少了多少失败和返工。

### Claude：比较具体档位，也比较 Claude Code 的工作方式

Claude 当前的公开产品线包含 **Fable 5.1、Opus 5.5、Sonnet 5.5 和 Haiku 5.5**。模型概览列出了各自的定位、上下文、接口标识与价格；选型时应以具体型号为单位。[^claude-models]

如果主要工作是修改现有仓库，我会把 Sonnet 放进第一轮评估，再对困难样本比较 Opus 和 Fable。评估 Claude Code 时，还要记录它读取了哪些文件、执行了哪些命令、如何处理失败。模型与代码工具共同完成任务，把整个工作流的成绩归因于模型本身，会误导 API 选型。

### Gemini：长生成与多模态值得评估，免费额度要单独看

**Gemini 4 Argon** 已出现在官方模型目录和定价页中。Google 将它定位于复杂软件工程、数学与科学问题、多步骤 Agent，以及最长可达 1M token 的长生成任务。这里的**输出长度**与输入上下文窗口是不同指标，调用时要分别核对。[^gemini-models][^gemini-pricing]

如果要处理论文、图表、图片或视频，我会先比较 Gemini 的具体输入能力，再测试提取和引用是否准确。长文档能被接收，只说明输入满足限制；读者真正需要的是模型能找到正确证据，并且没有漏掉例外条款。

Gemini 4 Argon 当前不提供 API 免费层。其发布期价格截至 **2026 年 11 月 30 日**；**12 月 1 日起**执行另一组价格。用它估算持续运行的服务时，应该同时算两种情况。[^gemini-pricing]

### Grok：实时信息来自搜索工具

当前官方文档推荐 **Grok 4.7** 用于代码、聊天和工具任务，列出的上下文为 500K token。它已经不能只按“社交平台聊天助手”来理解。[^grok]

但搜索场景有一个必须明确的条件：**没有启用搜索工具时，模型不会自动获得实时事件信息**。API 需要启用 Web Search 或 X Search，并核对返回的来源。Grok 文档也明确指出这一限制。[^grok]

如果你的任务经常要查 X 上的公开讨论，Grok 很值得进入候选名单。是否能交付可靠研究报告，还要检查信息源、事件发生时间，以及引用有没有真正支持结论。

### DeepSeek：确认别名背后的版本和时段价格

DeepSeek 当前推荐使用的模型名 `deepseek-flash` 对应 **DeepSeek V4.1 Flash**。旧的 `deepseek-v4-flash` 等名称仍可能接受请求，但官方说明服务已经转由 V4.1 Flash 提供。Pro 的当前版本则是 **V4 Pro 0813**。[^deepseek-updates][^deepseek-pricing]

这会影响复现：代码里的型号字符串没有改变，实际服务版本仍可能变化。做回归测试时，应同时记录请求日期、模型名和当时官方公布的对应版本。

DeepSeek 的价格还区分高峰、空闲时段和缓存命中情况。对于可以安排执行时间的批处理任务，这些条件会影响费用；对于需要立即返回的交互任务，则不能只用最低价格估算。[^deepseek-pricing]

### Qwen：云端型号与可下载模型分开选

阿里云百炼当前列出了 **Qwen3.8 Max、Qwen3.7 Plus、Qwen3.8 Flash** 等型号，也提供独立的全模态与实时接口。不同后缀对应不同任务和服务规格，要根据具体型号判断输入与工具支持。[^qwen-models]

Qwen 的官方仓库已经列出 **Qwen3.8-27B** 等可下载权重，并给出多种推理框架的部署说明。它值得被本地部署用户优先评估；但不要假设云端的 Max、Plus、Flash 与某个可下载模型完全相同，也不要用代码仓库的许可证替代权重文件附带的许可证。[^qwen-weights]

### Kimi：K3 已经覆盖多模态与工程任务

**Kimi K3** 是官方发布的开放权重、原生多模态 Agent 模型，支持文本、图像和视频，具有 1M token 上下文。官方介绍同时覆盖工程任务与知识工作，已超出早期“长文本阅读助手”的范围。权重采用 **Kimi K3 License**，部署前需要阅读具体条款。[^kimi]

如果经常处理中文资料、代码仓库和带图文档，我会把它放入候选。官方发布的大模型权重也不等于普通笔记本能舒适运行：部署规格、量化方式和可用内存需要另行确认。

### GLM：旗舰 5.3 的输入仍是文本

Z.ai 当前的旗舰 **GLM-5.3** 面向复杂软件工程和 Agent 任务。官方文档给出的规格是 **1M token 上下文、128K 最大输出、文本输入**，并提供工具调用、结构化输出和上下文缓存等说明。[^glm]

这意味着，用它处理扫描件或图片时，需要另选视觉模型或加入识别步骤。厂商拥有多模态产品线，并不能推导出每个旗舰型号都能直接看图。

### Seed / 豆包：通用模型与媒体生成分别核对

字节官方当前展示的通用模型是 **Seed2.1**，发布说明覆盖工具使用、工程任务和多模态理解。**Seedance 2.5** 属于视频方向，**Seedream** 属于图像方向；这些名称不应该混进通用语言模型的版本比较。[^seed]

如果你主要使用豆包，应该比较实际产品能完成哪些工作。如果要接火山方舟，则核对平台上的具体模型、接口和账单。聊天产品里的体验与 API 配置需要分别验收。

### MiniMax：M3 与 M3.1 预览的接入范围不同

MiniMax 当前的模型文档列出了 **M3** 和 **M3.1-Flash-Preview**。M3 面向多模态编码并提供 1M 上下文；M3.1 预览当前只通过 **M Plan 和 MiniMax Code** 提供，不能据此假定常规按量 API 已开放。[^minimax-models]

它值得进入代码工作流的候选集合。比较费用时，要区分按量 API 与订阅额度，还要注意 M3 在输入超过 512K token 后使用另一档价格。[^minimax-pricing]

### Mistral 与 Meta：加入候选，但先确认开放方式

Mistral 于 **2026 年 10 月 6 日**公布 **Mistral Large 4**。截至本文日期，可以试用的是公开预览 API；官方计划在 10 月底发布权重。因此，现在可以安排 API 评估，但本地部署计划应等待实际权重和许可证。[^mistral]

Meta 的官方首页已经将 **Muse Wonder 和 Muse Wonder Full** 展示为最新模型，并提供 Muse 产品入口。如果在关注 Meta 生态，应把 Muse 系列加入观察范围；是否能通过你的账户调用 API、是否有可下载权重，需要独立确认。[^meta]

## 4. API 价格怎么比较才有意义

Token 是模型处理和计费的文本单位，不等于汉字数或英文单词数。以下按 **每百万文本 token、美元、普通按量请求**比较：输入取未命中缓存的价格，输出单列；假定输入长度未触发加价档位，不含搜索等工具费用、税费、区域附加费和加速服务。DeepSeek 采用高峰时段价格。

| 模型 | 输入 / 百万 token | 输出 / 百万 token | 会影响预算的条件 |
| --- | ---: | ---: | --- |
| GPT-6 Astra | 10.00 | 50.00 | 输入超过 272K 后，整次请求适用长上下文加价[^openai-astra] |
| GPT-6.1 Sol | 2.00 | 10.00 | 同样需注意超过 272K 的加价与处理档位[^openai-sol] |
| GPT-6 Luna | 0.10 | 0.50 | 也有长上下文和服务档位价格差异[^openai-luna] |
| Claude Fable 5.1 | 10.00 | 50.00 | 缓存与批处理另有规则[^claude-models] |
| Claude Opus 5.5 | 4.00 | 20.00 | 缓存与批处理另有规则[^claude-models] |
| Claude Sonnet 5.5 | 2.00 | 10.00 | 缓存与批处理另有规则[^claude-models] |
| Gemini 4 Argon | 2.00 | 10.00 | 仅为截至 2026-11-30 的发布期价格[^gemini-pricing] |
| Grok 4.7 | 2.00 | 6.00 | 搜索等工具可能产生额外费用[^grok] |
| DeepSeek Flash | 0.30 | 1.20 | 高峰价格；空闲时段为其一半[^deepseek-pricing] |
| DeepSeek V4 Pro | 1.32 | 3.96 | 高峰价格；空闲时段为其一半[^deepseek-pricing] |
| MiniMax M3 | 0.30 | 1.20 | 标准档、输入不超过 512K；采用定价页当前实际收费[^minimax-pricing] |
| Mistral Large 4 | 1.36 | 4.18 | 当前为公开预览型号[^mistral] |

**Gemini 4 Argon 从 2026 年 12 月 1 日起，输入与输出价格分别调整为 4.00 和 20.00 美元 / 百万 token。** 11 月底以前的价格不能直接用于估算明年的账单。[^gemini-pricing]

这张表只帮助比较文本 token 费率。Qwen、Kimi、GLM 和 Seed 应按实际接入平台的地区、部署方式与规格查价；把人民币国内报价、美元国际报价和订阅额度放在同一列，数字看似齐全，实际无法直接比较。

### 用一个假设工作量算月费用

假设某项纯文本业务每月执行 **10,000 次请求**，每次包含 **4,000 个未缓存输入 token**，账单计入 **1,000 个输出 token**。没有重试、工具调用和额外计费项，那么一个月需要 40M 输入、10M 输出。

计算方法是：

```text
月文本费用 = 40 × 输入单价 + 10 × 输出单价
```

按上表计算，GPT-6.1 Sol 为 **180 美元**，GPT-6 Luna 为 **9 美元**，DeepSeek Flash 按高峰价为 **24 美元**。这些是上述假设下的算术结果，不是实测账单，也不说明三个模型在该业务上的成功率相同。

如果强模型每次贵一些，却少重试、少返工，它仍可能更划算。我更关心这个指标：

```text
每个成功任务的成本 = 模型、工具、重试等总费用 ÷ 验收通过的任务数
```

评估推理模型时，还应检查账单是否包含不可见的推理 token。Google 的定价页就明确将思考 token 计入输出价格。缓存、批处理和工具计费也需要按各家文档分别计算。[^gemini-pricing][^openai-astra][^minimax-pricing]

## 5. 订阅和接入可以怎么落地

### 个人使用：用常做的任务决定保留哪个产品

我建议先准备五个真实任务，例如修改一篇文章、读一份带图的报告、解释一段陌生代码、整理一组资料、查一个近期事件。用相同材料试两个产品，记录每次需要纠正什么。

如果主要写代码，优先比较代码工具能否在你的仓库中完成修改并通过检查。如果主要写作和阅读，检查事实、引用与修改量。如果经常搜索近期消息，检查来源与事件日期。试用之后再决定订阅，通常比同时购买多个“旗舰套餐”更容易判断价值。

### 应用开发：先建立一个基线，再决定是否分层

先选一个能够接入的模型，把提示词、输出格式和验收过程跑通，再用真实样本比较替代型号。我的候选起点会是：

- **复杂编码与工具工作流**：GPT-6.1 Sol、Claude Sonnet 5.5，加入 Kimi K3、GLM-5.3、MiniMax M3 做比较。
- **批量抽取与分类**：先评估 GPT-6 Luna、DeepSeek Flash、Qwen Flash。
- **混合媒体输入**：从 Gemini 与 Qwen 的具体多模态型号开始，按需要加入 Kimi 和 Seed。
- **搜索任务**：比较带搜索工具的 Grok 与其他助手，重点验收引用。

接入时，先确认具体型号是否支持所需的输入和工具调用，再验收业务结果。GPT-6.1 Sol 的接口限制与 GLM-5.3 的文本输入限制，就值得在这一步检查。[^openai-sol][^glm]

等基线稳定后，再考虑把简单子任务交给低成本型号、把困难样本升级到能力更强的型号。为了省 token 一开始就加入多套接口和复杂路由，可能让问题更难定位。

### 本地部署：先按容量选规格

本地部署前，要看机器的可用内存或显存、模型权重大小、量化方式，以及目标上下文长度。混合专家模型（Mixture of Experts，MoE）每次只激活部分参数，仍需要根据部署实现安排完整权重的存储和装载；“激活参数少”不能直接等同于“占用内存少”。Kimi 和 Qwen 官方仓库提供了架构与运行说明。[^kimi][^qwen-weights]

对已有个人机器，我会先尝试能够完整装入内存的小规格模型，确认速度与质量，再增加规模。还要测试离线条件下能否完成任务：模型在本地运行，并不意味着你接入的搜索、云端识别和其他工具也在本地。

## 6. 用真实任务评估，别只看排行榜

公开基准测试可以帮助发现候选，但分数还取决于提示词、推理预算、采样次数和执行环境。Agent 评测里的 **harness**，指的是组织模型执行任务的一整套程序，包括上下文、工具、命令执行、重试和结果判断。Kimi K3 的官方报告就分别说明了使用的 harness、推理设置与成绩来源。[^kimi]

因此，两个发布页上同名测试的数字，不一定构成同条件比较。要比较代码模型，还应确认测试集版本、工具权限、时间预算和任务是否独立完成。

我建议先做一个约 **20 项任务**的小样本评估。它足以暴露常见问题，但还不能证明生产环境的稳定性。

| 任务类别 | 建议样本 | 怎么验收 |
| --- | ---: | --- |
| 代码修改 | 5 项真实 bug 或小功能 | 原测试和针对问题的检查通过，修改范围正确 |
| 资料阅读 | 5 项带页码、表格或例外条件的问题 | 答案可回到原文核对，未漏掉重要条件 |
| 中文写作 | 5 项有明确读者、长度和事实约束的任务 | 人工盲评可用性，记录修改量 |
| 工具与搜索 | 5 项需要多步操作或近期来源的任务 | 工具参数正确，来源有效，失败处理可接受 |

具体比较时，我会这样操作：

1. 固定输入材料、提示词和验收标准；记录模型标识、日期、推理档位、工具权限和费用上限。
2. 从相同初始状态运行每个候选。代码任务使用相同提交和依赖；不要让后运行的模型看到前一个模型的答案。
3. 对结果评分。记录成功率、人工纠正次数、耗时、token 和总费用，保留失败样本。
4. 把昂贵或偶发失败的样本再运行几次，观察波动。将这部分额外费用也计入评估。
5. 上线前用更大样本补测，并在模型升级或别名变化后回归关键任务。

这些步骤是选型方法建议，本文没有执行这组横向实验。你真正需要的结果，是“在我的任务上，哪个方案以可接受的费用完成得更可靠”。

## 7. 最后核对几个容易影响结果的条件

**“支持 1M 上下文”不等于一定读懂 1M 内容。** 输入上限、最大输出、长输入费率和证据提取质量，应分别检查。OpenAI 的长上下文加价、Gemini 的长生成规格与 GLM 的输入 / 输出限制，就不能合并成一个数字。[^openai-sol][^gemini-pricing][^glm]

**免费层的数据政策可能不同。** Gemini 定价页区分免费层和付费层的数据用途。处理尚未公开的代码或资料前，应阅读对应产品、层级和地区的数据政策；不要由“官方 API”四个字推断数据处理方式。[^gemini-pricing]

**预览、正式服务与开放权重有各自的时间表。** Mistral Large 4 当前是预览 API、权重仍属后续计划；MiniMax M3.1 预览也有接入范围限制。上线方案应以已经可以访问和验收的服务为基础。[^mistral][^minimax-models]

**接口兼容不等于行为相同。** 先检查所需的工具调用、结构化输出与推理参数，再测错误恢复。GPT-6.1 Sol 的工具调用接口限制就是一个具体例子。[^openai-sol]

**别名可能改变实际模型。** DeepSeek 对旧 Flash 名称的映射已经说明了这一点。为关键任务保存版本记录和失败样本，模型变动时才能知道应该重新检查什么。[^deepseek-pricing]

开始选型时，拿两三个候选跑完自己的核心任务；把验收通过率、返工量和成功任务成本记下来。下一次出现新型号，就用同一组样本判断它是否值得替换现有方案。

## 官方资料与更新记录

以下资料的访问与核对日期均为 **2026 年 10 月 14 日**。持续更新的型号和定价页面应以调用时的内容为准。

[^openai-guide]: OpenAI，[Using GPT-6：模型选择与接口指南](https://developers.openai.com/api/docs/guides/latest-model)。
[^openai-astra]: OpenAI，[GPT-6 Astra 型号、计费与上下文规格](https://developers.openai.com/api/docs/models/gpt-6-astra)。
[^openai-sol]: OpenAI，[GPT-6.1 Sol 型号、接口限制与定价](https://developers.openai.com/api/docs/models/gpt-6.1-sol)。
[^openai-luna]: OpenAI，[GPT-6 Luna 型号与定价](https://developers.openai.com/api/docs/models/gpt-6-luna)。
[^claude-models]: Anthropic，[Claude 模型概览：型号、规格与基础价格](https://platform.claude.com/docs/en/about-claude/models/overview)。
[^gemini-models]: Google，[Gemini API 模型目录](https://ai.google.dev/gemini-api/docs/models)。
[^gemini-pricing]: Google，[Gemini Developer API 定价与数据用途](https://ai.google.dev/gemini-api/docs/pricing)，包括 Gemini 4 Argon 发布期价格与 2026-12-01 起的费率。
[^grok]: Grok，[公开模型、价格与实时搜索限制](https://docs.x.ai/developers/models)。
[^deepseek-updates]: DeepSeek，[API 更新记录](https://api-docs.deepseek.com/updates)。
[^deepseek-pricing]: DeepSeek，[Models & Pricing：当前版本、别名与美元价格](https://api-docs.deepseek.com/quick_start/pricing)；[人民币价格与北京时间高峰规则](https://api-docs.deepseek.com/zh-cn/quick_start/pricing)。
[^qwen-models]: 阿里云，[百炼模型目录](https://help.aliyun.com/zh/model-studio/models)。
[^qwen-weights]: Qwen 团队，[Qwen3.5 / 3.6 / 3.8 官方模型仓库](https://github.com/QwenLM/Qwen3.5)，包含开放型号、发布日期、推理框架与许可证说明。
[^kimi]: Moonshot AI，[Kimi K3 官方仓库与技术说明](https://github.com/MoonshotAI/Kimi-K3)，包含多模态规格、部署、许可证与评测条件。
[^glm]: Z.ai，[GLM-5.3 模型说明](https://docs.z.ai/guides/llm/glm-5.3)。
[^seed]: ByteDance Seed，[Seed2.1 发布说明](https://seed.bytedance.com/en/blog/seed2-1-officially-released-advancing-ai-productivity)，2026-06-23；[Seed 官方模型与产品目录](https://seed.bytedance.com/en/)。
[^minimax-models]: MiniMax，[模型概览与 M3.1 预览接入说明](https://platform.minimax.io/docs/guides/models-intro)。
[^minimax-pricing]: MiniMax，[按量计费、长输入与优先处理价格](https://platform.minimax.io/docs/guides/pricing-paygo)。
[^mistral]: Mistral，[Introducing Mistral Large 4](https://mistral.ai/news/mistral-large-4/)，2026-10-06，包含公开预览、当前 API 价格和月底发布权重的计划。
[^meta]: Meta，[官方模型与产品首页](https://ai.meta.com/)，当前展示 Muse Wonder / Wonder Full 和 Muse 产品入口。
