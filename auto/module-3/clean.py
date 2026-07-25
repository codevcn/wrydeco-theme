import os

main_files = [
    ".env",
    "main.py",
    "requirements.txt",
    "dev.cmd",
    "get_access_token.py",
    "get_access_token.cmd",
    "clean.py",
    "clean.cmd",
]

def clean():
    to_delete = []
    
    # Chỉ duyệt qua các file trong thư mục hiện tại, bỏ qua thư mục (như templates, __pycache__)
    for item in os.listdir("."):
        if os.path.isfile(item):
            if item not in main_files:
                to_delete.append(item)
                
    if not to_delete:
        print("Không có file thừa nào cần xóa.")
        return
        
    print("Các file thừa sẽ bị xóa:")
    for f in to_delete:
        print(f" - {f}")
        
    ans = input("\nBạn có chắc chắn muốn xóa các file này không? (y/N): ")
    if ans.lower() == 'y':
        for f in to_delete:
            try:
                os.remove(f)
                print(f"Đã xóa: {f}")
            except Exception as e:
                print(f"Lỗi khi xóa {f}: {e}")
        print("\nHoàn tất dọn dẹp!")
    else:
        print("\nĐã hủy lệnh xóa.")

if __name__ == "__main__":
    clean()
