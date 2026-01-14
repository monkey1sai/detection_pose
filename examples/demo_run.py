import argparse

from saga.config import SagaConfig
from saga.runner import SagaRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SAGA MVP demo.")
    parser.add_argument("--run-dir", default="runs")
    parser.add_argument("--beam-width", type=int, default=3)
    parser.add_argument("--max-iters", type=int, default=2)
    parser.add_argument("--timeout-s", type=float, default=10.0)
    parser.add_argument("--sglang-url", default="http://localhost:8082/v1/chat/completions")
    parser.add_argument("--sglang-api-key", default="")
    parser.add_argument("--use-sglang", action="store_true")
    parser.add_argument("--use-llm-modules", action="store_true")
    parser.add_argument("--text", default="這是一段測試文字")
    parser.add_argument("--keywords", default="測試")
    parser.add_argument("--config", default="")
    args = parser.parse_args()

    if args.config:
        cfg = SagaConfig.from_file(args.config)
    else:
        cfg = SagaConfig(
            run_dir=args.run_dir,
            beam_width=args.beam_width,
            max_iters=args.max_iters,
            timeout_s=args.timeout_s,
            sglang_url=args.sglang_url,
            sglang_api_key=args.sglang_api_key,
            use_sglang=args.use_sglang,
            use_llm_modules=args.use_llm_modules,
        )
    runner = SagaRunner(cfg)
    keyword_list = [k.strip() for k in args.keywords.split(",") if k.strip()]
    result = runner.run_once(args.text, keywords=keyword_list)
    print(result["best_candidate"])
    print(f"run_id={result['run_id']}")


if __name__ == "__main__":
    main()
