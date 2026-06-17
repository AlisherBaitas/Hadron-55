import os

# Укажите свои пути перед запуском
input_dir = "./input_data"
output_dir = "./output_data"
os.makedirs(output_dir, exist_ok=True)

ZERO_RATIO_THRESHOLD = 0.7

SCINTI_HIGH = "scinti : high sensitivity :"
SCINTI_MIDI = "scinti : midi sensitivity :"


def parse_numbers_from_line(line):
    parts = line.split(":")
    if len(parts) < 3:
        return []
    return [
        int(x)
        for x in parts[2].strip().split()
        if x.strip().lstrip("-").isdigit()
    ]


def zero_ratio(numbers):
    if not numbers:
        return 0
    return numbers.count(0) / len(numbers)


def should_drop_event(block):
    high_is_zero = False
    midi_is_zero = False

    for line in block:
        line_clean = line.strip()
        if line_clean.startswith(SCINTI_HIGH):
            numbers = parse_numbers_from_line(line_clean)
            if zero_ratio(numbers) >= ZERO_RATIO_THRESHOLD:
                high_is_zero = True
        elif line_clean.startswith(SCINTI_MIDI):
            numbers = parse_numbers_from_line(line_clean)
            if zero_ratio(numbers) >= ZERO_RATIO_THRESHOLD:
                midi_is_zero = True

    return high_is_zero and midi_is_zero


def split_events(lines):
    blocks = []
    current_block = []
    inside_event = False

    for line in lines:
        if line.startswith("|EVENT"):
            inside_event = True
            current_block = [line]
        elif line.strip() == "#" and inside_event:
            current_block.append(line)
            blocks.append(current_block)
            inside_event = False
        elif inside_event:
            current_block.append(line)

    return blocks


input_files = [
    f for f in os.listdir(input_dir)
    if f.endswith(".dat") and f[:-4].isdigit() and len(f[:-4]) == 6
]

for filename in input_files:
    input_path = os.path.join(input_dir, filename)
    output_path = os.path.join(output_dir, filename)

    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    blocks = split_events(lines)
    kept_blocks = []
    dropped_count = 0

    for block in blocks:
        if should_drop_event(block):
            dropped_count += 1
            continue
        kept_blocks.append(block)

    with open(output_path, "w", encoding="utf-8") as out_f:
        for block in kept_blocks:
            out_f.writelines(block)

    print(f"{filename}: всего={len(blocks)}, удалено={dropped_count}, сохранено={len(kept_blocks)}")

print(f"✅ Фильтрация завершена. Результаты в {output_dir}")
