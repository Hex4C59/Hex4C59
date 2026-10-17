"""Deterministic fixture policy; reads actual tool results, never calls an API."""
from __future__ import annotations

from copy import deepcopy
import json


class CorpusFixtureModel:
    def __init__(self, *, bad_first: bool = True, always_bad: bool = False,
                 query_override: str | None = None):
        self.bad_first, self.always_bad = bad_first, always_bad
        self.query_override = query_override
        self.requests: list[dict] = []
        self.responses: list[dict] = []
        self.counter = 0

    def call(self, name: str, **arguments):
        self.counter += 1
        return {"role": "assistant", "content": None, "tool_calls": [{
            "id": f"fixture-{self.counter}", "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)}}]}

    async def complete(self, messages, tools):
        self.requests.append({"messages": deepcopy(messages), "tools": deepcopy(tools)})
        response = self.respond(messages)
        self.responses.append(deepcopy(response))
        return response

    def respond(self, messages):
        stage = messages[0]["content"].splitlines()[0].removeprefix("STAGE: ")
        payload = json.loads(messages[1]["content"])
        if stage == "plan":
            questions = [{"id": f"Q{i}", "question": item["title"] + "说明了什么要求？",
                          "queries": [self.query_override or item["source_id"]]}
                         for i, item in enumerate(payload["catalog"][:2], 1)]
            value = {"focus": payload["task"], "questions": questions}
        elif stage == "research":
            tool_messages = [m for m in messages if m["role"] == "tool"]
            if not tool_messages:
                return self.call("search_sources", query=payload["question"]["queries"][0])
            observation = json.loads(tool_messages[-1]["content"])
            if not observation["ok"]:
                return {"role": "assistant", "content": "fixture: 工具失败，保留资料缺口。"}
            data = observation["result"]
            if len(tool_messages) == 1:
                if not data["hits"]:
                    return {"role": "assistant", "content": "fixture: 没有搜索结果。"}
                return self.call("fetch_source", source_id=data["hits"][0]["source_id"])
            if len(tool_messages) == 2:
                lines = [line.strip() for line in data["text"].splitlines() if len(line.strip()) >= 12]
                if not lines:
                    return {"role": "assistant", "content": "fixture: 没有足够长的可摘录文本。"}
                return self.call("save_note", source_id=data["source_id"], quote=lines[0][:600])
            return {"role": "assistant", "content": "fixture: 已保存本题的原文摘录。"}
        elif stage == "synthesize":
            claims = [{"question_id": note["question_id"], "text": note["quote"], "note_ids": [note["id"]]}
                      for note in payload["notes"]]
            if claims and (self.always_bad or (self.bad_first and payload["previous"] is None)):
                claims[0]["note_ids"] = ["N999"]
            value = {"title": "本地语料研究记录", "claims": claims,
                     "limitations": ["仅整理显式选定的本地文件；fixture 不证明模型研究质量，也未核验外部事实。"]}
        elif stage == "review":
            value = {"passed": not payload["mechanical_issues"],
                     "issues": ["修复引用后必须再次检查。"] if payload["mechanical_issues"] else []}
        else:
            raise ValueError("Unknown fixture stage")
        return {"role": "assistant", "content": json.dumps(value, ensure_ascii=False)}
