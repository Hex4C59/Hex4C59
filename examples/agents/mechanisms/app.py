"""Run deterministic, real mechanism checks without a model account."""
import argparse
import asyncio
import importlib
import json
import sys

PARTS = ("planning", "context_budget", "coordination", "guardrails")


async def run(parts):
    print("fixture / 本地确定性机制验证；不调用模型服务")
    for name in parts:
        module = importlib.import_module(name)
        async with asyncio.timeout(20):
            result = await module.demo()
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise RuntimeError(name + " did not confirm its demonstration checks")
        print(name + ": " + json.dumps(result, ensure_ascii=False, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", choices=PARTS, help="Run just one mechanism")
    args = parser.parse_args()
    try:
        asyncio.run(run((args.part,) if args.part else PARTS))
        return 0
    except Exception as error:
        print("Mechanism verification failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
