"""
서울과학기술대학교 수강신청시스템 시간표 원본 데이터 수집 스크립트.

시간표조회 화면(https://for-s.seoultech.ac.kr/html/pub/schedule.jsp)이 내부적으로 호출하는
JSON API(JSONMain, fsp_cmd=getScheduleGridData)를 그대로 호출해서, 학과 필터 없이
해당 학기 전체 강의 데이터를 한 번에 받아온다.

이 스크립트는 "크롤링" 단계만 담당한다: 받아온 응답을 가공하지 않고 그대로 파일로 저장한다.
LSTM_LIST(강의시간, 예: "월(3 ~ 4), 화(1)")를 요일/교시로 쪼개는 전처리는 다음 단계 스크립트에서 한다.

사용 예:
    python fetch_schedule_raw.py --year 2026 --semester 2
    python fetch_schedule_raw.py --year 2026 --semester 2 --out-dir data/raw

필요 패키지:
    pip install requests
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://for-s.seoultech.ac.kr"
SCHEDULE_PAGE_URL = f"{BASE_URL}/html/pub/schedule.jsp"
API_URL = f"{BASE_URL}/JSONMain"

SEMESTER_NAMES = {1: "1학기", 2: "2학기", 3: "여름학기", 4: "겨울학기"}

# 화면의 '주야' 콤보박스 값. 비워두면(=None) 주간/야간 전체가 함께 내려온다.
DN_DIV_CODES = {
    "all": "",
    "day": "00500001",
    "night": "00500002",
}


def build_sp_ymst(year: int, semester: int) -> str:
    """년도 + 학기코드를 API가 쓰는 SP_YMST 형식으로 합친다. 예: 2026, 2 -> '20262'."""
    if semester not in SEMESTER_NAMES:
        raise ValueError(f"semester는 1~4만 가능합니다 (입력값: {semester})")
    return f"{year}{semester}"


def fetch_schedule(sp_ymst: str, dn_div: str = "") -> dict:
    """전체 학과, 전체 요일 기준으로 해당 학기 시간표 데이터를 한 번에 받아온다."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
        }
    )

    # JSONMain이 세션 쿠키를 요구하는 경우를 대비해, 먼저 조회 화면을 한 번 열어 세션을 만든다.
    session.get(SCHEDULE_PAGE_URL, timeout=15)

    payload = {
        "fsp_action": "GridAction",
        "fsp_cmd": "getScheduleGridData",
        "SP_YMST": sp_ymst,
        "LESS_CD": "",     # 학과 코드. 비우면 전체 학과.
        "DN_DIV": dn_div,  # 주간/야간. 비우면 전체.
        "SUBJ_NM": "",
        "LECT_DIV": "",
        "DOTW_CD": "",     # 요일. 비우면 전체 요일.
    }
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Referer": SCHEDULE_PAGE_URL,
        "Origin": BASE_URL,
    }

    response = session.post(API_URL, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    if data.get("ErrorCode") != "0":
        raise RuntimeError(f"API 오류 응답: {data.get('ErrorMsg')} (code={data.get('ErrorCode')})")

    return data


def save_raw(data: dict, out_dir: Path, sp_ymst: str, year: int, semester: int, dn_div_key: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"schedule_raw_{sp_ymst}.json"

    wrapped = {
        "meta": {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "year": year,
            "semester": semester,
            "semester_name": SEMESTER_NAMES[semester],
            "sp_ymst": sp_ymst,
            "dn_div": dn_div_key,
            "source_api": API_URL,
            "record_count": data.get("records"),
        },
        "response": data,
    }

    out_path.write_text(json.dumps(wrapped, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True, help="예: 2026")
    parser.add_argument(
        "--semester",
        type=int,
        required=True,
        choices=sorted(SEMESTER_NAMES.keys()),
        help="1=1학기, 2=2학기, 3=여름학기, 4=겨울학기",
    )
    parser.add_argument(
        "--daynight",
        choices=sorted(DN_DIV_CODES.keys()),
        default="all",
        help="주간/야간 필터 (기본값: all = 전체)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/raw"),
        help="원본 JSON을 저장할 디렉토리 (기본값: data/raw)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sp_ymst = build_sp_ymst(args.year, args.semester)
    dn_div = DN_DIV_CODES[args.daynight]

    print(f"[fetch] {args.year}년 {SEMESTER_NAMES[args.semester]} (SP_YMST={sp_ymst}) 시간표 요청 중...")
    try:
        data = fetch_schedule(sp_ymst, dn_div)
    except requests.RequestException as e:
        print(f"[error] 요청 실패: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1

    record_count = data.get("records")
    print(f"[fetch] 완료: {record_count}건 수신")

    out_path = save_raw(data, args.out_dir, sp_ymst, args.year, args.semester, args.daynight)
    print(f"[save] 원본 저장 완료: {out_path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
