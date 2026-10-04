"""Command-line interface: ``incident-analyzer <command> [options]``."""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

from incident_analyzer import __version__
from incident_analyzer.config import ConfigurationError, Settings, load_settings
from incident_analyzer.schema import SchemaError, read_incidents, write_csv

log = logging.getLogger("incident_analyzer")

_DURATION = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([smhd])\s*$", re.IGNORECASE)
_UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}


def parse_duration(value: str) -> timedelta:
    match = _DURATION.match(value)
    if not match:
        raise argparse.ArgumentTypeError(f"invalid duration {value!r}; use e.g. 90s, 15m, 6h, 1d")
    amount, unit = match.groups()
    duration = timedelta(**{_UNITS[unit.lower()]: float(amount)})
    if duration <= timedelta(0):
        raise argparse.ArgumentTypeError("duration must be positive")
    return duration


def _non_negative_float(value: str) -> float:
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return number


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_fetch(args: argparse.Namespace, settings: Settings) -> int:
    from incident_analyzer.ingest import PagerDutyClient, fetch_incidents

    token = settings.require_pagerduty_token()
    with PagerDutyClient(token, base_url=settings.pagerduty_base_url) as client:
        df = fetch_incidents(client, since=args.since, until=args.until, service_ids=args.service_id)
    path = write_csv(df, args.output or settings.raw_path)
    print(f"Fetched {len(df)} incidents -> {path}")
    return 0


def cmd_curate(args: argparse.Namespace, settings: Settings) -> int:
    from incident_analyzer.curation import curate

    raw = pd.read_csv(args.input or settings.raw_path)
    curated, report = curate(raw)
    path = write_csv(curated, args.output or settings.curated_path)
    print(
        f"Curated {report.input_rows} -> {report.output_rows} incidents "
        f"({report.empty_payloads_removed} without payload, {report.duplicates_removed} duplicates) -> {path}"
    )
    return 0


def cmd_classify(args: argparse.Namespace, settings: Settings) -> int:
    from incident_analyzer.classify import OpenAIClassifier, classify_incidents

    output = Path(args.output or settings.categorized_path)
    source = Path(args.input or settings.curated_path)
    if args.resume and output.is_file():
        source = output
    incidents = read_incidents(source)

    classifier = OpenAIClassifier(settings.require_openai_key(), args.model or settings.llm_model)
    classified = classify_incidents(incidents, classifier, checkpoint=lambda df: write_csv(df, output))
    write_csv(classified, output)
    print(f"Classified {len(classified)} incidents -> {output}")
    return 0


def _fit(args: argparse.Namespace, settings: Settings):
    from incident_analyzer.transitions import TransitionModel

    incidents = read_incidents(args.input or settings.categorized_path)
    return TransitionModel.fit(incidents, max_gap=args.max_gap, smoothing=args.smoothing)


def cmd_transitions(args: argparse.Namespace, settings: Settings) -> int:
    model = _fit(args, settings)
    table = model.table
    path = write_csv(table, args.output or settings.transitions_path)
    observed = table[table["count"] > 0]
    print(
        f"Fitted {len(observed)} observed transitions across {len(model.services)} services "
        f"({int(observed['count'].sum())} incident pairs) -> {path}"
    )
    return 0


def cmd_forecast(args: argparse.Namespace, settings: Settings) -> int:
    from incident_analyzer.analytics import format_duration

    model = _fit(args, settings)
    if args.service not in model.services:
        print(f"Unknown service {args.service!r}. Known services: {', '.join(model.services)}", file=sys.stderr)
        return 2
    state = model.state(args.service)
    current = args.current or (state.category if state else None)
    print(f"Service: {args.service}\nCurrent: {current}\n")
    for rank, f in enumerate(model.forecast(args.service, args.current, top_k=args.top_k), start=1):
        timing = f"  median gap {format_duration(f.median_delay_s)}" if f.median_delay_s is not None else ""
        print(f"  {rank}. {f.category:<32} {f.probability:6.1%}  (n={f.support}, {f.basis}){timing}")
    return 0


def cmd_serve(args: argparse.Namespace, settings: Settings) -> int:
    from incident_analyzer.dashboard import create_app, load_dashboard_data

    app = create_app(load_dashboard_data(args.data or settings.categorized_path))
    # Settings already honour ./.env; stop Flask from searching parent
    # directories for other .env files.
    os.environ.setdefault("FLASK_SKIP_DOTENV", "1")
    app.run(host=args.host or settings.dashboard_host, port=args.port or settings.dashboard_port, debug=args.debug)
    return 0


def cmd_finetune_prep(args: argparse.Namespace, settings: Settings) -> int:
    from incident_analyzer.finetune import clean_corpus, known_labels, remove_leakage

    train_raw, test_raw = pd.read_csv(args.train), pd.read_csv(args.test)
    labels = known_labels(train_raw, test_raw)
    train, train_report = clean_corpus(train_raw, labels)
    test, test_report = clean_corpus(test_raw, labels)
    test, leaked = remove_leakage(train, test)

    out = Path(args.output_dir)
    write_csv(train, out / "train.csv")
    write_csv(test, out / "test.csv")
    for name, report in (("train", train_report), ("test", test_report)):
        print(
            f"{name}: {report.input_rows} -> {report.output_rows} rows, {report.classes} classes "
            f"(repaired {report.repaired_labels}, dropped {report.dropped_labels}, "
            f"de-duplicated {report.duplicates_removed})"
        )
    print(f"test: removed {leaked} rows that leak from train -> {out}")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="incident-analyzer",
        description="Incident analytics and transition forecasting for PagerDuty service fleets.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    p = sub.add_parser("fetch", help="download incidents from PagerDuty")
    p.add_argument("--since", help="ISO-8601 start of the window (default: all history)")
    p.add_argument("--until", help="ISO-8601 end of the window")
    p.add_argument("--service-id", action="append", help="restrict to a PagerDuty service ID (repeatable)")
    p.add_argument("-o", "--output", help="output CSV (default: <data dir>/incidents_raw.csv)")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("curate", help="remove noise and duplicates from a raw export")
    p.add_argument("-i", "--input", help="raw CSV (default: <data dir>/incidents_raw.csv)")
    p.add_argument("-o", "--output", help="output CSV (default: <data dir>/incidents_curated.csv)")
    p.set_defaults(func=cmd_curate)

    p = sub.add_parser("classify", help="assign taxonomy categories with an LLM")
    p.add_argument("-i", "--input", help="curated CSV (default: <data dir>/incidents_curated.csv)")
    p.add_argument("-o", "--output", help="output CSV (default: <data dir>/incidents_categorized.csv)")
    p.add_argument("--model", help="chat model name (default: $INCIDENT_ANALYZER_LLM_MODEL)")
    p.add_argument("--resume", action="store_true", help="continue a partially classified output file")
    p.set_defaults(func=cmd_classify)

    model_args = argparse.ArgumentParser(add_help=False)
    model_args.add_argument("-i", "--input", help="categorised CSV (default: <data dir>/incidents_categorized.csv)")
    model_args.add_argument(
        "--max-gap", type=parse_duration, help="ignore pairs further apart than this (e.g. 15m, 6h)"
    )
    model_args.add_argument(
        "--smoothing", type=_non_negative_float, default=0.0, help="additive smoothing constant (default: 0)"
    )

    p = sub.add_parser("transitions", parents=[model_args], help="fit and export the transition model")
    p.add_argument("-o", "--output", help="output CSV (default: <data dir>/transition_model.csv)")
    p.set_defaults(func=cmd_transitions)

    p = sub.add_parser("forecast", parents=[model_args], help="rank the most likely next incidents for a service")
    p.add_argument("service", help="service name as it appears in the dataset")
    p.add_argument("--current", help="assume this current category instead of the latest observed one")
    p.add_argument("-k", "--top-k", type=int, default=3)
    p.set_defaults(func=cmd_forecast)

    p = sub.add_parser("serve", help="launch the interactive dashboard")
    p.add_argument("--data", help="categorised CSV (default: <data dir>/incidents_categorized.csv)")
    p.add_argument("--host", help="bind address (default: $INCIDENT_ANALYZER_HOST or 127.0.0.1)")
    p.add_argument("--port", type=int, help="port (default: $INCIDENT_ANALYZER_PORT or 8050)")
    p.add_argument("--debug", action="store_true", help="enable Dash hot reload and debug tools")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("finetune-prep", help="clean and format the classifier fine-tuning corpus")
    p.add_argument("--train", default="data/finetune/train.csv")
    p.add_argument("--test", default="data/finetune/test.csv")
    p.add_argument("-o", "--output-dir", default="data/finetune")
    p.set_defaults(func=cmd_finetune_prep)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        return args.func(args, load_settings())
    except (ConfigurationError, SchemaError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
