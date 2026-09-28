---
name: mod-notifications
description: >-
  Dùng Mod CLI để gửi thông báo đúng cách qua Windows Toast và hệ thống `mod notify`
  (ntfy/Telegram/Toast), đặc biệt khi cần gửi đồng thời thông báo desktop và remote/mobile
  sau khi AI Agent hoàn thành, thất bại hoặc cần người dùng chú ý tới một tác vụ.
---

# Mod Notifications Skill

Skill này hướng dẫn AI Agent sử dụng **Mod CLI (`mod`)** để gửi thông báo một cách chính xác, ít gây phiền và không nhầm lẫn giữa hai cơ chế:

- `mod toast`: Windows desktop Toast Notification, có hỗ trợ âm thanh.
- `mod notify`: facade đa kênh, hỗ trợ `ntfy`, `telegram`, `toast`; mặc định là `ntfy`.

## 1. Khi nào sử dụng skill này

Sử dụng khi người dùng yêu cầu một trong các ý sau:

- thông báo khi tác vụ hoàn thành;
- thông báo khi tác vụ thất bại;
- gửi thông báo lên desktop Windows;
- gửi thông báo tới điện thoại/remote qua ntfy;
- gửi thông báo qua Telegram;
- gửi **cả Toast và Notify** cho cùng một sự kiện;
- kiểm tra hoặc chẩn đoán hệ thống notification của Mod CLI.

Không tự động gửi notification cho mọi thao tác nhỏ. Chỉ gửi khi người dùng yêu cầu, workflow hiện tại đã quy định phải thông báo, hoặc tác vụ đủ dài/quan trọng để notification có ích.

---

## 2. Mô hình cần ghi nhớ

```text
mod toast
  └── Windows Toast desktop
      └── BurntToast + WinMM custom audio

mod notify send
  ├── ntfy      <- mặc định; remote/mobile
  ├── telegram  <- cần TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
  └── toast     <- cũng route về Windows Toast
```

### Quy tắc quan trọng nhất khi gửi cả hai

Khi người dùng muốn **Toast + Notify cùng lúc**, mặc định hãy gửi:

```text
1. mod toast ...
2. mod notify send ...
```

Trong đó lần `mod notify send` mặc định đi qua **ntfy**.

**Không** dùng cặp sau để biểu diễn desktop + remote:

```text
mod toast ...
mod notify send ... --channel toast
```

Vì cả hai lệnh trên đều gửi về Windows Toast và không tạo remote/mobile notification.

Nếu người dùng chỉ rõ Telegram, dùng:

```text
mod toast ...
mod notify send ... --channel telegram
```

---

## 3. Cú pháp chuẩn được phép dùng

### 3.1 Windows Toast

```text
mod toast "<title>" "<message>" [--audio <path-or-sound>]
```

Ví dụ:

```text
mod toast "Build hoàn tất" "Project đã build thành công."
```

Tắt âm:

```text
mod toast "Build hoàn tất" "Project đã build thành công." --audio none
```

Dùng system sound:

```text
mod toast "Cần chú ý" "Tác vụ cần bạn kiểm tra." --audio reminder
```

Dùng audio file:

```text
mod toast "Hoàn tất" "Tác vụ đã xong." --audio "D:/sounds/done.mp3"
```

Nếu không truyền `--audio`, Mod CLI dùng audio mặc định của project.

`mod toast` chỉ phù hợp trên Windows và phụ thuộc PowerShell module `BurntToast`.

### 3.2 Notify

Public actions hợp lệ qua dispatcher hiện tại:

```text
mod notify send
mod notify test
mod notify channels
mod notify config
```

Gửi qua ntfy mặc định:

```text
mod notify send "<message>" --title "<title>"
```

Gửi ntfy với metadata:

```text
mod notify send "<message>" --title "<title>" --channel ntfy --priority high --tags tada --url "https://example.com" --topic "custom-topic"
```

Gửi Telegram:

```text
mod notify send "<message>" --title "<title>" --channel telegram
```

Gửi Toast thông qua abstraction `notify`:

```text
mod notify send "<message>" --title "<title>" --channel toast
```

Chỉ dùng `--channel toast` khi người dùng muốn đi qua API `notify`; không dùng nó như remote notification thứ hai trong workflow Toast + Notify.

---

## 4. Workflow chuẩn cho AI Agent

### A. Người dùng yêu cầu "thông báo khi xong" nhưng không chỉ rõ kênh

Nếu ngữ cảnh cho thấy họ đang dùng notification của Mod CLI nói chung, ưu tiên remote/mobile bằng ntfy:

```text
mod notify send "<kết quả ngắn gọn>" --title "<tên tác vụ> hoàn tất"
```

Nếu ngữ cảnh đang nói riêng về desktop, dùng `mod toast`.

### B. Người dùng yêu cầu "Toast và Notify", "cả desktop và điện thoại", hoặc tương đương

Luôn thực hiện **hai lần gửi độc lập**:

```text
mod toast "<title>" "<message>"
mod notify send "<message>" --title "<title>"
```

Hai lệnh là best-effort độc lập. **Nếu lệnh đầu thất bại vẫn phải thử lệnh thứ hai.** Không dùng shell chaining kiểu `&&` làm lần gửi thứ hai bị bỏ qua khi lần đầu lỗi.

### C. Người dùng yêu cầu Toast + Telegram

```text
mod toast "<title>" "<message>"
mod notify send "<message>" --title "<title>" --channel telegram
```

### D. Khi tác vụ thất bại

Notification phải nói rõ tác vụ thất bại nhưng ngắn gọn, không dump stack trace dài vào notification.

Ví dụ:

```text
mod toast "Build thất bại" "Build project không thành công. Xem terminal để biết chi tiết."
mod notify send "Build project không thành công. Xem terminal để biết chi tiết." --title "Build thất bại" --priority high --tags warning
```

Chỉ dùng `urgent` khi sự kiện thực sự khẩn cấp theo yêu cầu/ngữ cảnh; không tự nâng mọi lỗi lên urgent.

### E. Khi cần người dùng quay lại tương tác

Ví dụ tác vụ đã chạy tới bước cần input:

```text
mod toast "Cần bạn xác nhận" "Tác vụ đang chờ lựa chọn trong terminal."
mod notify send "Tác vụ đang chờ lựa chọn trong terminal." --title "Cần bạn xác nhận" --priority high
```

---

## 5. Quy tắc nội dung notification

1. **Title ngắn:** thường 2-8 từ, mô tả trạng thái hoặc tên tác vụ.
2. **Message ngắn:** ưu tiên một câu cho biết chuyện gì đã xảy ra và người dùng có cần hành động hay không.
3. Không nhét log dài, stack trace, diff, JSON lớn hoặc output nhiều dòng vào notification.
4. Không gửi secret, token, password, API key, cookie hoặc dữ liệu nhạy cảm vào notification.
5. Với cùng một sự kiện gửi Toast + Notify, giữ title/message nhất quán trừ khi có lý do cần rút gọn riêng cho desktop.
6. Với nội dung động được đưa qua shell, luôn quote title/message đúng cách. Ưu tiên mỗi `message` là **một argument được quote** thay vì tách thành nhiều positional argument.
7. Với Telegram, ưu tiên plain text. Backend hiện dùng `parse_mode=HTML`, vì vậy tránh chủ động chèn HTML không cần thiết vào title/message.

---

## 6. Khác biệt tham số giữa Toast và Notify

### `mod toast`

Hỗ trợ:

- title;
- một hoặc nhiều message text;
- `--audio`;
- system sound;
- custom audio file;
- silent audio (`none`, `silent`, `off`, ...).

### `mod notify send`

Hỗ trợ public flags:

- `--channel` / `-c`;
- `--title` / `-t`;
- `--topic`;
- `--priority` / `-p`;
- `--tags` / `--tag`;
- `--url` / `--link`.

**Không truyền `--audio` vào `mod notify send`.** Public CLI hiện không parse flag này. Nếu cần kiểm soát audio desktop, dùng `mod toast` trực tiếp.

Metadata `topic`, `priority`, `tags`, `url` có ý nghĩa đầy đủ nhất với `ntfy`. Telegram và Toast có thể bỏ qua các metadata không hỗ trợ.

---

## 7. Kênh Notify

### ntfy

Là channel mặc định.

```text
mod notify send "Done" --title "Task complete"
```

Tương đương về channel với:

```text
mod notify send "Done" --title "Task complete" --channel ntfy
```

Có thể dùng:

```text
--priority min|low|default|high|urgent
--tags tag1,tag2
--topic <topic>
--url <click-url>
```

Không truyền priority tùy ý. Implementation hiện fallback priority không nhận diện được về `default`, vì vậy Agent phải chỉ dùng các giá trị chuẩn phía trên.

### telegram

Yêu cầu `.env` có:

```text
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Nếu chưa cấu hình, lệnh gửi sẽ thất bại. Không tự yêu cầu hoặc hiển thị token trong notification.

### toast

```text
mod notify send "Done" --title "Task complete" --channel toast
```

Backend này reuse ToastNotifier nhưng public `mod notify send` không có `--audio`; dùng audio mặc định.

---

## 8. Diagnostics và kiểm tra

Không chạy diagnostics trước mỗi notification. Chỉ dùng khi người dùng yêu cầu kiểm tra hoặc khi notification vừa thất bại.

Xem các channel:

```text
mod notify channels
```

Xem hướng dẫn cấu hình:

```text
mod notify config
```

Test ntfy:

```text
mod notify test --channel ntfy
```

Test Telegram:

```text
mod notify test --channel telegram
```

Test Toast thông qua notify:

```text
mod notify test --channel toast
```

Lưu ý: `mod notify channels` chỉ phản ánh cấu hình theo implementation hiện tại; trạng thái "Sẵn sàng" của `toast` không chứng minh chắc chắn module PowerShell BurntToast đã được cài hoặc runtime thực sự hoạt động.

---

## 9. Không dùng các alias nội bộ qua public CLI

`notify_cli.py` có một số alias nội bộ, nhưng dispatcher `src/main.py` hiện chỉ chấp nhận bốn action chính thức.

Vì vậy Agent **chỉ dùng**:

```text
send
test
channels
config
```

Không dùng qua lệnh `mod`:

```text
ping
ls
list
guide
env
```

Không gọi:

```text
mod notify --syntax
```

Nếu thực sự cần syntax có thể dùng:

```text
mod notify send --syntax
```

nhưng thông thường không cần gọi syntax trong workflow notification.

---

## 10. Error handling bắt buộc

Khi gửi dual notification:

1. Gửi Toast.
2. Ghi nhận exit code/kết quả.
3. **Dù Toast thành công hay thất bại, vẫn gửi Notify.**
4. Ghi nhận kết quả Notify.
5. Không lặp lại vô hạn khi một kênh lỗi.
6. Nếu cả hai lỗi, báo lỗi trong terminal/output chính của Agent; không retry spam trừ khi người dùng yêu cầu.

Không dùng:

```text
mod toast ... && mod notify send ...
```

vì lần Notify sẽ không chạy nếu Toast trả exit code khác 0.

Nếu execution environment cho phép, ưu tiên hai tool/shell calls độc lập. Nếu buộc chạy trong cùng script, phải bảo đảm lệnh thứ hai vẫn chạy sau lỗi của lệnh thứ nhất.

---

## 11. Recipes chuẩn

### Hoàn thành tác vụ — Desktop + ntfy

```text
mod toast "Tác vụ hoàn tất" "Đã xử lý xong dữ liệu."
mod notify send "Đã xử lý xong dữ liệu." --title "Tác vụ hoàn tất" --priority default --tags tada
```

### Hoàn thành tác vụ — Desktop silent + ntfy

```text
mod toast "Tác vụ hoàn tất" "Đã xử lý xong dữ liệu." --audio none
mod notify send "Đã xử lý xong dữ liệu." --title "Tác vụ hoàn tất"
```

### Lỗi — Desktop + ntfy

```text
mod toast "Tác vụ thất bại" "Không thể hoàn tất. Xem terminal để biết chi tiết."
mod notify send "Không thể hoàn tất. Xem terminal để biết chi tiết." --title "Tác vụ thất bại" --priority high --tags warning
```

### Desktop + Telegram

```text
mod toast "Deploy hoàn tất" "Website đã deploy thành công."
mod notify send "Website đã deploy thành công." --title "Deploy hoàn tất" --channel telegram
```

### Chỉ desktop

```text
mod toast "Hoàn tất" "Tác vụ đã xong."
```

### Chỉ mobile/remote mặc định

```text
mod notify send "Tác vụ đã xong." --title "Hoàn tất"
```

---

## 12. Decision table

| Ý định | Lệnh nên dùng |
|---|---|
| Chỉ desktop Windows | `mod toast` |
| Chỉ remote/mobile, không chỉ rõ channel | `mod notify send` (ntfy mặc định) |
| Chỉ ntfy | `mod notify send --channel ntfy` |
| Chỉ Telegram | `mod notify send --channel telegram` |
| Đi qua Notify abstraction nhưng hiển thị desktop | `mod notify send --channel toast` |
| Desktop + mobile | `mod toast` + `mod notify send` |
| Desktop + Telegram | `mod toast` + `mod notify send --channel telegram` |
| Cần custom/silent audio desktop | dùng `mod toast --audio ...` |

---

## 13. Nguyên tắc ưu tiên cuối cùng

Khi có xung đột giữa ví dụ trong skill và yêu cầu cụ thể của người dùng:

1. Tuân theo yêu cầu rõ ràng của người dùng về channel, audio, title, message và mức độ ưu tiên.
2. Chỉ dùng cú pháp mà public Mod CLI hiện hỗ trợ.
3. Với dual notification, bảo toàn hai đích độc lập: **desktop Toast + remote Notify**.
4. Nếu một kênh thất bại, vẫn thử kênh còn lại và báo kết quả trung thực.
