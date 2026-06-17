import os
import numpy as np

# Укажите свои пути перед запуском
input_dir = "./input_data"
output_dir = "./output_data"
os.makedirs(output_dir, exist_ok=True)

target_labels = [
    "back_1 : high sensitivity :", "back_2 : high sensitivity :", "back_3 : high sensitivity :",
    "back_g : high sensitivity :", "back_g : low sensitivity :",
    "front_1 : high sensitivity :", "front_2 : high sensitivity :", "front_3 : high sensitivity :",
    "front_g : high sensitivity :", "front_g : low sensitivity :",
    "left_1 : high sensitivity :", "left_2 : high sensitivity :", "left_3 : high sensitivity :", "left_4 : high sensitivity :",
    "left_g : high sensitivity :", "left_g : low sensitivity :",
    "middle_1 : high sensitivity :", "middle_2 : high sensitivity :", "middle_3 : high sensitivity :",
    "right_1 : high sensitivity :", "right_2 : high sensitivity :", "right_3 : high sensitivity :", "right_4 : high sensitivity :",
    "right_g : high sensitivity :", "right_g : low sensitivity :"
]

def parse_numbers_from_line(line):
    parts = line.split(":")
    if len(parts) < 3:
        return []
    return [int(x) for x in parts[2].strip().split() if x.strip().lstrip('-').isdigit()]

def replace_outliers_with_context(numbers, ratio_threshold=10, absolute_threshold=1000):
    arr = list(numbers)
    result = arr[:]
    length = len(arr)

    for i in range(length):
        current = arr[i]

        if i == 0 and length > 1:
            if abs(current) > absolute_threshold:
                result[i] = arr[i + 1]
                continue
            elif current > 0 and sum(arr[j] == 0 for j in range(1, min(5, length))) >= 2:
                result[i] = 0
                continue

        elif i == length - 1 and abs(current) > absolute_threshold:
            result[i] = arr[i - 1]
            continue

        elif 0 < i < length - 1:
            left = arr[i - 1]
            right = arr[i + 1]
            avg = (left + right) / 2
            if (current > avg * ratio_threshold and avg > 0) or current > absolute_threshold:
                result[i] = int(avg)
                continue

        left_zeros = sum(arr[j] == 0 for j in range(max(0, i - 3), i)) >= 2
        right_zeros = sum(arr[j] == 0 for j in range(i + 1, min(length, i + 4))) >= 2
        if current > 0 and left_zeros and right_zeros:
            result[i] = 0

    return result

def is_block_mostly_small_values(all_numbers, ratio_threshold=0.9):
    total = len(all_numbers)
    small = sum(1 for n in all_numbers if 0 <= n <= 7)
    return small / total >= ratio_threshold

input_files = [f for f in os.listdir(input_dir) if f.endswith(".dat") and f[:-4].isdigit() and len(f[:-4]) == 6]

for filename in input_files:
    input_path = os.path.join(input_dir, filename)
    output_path = os.path.join(output_dir, filename)

    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

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

    cleaned_blocks = []

    for block in blocks:
        if len(block) > 1 and any(word in block[1].lower() for word in ["calibr", "test"]):
            continue

        numeric_lines = [line for line in block if any(label in line for label in target_labels)]
        if len(numeric_lines) != 25:
            continue

        cleaned_lines = []
        all_block_numbers = []

        for line in numeric_lines:
            numbers = parse_numbers_from_line(line)
            numbers = replace_outliers_with_context(numbers)
            all_block_numbers.extend(numbers)

            prefix = line.split(":")[0] + " : " + line.split(":")[1] + " :"
            cleaned_lines.append(prefix + " " + " ".join(map(str, numbers)) + "\n")

        if not is_block_mostly_small_values(all_block_numbers):
            cleaned_block = []
            num_idx = 0
            for line in block:
                if any(label in line for label in target_labels):
                    cleaned_block.append(cleaned_lines[num_idx])
                    num_idx += 1
                else:
                    cleaned_block.append(line)
            cleaned_blocks.append(cleaned_block)

    with open(output_path, "w", encoding="utf-8") as out_f:
        for block in cleaned_blocks:
            out_f.writelines(block)

print(f"✅ Обработка завершена. Сохранено в {output_dir}")
