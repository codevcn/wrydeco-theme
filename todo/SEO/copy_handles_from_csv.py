import csv
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print('Usage: python copy_handles_from_csv.py "path\\to\\file.csv"', file=sys.stderr)
        return 1

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"File not found: {csv_path}", file=sys.stderr)
        return 1

    handles = []
    seen = set()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or "Handle" not in reader.fieldnames:
            print('CSV must contain a "Handle" column.', file=sys.stderr)
            return 1

        for row in reader:
            handle = (row.get("Handle") or "").strip()
            if handle and handle not in seen:
                seen.add(handle)
                handles.append(handle)

    output = ",".join(handles)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
