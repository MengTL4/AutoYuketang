#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from utils.yuketang_exam_decoder import decode_exercise_payload, resolve_workdir


GET_EXERCISE_LIST_MARKER = "/mooc-api/v1/lms/exercise/get_exercise_list/"


def load_har_entries(har_path: Path) -> list[dict[str, Any]]:
    har = json.loads(har_path.read_text(encoding="utf-8"))
    return har["log"]["entries"]


def extract_exercise_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matches = []
    for entry in entries:
        url = entry.get("request", {}).get("url", "")
        if GET_EXERCISE_LIST_MARKER not in url:
            continue
        if entry.get("response", {}).get("status") != 200:
            continue
        matches.append(entry)
    return matches


def write_decoded_json(target: Path, payload: Any) -> None:
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def print_summary(
    decoded: dict[str, Any],
    url: str,
    font_url: str,
    mapping: dict[str, str],
) -> None:
    data = decoded.get("data", {})
    exercise_id = data.get("exercise_id")
    problems = data.get("problems", [])

    print(f"=== exercise_id={exercise_id} ===")
    print(f"url: {url}")
    print(f"font: {font_url}")
    print()

    for problem in problems:
        index = problem.get("index", "?")
        content = problem.get("content", {})
        body = content.get("Body", "")
        if body:
            print(f"Q{index}. {body}")
        for option in content.get("Options", []):
            print(f"  {option.get('key', '?')}. {option.get('value', '')}")
        print()

    if mapping:
        pairs = " ".join(f"{fake}->{real}" for fake, real in mapping.items())
        print("mapping:", pairs)
        print()


def build_output_name(exercise_id: Any) -> str:
    return f"decoded_exercise_{exercise_id}.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decode Yuketang get_exercise_list responses that use encrypted exam fonts."
    )
    parser.add_argument("har", type=Path, help="Path to the HAR file")
    parser.add_argument(
        "--workdir",
        type=Path,
        default=None,
        help="Directory used for cached fonts and decoded JSON outputs. Defaults to the HAR directory.",
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Do not write decoded JSON files next to the HAR.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    har_path = args.har.resolve()
    if not har_path.exists():
        print(f"HAR not found: {har_path}", file=sys.stderr)
        return 1

    workdir = resolve_workdir(args.workdir or har_path.parent)
    entries = load_har_entries(har_path)
    exercise_entries = extract_exercise_entries(entries)
    if not exercise_entries:
        print("No get_exercise_list responses found.", file=sys.stderr)
        return 1

    for entry in exercise_entries:
        url = entry["request"]["url"]
        payload = json.loads(entry["response"]["content"]["text"])
        decoded, mapping = decode_exercise_payload(payload, workdir=workdir)
        font_url = payload["data"]["font"]

        if not args.no_json:
            output_name = build_output_name(decoded["data"]["exercise_id"])
            write_decoded_json(workdir / output_name, decoded)

        print_summary(decoded, url, font_url, mapping)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
