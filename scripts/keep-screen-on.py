import ctypes
import time

# Windows execution state flags
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


def prevent_sleep() -> None:
    result = ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    )

    if result == 0:
        raise ctypes.WinError()


def restore_sleep_settings() -> None:
    result = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

    if result == 0:
        raise ctypes.WinError()


def main() -> None:
    try:
        prevent_sleep()
        print("Đang ngăn Windows sleep và tắt màn hình.")
        print("Nhấn Ctrl + C để dừng.")

        while True:
            time.sleep(60)

    except KeyboardInterrupt:
        print("\nĐang khôi phục cài đặt sleep của Windows...")

    finally:
        restore_sleep_settings()
        print("Đã cho phép Windows sleep trở lại.")


if __name__ == "__main__":
    main()