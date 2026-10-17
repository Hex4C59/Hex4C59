# Agent 机制的可执行例子

本包配合规划、上下文、人工确认、多 Agent 协作和 Guardrails 五篇文章。它使用真实的异步任务、文件或 SQLite 验证确定性规则；默认命令不调用模型，不需要账号或密钥。

从 ZIP 解压后进入目标目录：

```sh
unzip mechanisms.zip -d mechanisms
cd mechanisms
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
python -m unittest discover -v
```

Python 最低为 3.11。PowerShell 使用 `.venv\Scripts\Activate.ps1` 激活环境。单独观察一个机制可使用 `python app.py --part planning`；其他选项为 `context_budget`、`coordination`、`guardrails`。

- `planning.py` 区分正常完成、步骤失败、超时与达到轮次上限，避免把超时文字当成完成标记。
- `context_budget.py` 在实际请求之前限制上下文，保留当前任务和成组的工具调用及返回。字符预算不等于某个模型的 token 限额。
- `coordination.py` 在 SQLite 事务中保存确认请求、任务领取和消息读取进度，校验请求与实际操作是否对应。
- `guardrails.py` 在工具执行入口检查并阻断不允许的操作；它不把命令包装或提示词称为操作系统沙箱。

`app.py` 汇总运行四个模块的演示；每个模块返回实际检查结果，出现异常或检查失败时退出非零。测试使用合成数据和临时目录，覆盖成功路径和相应失败条件。

这些模块展示本地机制。用户或执行者标识由受信任调用者提供，不构成联网账号认证；工作区规则不隔离恶意进程。各模块说明和对应正文给出具体限制，不应直接当成多租户或生产安全服务使用。
