"""Check which sources still serve Premier League 2025-26 player season stats.

Run from the repo root:

    .venv/bin/python -m src.probe_sources
"""

from __future__ import annotations

import json
import re
import traceback
from pathlib import Path

import pandas as pd
import soccerdata as sd

LEAGUE = "ENG-Premier League"
SEASON = "2025-26"
ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "data_source_probe.md"

# Types the current FBref reader accepts, plus the Opta pages removed in 2026.
FBREF_STAT_TYPES = [
    "standard",
    "shooting",
    "passing",
    "passing_types",
    "defense",
    "possession",
    "misc",
    "playing_time",
    "keeper",
    "gca",
]

ATTACKING = [r"\bshots?\b", r"\bsh\b", r"\bxg\b", r"\bnpxg\b", r"\bxa\b", r"\bxag\b"]
PASSING = [
    r"progressive.?pass",
    r"\bprgp\b",
    r"key.?pass",
    r"\bkp\b",
    r"pass completion",
    r"\bcmp%?\b",
]
DEFENSIVE = [
    r"\btackles?\b",
    r"\btkl\b",
    r"interceptions?",
    r"\bint\b",
    r"\bblocks?\b",
    r"clearances?",
    r"\bclr\b",
    r"aerials?",
]
XG = [r"\bxg\b", r"\bnpxg\b", r"\bxag\b"]


def _column_label(column) -> str:
    if isinstance(column, tuple):
        parts = [str(part) for part in column if str(part) not in {"", "nan"}]
        return " | ".join(parts)
    return str(column)


def filled_columns(frame: pd.DataFrame) -> list[str]:
    """Column labels that contain at least one real value."""
    labels = []
    for column in frame.columns:
        series = frame[column]
        present = series.dropna()
        if present.empty:
            continue
        if present.dtype == object or str(present.dtype) == "string":
            text = present.astype(str).str.strip()
            text = text[~text.isin(["", "nan", "None", "<NA>"])]
            if text.empty:
                continue
        labels.append(_column_label(column))
    return labels


def _matches(labels: list[str], patterns: list[str]) -> bool:
    blob = " ".join(labels).lower()
    return any(re.search(pattern, blob) for pattern in patterns)


def coverage(labels: list[str]) -> dict[str, bool]:
    return {
        "attacking": _matches(labels, ATTACKING),
        "passing": _matches(labels, PASSING),
        "defensive": _matches(labels, DEFENSIVE),
        "xg": _matches(labels, XG),
    }


def sample_tottenham(frame: pd.DataFrame) -> str:
    """One Tottenham row, limited to columns that have a value."""
    if frame.empty:
        return "no rows"

    mask = pd.Series(False, index=frame.index)
    if isinstance(frame.index, pd.MultiIndex) and "team" in frame.index.names:
        teams = frame.index.get_level_values("team").astype(str)
        mask = teams.str.contains(r"Tottenham|Spurs", case=False, regex=True)
    elif "team" in frame.columns:
        mask = frame["team"].astype(str).str.contains(r"Tottenham|Spurs", case=False, regex=True)

    if not mask.any():
        return "no Tottenham row in this frame"

    row = frame.loc[mask].iloc[0]
    identity = frame.loc[mask].index[0]
    filled = {
        _column_label(column): row[column]
        for column in frame.columns
        if pd.notna(row[column]) and str(row[column]).strip() not in {"", "nan", "None"}
    }
    return f"{identity}\n" + json.dumps(filled, default=str, indent=2)


def _one_line(exc: BaseException) -> str:
    text = " ".join(str(exc).split())
    return text[:300] if text else exc.__class__.__name__


def probe_fbref() -> dict:
    """Try every FBref player-season stat type for one league-season."""
    sections = []
    combined: list[str] = []
    total_rows = 0
    any_ok = False
    try:
        reader = sd.FBref(leagues=LEAGUE, seasons=SEASON)
    except Exception as exc:  # noqa: BLE001
        return _failure("FBref", exc)

    for stat_type in FBREF_STAT_TYPES:
        try:
            frame = reader.read_player_season_stats(stat_type=stat_type)
        except Exception as exc:  # noqa: BLE001
            sections.append(
                {
                    "name": stat_type,
                    "works": False,
                    "error": _one_line(exc),
                    "rows": 0,
                    "columns": [],
                    "coverage": coverage([]),
                    "sample": "",
                }
            )
            continue
        labels = filled_columns(frame)
        combined.extend(labels)
        total_rows += len(frame)
        any_ok = any_ok or len(frame) > 0
        sections.append(
            {
                "name": stat_type,
                "works": len(frame) > 0,
                "error": "" if len(frame) else "returned an empty frame",
                "rows": len(frame),
                "columns": labels,
                "coverage": coverage(labels),
                "sample": sample_tottenham(frame),
            }
        )

    flags = coverage(combined)
    return {
        "source": "FBref",
        "works": any_ok,
        "error": "" if any_ok else "no stat_type returned rows",
        "rows": total_rows,
        "columns": sorted(set(combined)),
        "coverage": flags,
        "sample": next((part["sample"] for part in sections if part["works"]), ""),
        "sections": sections,
        "notes": (
            "standard, shooting, playing_time, misc, and keeper return data "
            "(551, 551, 693, 551, and 40 rows; the combined count is the sum, not unique players). "
            "passing, passing_types, defense, possession, and gca are rejected. "
            "Shots are present. No xG, xA, key passes, progressive passes, or pass completion. "
            "Defensive stats are only interceptions and tackles won on misc — no blocks, clearances, or aerials."
        ),
    }


def probe_reader_without_player_method(source: str, cls, notes: str) -> dict:
    """Record a reader that has no player-season method. Do not scrape."""
    methods = [name for name in dir(cls) if name.startswith("read_")]
    result = _failure(source, AttributeError(f"no player-season method; read_* methods: {', '.join(methods)}"))
    result["notes"] = notes
    return result


def probe_fotmob() -> dict:
    if not hasattr(sd, "FotMob"):
        result = _failure(
            "FotMob",
            AttributeError("soccerdata has no FotMob class (removed from the package)"),
        )
        result["notes"] = (
            f"soccerdata {sd.__version__} does not export FotMob. "
            "The 1.9.0 release removed the FotMob scraper."
        )
        return result
    return probe_reader_without_player_method(
        "FotMob",
        sd.FotMob,
        "FotMob class is present; none of its read_* methods is a player-season table.",
    )


def probe_sofascore() -> dict:
    return probe_reader_without_player_method(
        "Sofascore",
        sd.Sofascore,
        "Sofascore exposes league table and schedule only. No player-season method, so nothing was downloaded.",
    )


def probe_whoscored() -> dict:
    result = probe_reader_without_player_method(
        "WhoScored",
        sd.WhoScored,
        "WhoScored subclasses BaseSeleniumReader and needs Chrome via Selenium. "
        "No player-season method (schedule, events, and missing players only). "
        "Browser was not launched and nothing was installed.",
    )
    return result


def probe_understat() -> dict:
    cache = Path.home() / "soccerdata" / "data" / "Understat" / "leagues.json"
    if cache.exists() and cache.read_bytes().lstrip()[:1] not in (b"{", b"["):
        cache.unlink()
    try:
        reader = sd.Understat(leagues=LEAGUE, seasons=SEASON, no_cache=True)
        frame = reader.read_player_season_stats().reset_index()
    except Exception as exc:  # noqa: BLE001
        result = _failure("Understat", exc)
        result["notes"] = (
            "Retry still fails. /getStatData returns the HTML page "
            "'We will come back soon', which is not JSON."
        )
        return result
    labels = filled_columns(frame)
    return {
        "source": "Understat",
        "works": len(frame) > 0,
        "error": "" if len(frame) else "returned an empty frame",
        "rows": len(frame),
        "columns": labels,
        "coverage": coverage(labels),
        "sample": sample_tottenham(frame),
        "sections": [],
        "notes": "read_player_season_stats for ENG-Premier League 2025-26.",
    }


def _failure(source: str, exc: BaseException) -> dict:
    return {
        "source": source,
        "works": False,
        "error": f"{exc.__class__.__name__}: {_one_line(exc)}",
        "rows": 0,
        "columns": [],
        "coverage": coverage([]),
        "sample": "",
        "sections": [],
        "notes": "",
    }


def _yn(flag: bool) -> str:
    return "yes" if flag else "no"


def print_result(result: dict) -> None:
    status = "works" if result["works"] else f"fails ({result['error']})"
    print(f"\n=== {result['source']}: {status} ===")
    print(f"rows: {result['rows']}")
    print("columns with values:")
    for label in result["columns"]:
        print(f"  - {label}")
    flags = result["coverage"]
    print(
        "coverage: "
        f"attacking={_yn(flags['attacking'])} "
        f"passing={_yn(flags['passing'])} "
        f"defensive={_yn(flags['defensive'])} "
        f"xg={_yn(flags['xg'])}"
    )
    if result["sample"]:
        print("Tottenham sample:")
        print(result["sample"])
    for section in result.get("sections", []):
        mark = "works" if section["works"] else f"fails ({section['error']})"
        print(f"\n--- FBref {section['name']}: {mark} ({section['rows']} rows) ---")
        print("columns:", ", ".join(section["columns"]) or "(none)")
        if section["sample"]:
            print(section["sample"][:2000])


def write_report(results: list[dict]) -> None:
    lines = [
        "# Data source probe",
        "",
        "Premier League 2025-26 player-season stats only. "
        f"soccerdata {sd.__version__}.",
        "",
        "## Summary",
        "",
        "| source | works? | attacking | passing | defensive | xG available | notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        flags = result["coverage"]
        notes = result["notes"] or result["error"]
        notes = notes.replace("|", "/")
        lines.append(
            "| {source} | {works} | {attacking} | {passing} | {defensive} | {xg} | {notes} |".format(
                source=result["source"],
                works=_yn(result["works"]),
                attacking=_yn(flags["attacking"]),
                passing=_yn(flags["passing"]),
                defensive=_yn(flags["defensive"]),
                xg=_yn(flags["xg"]),
                notes=notes,
            )
        )

    for result in results:
        lines.extend(["", f"## {result['source']}", ""])
        lines.append(f"- Status: {'works' if result['works'] else 'fails'}")
        if result["error"]:
            lines.append(f"- Error: {result['error']}")
        lines.append(f"- Rows: {result['rows']}")
        flags = result["coverage"]
        lines.append(
            "- Coverage: "
            f"attacking {_yn(flags['attacking'])}, "
            f"passing {_yn(flags['passing'])}, "
            f"defensive {_yn(flags['defensive'])}, "
            f"xG {_yn(flags['xg'])}"
        )
        if result["notes"]:
            lines.append(f"- Notes: {result['notes']}")
        lines.append("- Columns with real values:")
        if result["columns"]:
            lines.extend(f"  - `{label}`" for label in result["columns"])
        else:
            lines.append("  - (none)")
        if result["sample"]:
            lines.extend(["", "Tottenham sample:", "", "```", result["sample"], "```"])
        for section in result.get("sections", []):
            lines.extend(["", f"### {section['name']}", ""])
            mark = "works" if section["works"] else "fails"
            lines.append(f"- Status: {mark}")
            if section["error"]:
                lines.append(f"- Error: {section['error']}")
            lines.append(f"- Rows: {section['rows']}")
            flags = section["coverage"]
            lines.append(
                "- Coverage: "
                f"attacking {_yn(flags['attacking'])}, "
                f"passing {_yn(flags['passing'])}, "
                f"defensive {_yn(flags['defensive'])}, "
                f"xG {_yn(flags['xg'])}"
            )
            lines.append("- Columns with real values:")
            if section["columns"]:
                lines.extend(f"  - `{label}`" for label in section["columns"])
            else:
                lines.append("  - (none)")
            if section["sample"]:
                lines.extend(["", "```", section["sample"], "```"])

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"\nWrote {REPORT_PATH}")


def main() -> None:
    probes = [
        ("FBref", probe_fbref),
        ("FotMob", probe_fotmob),
        ("Sofascore", probe_sofascore),
        ("WhoScored", probe_whoscored),
        ("Understat", probe_understat),
    ]
    results = []
    for name, probe in probes:
        print(f"\nProbing {name}...")
        try:
            result = probe()
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            result = _failure(name, exc)
        print_result(result)
        results.append(result)
    write_report(results)


if __name__ == "__main__":
    main()
