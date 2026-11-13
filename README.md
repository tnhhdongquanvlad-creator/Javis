# Javis — LDPlayer Manager

Tool có giao diện để quản lý nhiều tab LDPlayer cùng lúc.

## Yêu cầu
- Windows + LDPlayer 4/9
- Python 3.8+ (tick "Add Python to PATH" khi cài). Không cần cài thêm thư viện.
- Trong mỗi tab giả lập nên cài sẵn Chrome. Nếu chưa có, link sẽ mở bằng trình duyệt mặc định.

## Tải bản exe

Vào mục **Releases** của repo, tải `Javis.exe` rồi chạy luôn, không cần cài Python.
`config.json` sẽ được tạo cạnh file exe.

## Chạy từ mã nguồn

```bash
python ld_manager.py
```

## Cách dùng
1. **Thư mục LDPlayer**: trỏ tới thư mục chứa `ldconsole.exe` (mặc định LD4: `C:\LDPlayer\LDPlayer4.0`), bấm **Lưu**.
2. Chọn tab trong danh sách (giữ **Ctrl/Shift** để chọn nhiều, hoặc bấm **Chọn tất cả**).
3. **Bật / Tắt / Khởi động lại / Xếp cửa sổ** các tab đã chọn.
4. **Mở Chrome**: mở app Chrome trên các tab đã chọn.
5. **Mở link**: nhập link (hoặc chọn link đã lưu), bấm **Mở link trên tab đã chọn**.
   - **Lưu link** / **Xóa link**: quản lý danh sách link hay dùng (lưu ở `config.json`).

Lưu ý: tab phải đang chạy (Android đã khởi động xong) thì mới mở được Chrome hoặc link.
