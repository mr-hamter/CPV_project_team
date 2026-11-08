# Nhập chữ bằng cử chỉ tay (CPV)

Dùng webcam + MediaPipe Hands để nhận diện bàn tay, người dùng chạm ngón cái vào các ngón khác để nhập mã 1/2, sau đó chương trình đổi mã thành chữ và đọc bằng loa.

## Cài đặt và chạy

Trên Windows, nhấp đúp **`CHAY_CHUONG_TRINH.cmd`** trong thư mục dự án để chạy.
File này tự chuyển về đúng thư mục và bao đường dẫn bằng một cặp dấu nháy,
tránh lỗi `[Errno 22] Invalid argument` khi tên thư mục có dấu cách.

Trong VS Code, mở thư mục dự án rồi nhấn **F5**, chọn **Chạy nhận diện cử chỉ tay**.
Cấu hình chạy theo module nên không phải ghép đường dẫn file vào lệnh PowerShell.

Hoặc chạy trong Terminal:

```
pip install -r requirements.txt
python -X utf8 dieu_khien_cu_chi_tay.py
```

Tùy chọn: `--camera 1` (chọn camera khác), `--threshold 0.3` (ngưỡng chạm, mặc định 0.28).

## Cách dùng

Chỉ đưa **một** bàn tay vào camera (trái hay phải đều được), mở tay ra trước khi thao tác.

| Cử chỉ | Tác dụng |
|---|---|
| Ngón cái chạm đầu ngón trỏ | thêm dấu `1` |
| Ngón cái chạm đầu ngón giữa | thêm dấu `2` |
| Ngón cái chạm đầu ngón áp út | xác nhận mã → ra chữ |
| Ngón cái chạm đầu ngón út | đọc văn bản qua loa và lưu vào lịch sử |
| Vuốt ngón cái trên lòng bàn tay, từ gốc ngón trỏ sang gốc ngón út | dấu cách |
| Nắm tay rồi mở ra | xóa dấu cuối của mã đang nhập |

Mỗi lần chạm phải giữ khoảng 0,1 giây rồi tách ra mới được tính. Vuốt phải xong trong 1 giây và phải vuốt đúng chiều trỏ → út. Nếu mã còn đang nhập dở thì vuốt cách sẽ báo lỗi, cần xác nhận hoặc xóa mã trước.

## Bảng mã

Mã ngắn được dùng trước: A=`1`, B=`2`, C=`11`, D=`12`, E=`21`, F=`22`, G=`111` … N=`222`, O=`1111` … Z=`2122`. Mã `2211` = xóa chữ cuối trong văn bản. Bảng mã đầy đủ hiện trong cửa sổ chương trình.

Vì `1` (A) cũng là phần đầu của `11` (C) nên phải chạm ngón áp út để xác nhận.

## Cấu trúc code

- `camera.py`: luồng riêng đọc camera, lật ảnh, chạy MediaPipe, vẽ khung xương tay.
- `gesture.py`: từ 21 điểm của bàn tay tính ra lệnh (chạm ngón, nắm tay, vuốt lòng bàn tay).
- `contact.py`: kiểm tra một lần chạm (giữ đủ lâu rồi tách ra).
- `codebook.py`: bảng mã 1/2 và xử lý mã đang nhập.
- `recognizer.py`, `ui.py`: phần điều khiển và giao diện Tkinter.
- `dataset.py`, `speech.py`, `evaluation.py`: lưu phiên, đọc loa, tính kết quả đo thử.

Phát hiện vuốt: chiếu đầu ngón cái (điểm 4) lên đường nối gốc ngón trỏ (điểm 5) và gốc ngón út (điểm 17). Được `u = 0` ở gốc ngón trỏ, `u = 1` ở gốc ngón út, `v` là khoảng cách tới đường đó (chia cho độ rộng bàn tay). Khi ngón cái nằm trên lòng bàn tay mà `u` đi từ dưới 0,25 lên trên 0,8 trong vòng 1 giây thì tính là một dấu cách.

## Hiệu năng

Phần nặng nhất là MediaPipe, nên phần này chạy trên luồng riêng cùng với việc đọc camera. Giao diện cứ 15 ms lấy kết quả mới nhất một lần và chỉ dán ảnh vào `PhotoImage` có sẵn, không tạo lại widget hay vẽ lại cả cửa sổ, nên hình không còn bị giật.

## Đo thử và đánh giá

Menu **Đo thử → Bắt đầu đo...**: nhập chữ cần thử (để trống nếu muốn thử trường hợp không chạm) và điều kiện ánh sáng/góc quay, thực hiện cử chỉ rồi chọn **Kết thúc đo**. Kết quả được ghi vào `data/trials.csv`.

Tính độ chính xác và confusion matrix: `python dieu_khien_cu_chi_tay.py --report data/trials.csv`.

## Kiểm thử

```
python -m unittest discover -s tests -v
python tests/smoke_gui.py
```

Các test dùng tọa độ tay giả lập, nên vẫn cần thử với camera thật để chỉnh ngưỡng cho phù hợp.
