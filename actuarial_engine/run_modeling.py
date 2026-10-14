"""End-to-end orchestration entry point for actuarial model candidates."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from .calculation import EngineRunResult, run_modeling
from .config import EngineConfig


def _parse_csv_option(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of-date", required=True, type=date.fromisoformat)
    parser.add_argument("--model-run-id")
    parser.add_argument("--triangle-csv", type=Path)
    parser.add_argument("--expected-input-csv", type=Path)
    parser.add_argument("--triangle-grains", default="annual")
    parser.add_argument("--measures", default="incurred")
    parser.add_argument(
        "--development-methods",
        default="simple_average,volume_weighted,recent_3_weighted",
    )
    parser.add_argument("--tail-methods", default="none,curve")
    parser.add_argument(
        "--ultimate-methods",
        default="chainladder,mack_chainladder,bornhuetter_ferguson,cape_cod",
    )
    parser.add_argument("--output-directory", type=Path, default=Path("engine_output"))
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = EngineConfig(
        as_of_date=args.as_of_date,
        triangle_grains=_parse_csv_option(args.triangle_grains),
        measures=_parse_csv_option(args.measures),
        development_methods=_parse_csv_option(args.development_methods),
        tail_methods=_parse_csv_option(args.tail_methods),
        ultimate_methods=_parse_csv_option(args.ultimate_methods),
    )

    if args.triangle_csv:
        triangle = pd.read_csv(args.triangle_csv)
        expected = (
            pd.read_csv(args.expected_input_csv) if args.expected_input_csv else None
        )
        repository = None
    else:
        from .io import SnowflakeRepository

        repository = SnowflakeRepository.from_environment()
        triangle = repository.read_triangle(
            as_of_date=args.as_of_date,
            triangle_grains=config.triangle_grains,
        )
        expected = repository.read_expected_input(
            as_of_date=args.as_of_date,
            triangle_grains=config.triangle_grains,
        )

    result = run_modeling(
        triangle,
        config=config,
        expected_input=expected,
        model_run_id=args.model_run_id,
    )
    if args.no_write or repository is None:
        _write_local_results(result, args.output_directory)
    else:
        repository.write_run(result)

    print(
        f"model_run_id={result.model_run_id} "
        f"ldf_candidates={len(result.ldf_candidates)} "
        f"model_candidates={len(result.model_candidates)}"
    )


def _write_local_results(result: EngineRunResult, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name in (
        "ldf_observations",
        "ldf_candidates",
        "tail_candidates",
        "model_candidates",
        "diagnostics",
    ):
        getattr(result, name).to_csv(directory / f"{name}.csv", index=False)


if __name__ == "__main__":
    main()
