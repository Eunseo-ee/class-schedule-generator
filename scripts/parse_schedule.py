"""
크롤링한 시간표 원본 JSON을 강의(course) + 시간 슬롯(time slot) 구조로 정규화하는 스크립트.

크롤링 단계(crawling.py)가 저장한 원본(data/raw/schedule_raw_{SP_YMST}.json)을 읽어서
LSTM_LIST(강의시간)를 요일/시간 구간으로 쪼갠다. 원본 파일은 수정하지 않는다.

LSTM_LIST 형식 예:
    "금(3 ~ 5)"                  -> 금요일 3~5교시
    "수(3 ~ 4), 목(3)"           -> 요일이 여러 개
    "월(1 ~ 3, 5 ~ 7)"           -> 한 요일에 구간이 둘
    "수(4 ~ 5A), 금(4 ~ 5A)"     -> A/B는 한 교시의 앞/뒤 절반 (30분)

시간은 "30분 단위 칸"의 정수로 저장한다. 구간은 [start, end) (end 미포함).
    N교시 = 칸 2N, 2N+1   (NA = 2N, NB = 2N+1)
    예) "4 ~ 5A" -> [8, 11),  "5B ~ 6" -> [11, 14)
이렇게 하면 두 구간이 겹치는지는 `s1 < e2 and s2 < e1` 한 줄로 판정되고,
0.5 같은 실수를 쓰지 않아 오차도 없다.

사용 예:
    python scripts/parse_schedule.py --year 2026 --semester 2

출력:
    data/parsed/schedule_parsed_{SP_YMST}.json  (courses, time_slots)
    data/parsed/parse_report_{SP_YMST}.json     (건수, 수동 보정, 경고, 실패)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DAY_CODES = {
    "월": "MON",
    "화": "TUE",
    "수": "WED",
    "목": "THU",
    "금": "FRI",
    "토": "SAT",
    "일": "SUN",
}

# 수강신청 화면에서 직접 확인한 원본 데이터 오류. 키는 (SUBJ_CD, LECT_NUMB).
# 원본 JSON은 건드리지 않고, 파싱 직전에 이 값으로 LSTM_LIST만 바꿔서 쓴다.
MANUAL_FIX: dict[tuple[str, str], str] = {
    # 공중보건학: 원본의 화요일 값("화(5A, 5A ~ 5A, ...)")은 오류, 실제로는 토요일만 있음
    ("703006", "11001"): "토(5 ~ 7)",
    # 건설환경공학: 원본의 "화(1A, 2 ~ 2)"에서 1A는 오류, 실제로는 화 2교시
    ("702045", "21001"): "화(2), 토(1 ~ 3)",
}

# "월(1 ~ 3, 5 ~ 7)" 같은 요일 한 덩어리. 괄호 안에 쉼표가 있을 수 있어서 요일 단위로 먼저 끊는다.
DAY_GROUP_RE = re.compile(r"([월화수목금토일])\(([^)]*)\)")
# 괄호 안의 구간 하나: "3", "3A", "3 ~ 5", "4 ~ 5A", "5B ~ 6"
RANGE_RE = re.compile(r"^(\d+)([AB]?)(?:\s*~\s*(\d+)([AB]?))?$")

MAX_SLOT = 31  # 0~14교시 -> 칸 0~29, 여유를 두고 상한만 검사


class TimeParseError(ValueError):
    """LSTM_LIST를 해석할 수 없을 때."""


def parse_range(text: str) -> tuple[int, int]:
    """'4 ~ 5A' 같은 구간 하나를 [start, end) 칸 번호로 바꾼다."""
    m = RANGE_RE.match(text.strip())
    if not m:
        raise TimeParseError(f"해석할 수 없는 구간: {text!r}")
    start_n, start_half, end_n, end_half = m.groups()

    start = int(start_n) * 2 + (1 if start_half == "B" else 0)
    if end_n is None:
        # 단일 표기: "3" = 한 교시 전체, "3A"/"3B" = 그 교시의 절반
        end = start + (2 if start_half == "" else 1)
    else:
        # 끝 표기: "5A"는 5교시 앞 절반까지, "5" 또는 "5B"는 5교시 끝까지
        end = int(end_n) * 2 + (1 if end_half == "A" else 2)

    if not (0 <= start < end <= MAX_SLOT):
        raise TimeParseError(f"범위가 올바르지 않음: {text!r} -> [{start}, {end})")
    return start, end


def merge_ranges(
    ranges: list[tuple[int, int]],
) -> tuple[list[tuple[int, int]], bool]:
    """같은 요일의 구간을 정렬하고, 맞닿거나 겹치는 구간을 하나로 합친다.

    반환: (병합된 구간들, 서로 '겹치는' 구간이 있었는지).
    맞닿기만 한 경우("10A, 10B ~ 11")는 정상이라 경고 대상이 아니다.
    """
    merged: list[tuple[int, int]] = []
    overlapped = False
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:
            if start < merged[-1][1]:
                overlapped = True
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged, overlapped


def parse_lstm(text: str) -> tuple[list[tuple[str, int, int]], list[str]]:
    """LSTM_LIST 문자열을 [(요일코드, start, end), ...]로 바꾼다.

    반환: (슬롯 목록, 경고 목록). 해석 불가면 TimeParseError.
    """
    groups = DAY_GROUP_RE.findall(text)
    leftover = DAY_GROUP_RE.sub("", text).strip(" ,")
    if not groups or leftover:
        raise TimeParseError(f"해석할 수 없는 형식: {text!r}")

    by_day: dict[str, list[tuple[int, int]]] = {}
    for day_kr, body in groups:
        for part in body.split(","):
            by_day.setdefault(DAY_CODES[day_kr], []).append(parse_range(part))

    warnings: list[str] = []
    slots: list[tuple[str, int, int]] = []
    for day_code in DAY_CODES.values():
        if day_code not in by_day:
            continue
        merged, overlapped = merge_ranges(by_day[day_code])
        if overlapped:
            warnings.append(f"{day_code}: 겹치는 구간을 병합함")
        slots.extend((day_code, s, e) for s, e in merged)
    return slots, warnings


def to_int(value: str | None) -> int | None:
    return int(value) if value not in (None, "") else None


def to_course(row: dict, time_status: str) -> dict:
    room = " ".join((row.get("BLDG_COUM") or "").split())
    return {
        "subj_cd": row["SUBJ_CD"],
        "lect_numb": row["LECT_NUMB"],
        "name": row["SUBJ_KNM"],
        "professor": row.get("PROF_NM"),
        "credits": to_int(row.get("UNIT")),
        "category": row.get("CMPT_DIV_NM"),
        "department": row.get("MNG_LESS_NM"),
        "capacity": to_int(row.get("COUR_INWON")),
        "room": room or None,  # 강의실은 슬롯별로 짝지을 수 없어서 강의 단위 문자열로 둔다
        "day_night": row.get("DN_DIV_NM"),
        "language": row.get("COUR_LANG"),
        "note": row.get("NOTE"),
        "time_raw": row.get("LSTM_LIST"),
        "time_status": time_status,  # parsed / manual_fix / no_time
    }


def build(rows: list[dict]) -> tuple[list[dict], list[dict], dict]:
    courses: list[dict] = []
    time_slots: list[dict] = []
    report = {
        "total": len(rows),
        "parsed": 0,
        "manual_fix": [],
        "no_time": [],
        "warnings": [],
        "failures": [],
    }

    seen_fix_keys: set[tuple[str, str]] = set()

    for row in rows:
        key = (row["SUBJ_CD"], row["LECT_NUMB"])
        label = f"{key[0]}-{key[1]} {row['SUBJ_KNM']}"
        text = row.get("LSTM_LIST")
        status = "parsed"

        if key in MANUAL_FIX:
            seen_fix_keys.add(key)
            report["manual_fix"].append(
                {"course": label, "original": text, "fixed": MANUAL_FIX[key]}
            )
            text = MANUAL_FIX[key]
            status = "manual_fix"

        if text is None:
            # 시간이 없는 강의(타대학이수과목 등). 강의는 남기되 슬롯은 만들지 않는다.
            courses.append(to_course(row, "no_time"))
            report["no_time"].append(label)
            continue

        try:
            slots, warnings = parse_lstm(text)
        except TimeParseError as e:
            # 실패한 강의는 버리지 않고 목록에 남긴다. 슬롯은 만들지 않는다.
            courses.append(to_course(row, "failed"))
            report["failures"].append({"course": label, "raw": text, "error": str(e)})
            continue

        courses.append(to_course(row, status))
        for day, start, end in slots:
            time_slots.append(
                {
                    "subj_cd": key[0],
                    "lect_numb": key[1],
                    "day": day,
                    "start_slot": start,
                    "end_slot": end,
                }
            )
        for w in warnings:
            report["warnings"].append({"course": label, "raw": text, "warning": w})
        if status == "parsed":
            report["parsed"] += 1

    # 보정 대상이 원본에 없으면(다른 학기 파일 등) 조용히 넘어가지 않고 알린다.
    for key in MANUAL_FIX:
        if key not in seen_fix_keys:
            report["warnings"].append(
                {"course": f"{key[0]}-{key[1]}", "warning": "MANUAL_FIX 대상이 이 파일에 없음"}
            )

    return courses, time_slots, report


def print_report(report: dict, n_slots: int) -> None:
    print(f"[report] 전체 {report['total']}건")
    print(f"  - 파싱 성공(규칙): {report['parsed']}건")
    print(f"  - 수동 보정 후 파싱: {len(report['manual_fix'])}건")
    print(f"  - 시간 없음(슬롯 미생성): {len(report['no_time'])}건")
    print(f"  - 실패: {len(report['failures'])}건")
    print(f"  - 생성된 시간 슬롯: {n_slots}개")
    for w in report["warnings"]:
        print(f"  [warn] {w}")
    for f in report["failures"]:
        print(f"  [fail] {f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True, help="예: 2026")
    parser.add_argument("--semester", type=int, required=True, help="1~4")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/parsed"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sp_ymst = f"{args.year}{args.semester}"
    raw_path = args.raw_dir / f"schedule_raw_{sp_ymst}.json"

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    rows = raw["response"]["rows"]
    expected = raw["meta"]["record_count"]
    if len(rows) != expected:
        print(f"[error] 건수 불일치: meta={expected}, rows={len(rows)}", file=sys.stderr)
        return 1

    courses, time_slots, report = build(rows)

    # 모든 강의가 정확히 한 번씩 분류되었는지 확인한다.
    classified = (
        sum(1 for c in courses if c["time_status"] in ("parsed", "manual_fix"))
        + len(report["no_time"])
        + len(report["failures"])
    )
    if classified != len(rows) or len(courses) != len(rows):
        print(f"[error] 분류 건수 불일치: {classified} / {len(rows)}", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    parsed_path = args.out_dir / f"schedule_parsed_{sp_ymst}.json"
    report_path = args.out_dir / f"parse_report_{sp_ymst}.json"
    parsed_path.write_text(
        json.dumps(
            {"meta": raw["meta"], "courses": courses, "time_slots": time_slots},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print_report(report, len(time_slots))
    print(f"[save] {parsed_path.resolve()}")
    print(f"[save] {report_path.resolve()}")
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
