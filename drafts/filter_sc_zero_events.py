#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import glob

# ====== НАСТРОЙКИ ======
INPUT_DIR = "./input_data"    # папка с исходными B######.txt
OUTPUT_DIR = "./output_data"  # папка для отфильтрованных файлов
FILES_PATTERN = r"B[0-9]{6}\.txt$"

ZERO_THRESHOLD = 0.60  # 60%
# =======================


def split_events(text: str):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    parts = re.split(r"(?m)^\s*#\s*$", text)
    return [p.strip("\n") for p in parts if p.strip()]


def parse_numbers_from_sc_line(line: str):
    _, rhs = line.split(":", 1)
    nums = re.findall(r"-?\d+", rhs)
    return [int(x) for x in nums]


def zero_fraction(nums):
    if not nums:
        return 1.0
    return sum(1 for x in nums if x == 0) / len(nums)


def should_keep_event(event_block: str) -> bool:
    sc_h = None
    sc_l = None

    for raw in event_block.splitlines():
        s = raw.strip()
        if s.startswith("Sc-H:"):
            sc_h = parse_numbers_from_sc_line(s)
        elif s.startswith("Sc-L:"):
            sc_l = parse_numbers_from_sc_line(s)

    if sc_h is None or sc_l is None:
        return False
    if zero_fraction(sc_h) >= ZERO_THRESHOLD:
        return False
    if zero_fraction(sc_l) >= ZERO_THRESHOLD:
        return False

    return True


def main():
    if not os.path.isdir(INPUT_DIR):
        raise FileNotFoundError(f"Не найдена папка INPUT_DIR: {INPUT_DIR}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.txt")))
    files = [f for f in files if re.search(FILES_PATTERN, os.path.basename(f))]

    if not files:
        print(f"В папке {INPUT_DIR} нет файлов вида B######.txt")
        return

    for fp in files:
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        events = split_events(text)

        kept_blocks = []
        kept_count = 0
        for ev in events:
            if should_keep_event(ev):
                kept_blocks.append(ev.rstrip() + "\n#\n")
                kept_count += 1

        out_path = os.path.join(OUTPUT_DIR, os.path.basename(fp))
        with open(out_path, "w", encoding="utf-8") as out:
            out.writelines(kept_blocks)

        print(f"{os.path.basename(fp)}: всего={len(events)}, оставлено={kept_count} -> {out_path}")


if __name__ == "__main__":
    main()
