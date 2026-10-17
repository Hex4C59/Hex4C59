# 实战教程公共运行层

各文章的 ZIP 在打包时包含本目录的 `agent_runtime.py` 和依赖版本。仓库内运行某个例子时，将本目录加入 `PYTHONPATH`；下载后的 ZIP 已把它放在入口旁。

运行层顺序执行模型给出的工具调用，检查工具名、JSON 参数及其 JSON Schema，把工具异常作为失败结果返回模型，并设置轮数、调用次数和异步总期限。同步工具应快速返回；这层代码不能强行停止阻塞的 Python 函数，也不是系统沙箱。大于 32,000 字符的工具结果返回错误，调用者应缩小查询。

`ScriptedModel` 提供固定响应，供本地演示和回归测试使用。它验证程序是否按预定调用处理真实工具，不验证模型选工具的能力。`OpenAIChatModel` 使用 `AsyncOpenAI`；启用 `--live` 前设置 `OPENAI_API_KEY`、`OPENAI_MODEL`，所选模型与服务应支持 Chat Completions 的工具调用。兼容服务可另设 `OPENAI_BASE_URL`。密钥从环境读取，不写入示例或日志。在线模型路径不在无密钥本地测试的覆盖范围内。

文件路径检查拒绝绝对路径、上级目录和符号链接，适用于由当前用户控制、没有其他进程并发更换目录的私有工作区。运行不受信代码需要额外的操作系统隔离。

默认事件只记录阶段、工具名、状态和耗时，不记录提示词、工具参数或工具内容。实际对话仍由调用方持有，应自行确定保存和脱敏方式。

接口依据（核对日期：2026-10-17）：

- [OpenAI 工具调用指南](https://developers.openai.com/api/docs/guides/function-calling)
- [JSON Schema 验证库](https://python-jsonschema.readthedocs.io/en/stable/validate/)
