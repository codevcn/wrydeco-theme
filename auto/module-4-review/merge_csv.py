import csv
import sys
import os
import glob
import shutil

# Set stdout encoding for Windows terminal
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# =====================================================================
# KHAI BÁO THƯ MỤC VÀ FILE ĐẦU RA (Bạn có thể tùy chỉnh tại đây)
# =====================================================================
# Thư mục chứa các file CSV cần hợp nhất
INPUT_FOLDER = r"output"

# File output sau khi gộp toàn bộ
OUTPUT_CSV = r"output/merged-reviews.csv"

# Thư mục lưu trữ (warehouse) để chuyển các file CSV gốc sau khi hợp nhất
WAREHOUSE_FOLDER = r"warehouse"
# =====================================================================

def merge_csv_in_folder(folder_path, output_file, warehouse_dir):
    print("=" * 60)
    print("🚀 BẮT ĐẦU HỢP NHẤT FILE CSV VÀ CHUYỂN VÀO WAREHOUSE")
    print(f"📁 Thư mục nguồn: {folder_path}")
    print(f"📦 Thư mục lưu trữ (Warehouse): {warehouse_dir}")
    print("=" * 60)
    
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        print(f"❌ Lỗi: Thư mục nguồn không tồn tại tại đường dẫn: {folder_path}")
        return

    # Lấy danh sách tất cả các file .csv trong folder
    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
    
    # Chuẩn hóa đường dẫn file output để tránh gộp chính file output
    output_file_abs = os.path.abspath(output_file)
    csv_files = [f for f in csv_files if os.path.abspath(f) != output_file_abs]

    if not csv_files:
        print(f"⚠️ Không tìm thấy file CSV nào cần hợp nhất trong thư mục: {folder_path}")
        return

    print(f"🔍 Tìm thấy {len(csv_files)} file CSV cần xử lý:\n")

    all_rows = []
    fieldnames = []
    total_files_read = 0

    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    fieldnames = reader.fieldnames
                rows = list(reader)
                all_rows.extend(rows)
                print(f"  [0] 📄 Đã giữ lại dữ liệu từ: {os.path.basename(output_file)} -> {len(rows)} dòng")
        except Exception as e:
            print(f"  ❌ Lỗi khi đọc dữ liệu cũ từ {os.path.basename(output_file)}: {e}")

    for idx, file_path in enumerate(sorted(csv_files), 1):
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if not fieldnames and reader.fieldnames:
                    fieldnames = reader.fieldnames
                rows = list(reader)
                all_rows.extend(rows)
                total_files_read += 1
                print(f"  [{idx}] 📄 Đã đọc: {os.path.basename(file_path)} -> {len(rows)} dòng")
        except Exception as e:
            print(f"  [{idx}] ❌ Lỗi khi đọc file {os.path.basename(file_path)}: {e}")

    if not all_rows:
        print("\n⚠️ Không có dữ liệu nào được đọc từ các file CSV.")
        return

    # Đảm bảo thư mục output tồn tại
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)

    # Ghi toàn bộ dữ liệu ra file mới
    with open(output_file, "w", encoding="utf-8", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print("-" * 60)
    print(f"✅ Hợp nhất thành công {total_files_read} file ({len(all_rows)} dòng dữ liệu) vào file:")
    print(f"👉 {output_file}")
    print("-" * 60)

    # Đảm bảo thư mục warehouse tồn tại
    os.makedirs(warehouse_dir, exist_ok=True)
    print(f"🚚 Đang chuyển {len(csv_files)} file CSV gốc sang thư mục '{warehouse_dir}'...")

    moved_count = 0
    for file_path in csv_files:
        try:
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(warehouse_dir, file_name)
            # Nếu file cũ đã tồn tại trong warehouse thì xóa đi để ghi đè an toàn trên Windows
            if os.path.exists(dest_path):
                os.remove(dest_path)
            shutil.move(file_path, dest_path)
            moved_count += 1
            print(f"  📦 Đã chuyển: {file_name} -> {warehouse_dir}/")
        except Exception as e:
            print(f"  ❌ Lỗi khi chuyển file {file_name}: {e}")

    print("=" * 60)
    print(f"🎉 HOÀN TẤT! Trong folder '{folder_path}' hiện chỉ giữ lại file:")
    print(f"👉 {os.path.basename(output_file)}")
    print("=" * 60)

if __name__ == "__main__":
    merge_csv_in_folder(INPUT_FOLDER, OUTPUT_CSV, WAREHOUSE_FOLDER)
