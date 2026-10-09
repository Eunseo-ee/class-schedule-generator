import json, collections, sys

path = sys.argv[1]  # 실행할 때 JSON 경로를 인자로 받음
d = json.load(open(path, encoding="utf-8"))
courses, slots = d["courses"], d["time_slots"]
keys = [(c["subj_cd"], c["lect_numb"]) for c in courses]
slot_keys = {(s["subj_cd"], s["lect_numb"]) for s in slots}

print("meta.record_count:", d["meta"]["record_count"], "/ courses:", len(courses))
print("중복 키:", [k for k, n in collections.Counter(keys).items() if n > 1][:10])
print("강의 없는 슬롯:", slot_keys - set(keys))
print("time_status:", collections.Counter(c["time_status"] for c in courses))
print("슬롯 없는 강의 수:", sum(1 for k in keys if k not in slot_keys))
print("슬롯 중복:", [k for k, n in collections.Counter(
    (s["subj_cd"], s["lect_numb"], s["day"], s["start_slot"]) for s in slots).items() if n > 1][:10])
print("max end_slot:", max(s["end_slot"] for s in slots),
      "/ start>=end:", [s for s in slots if s["start_slot"] >= s["end_slot"]][:5])