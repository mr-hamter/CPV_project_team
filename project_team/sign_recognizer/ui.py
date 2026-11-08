"""Giao diện Tkinter: camera bên trái, bảng mã bên phải, ô văn bản bên dưới."""
import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
from .camera import WIDTH, HEIGHT
from .codebook import CODEBOOK, MAX_CODE_LENGTH, SYMBOL_CODES

MONO = ('Consolas', 11)
GUIDE = ('Chạm đầu ngón cái vào đầu ngón:\n'
         '   trỏ = 1\n'
         '   giữa = 2\n'
         '   áp út = xác nhận mã\n'
         '   út = đọc và gửi\n\n'
         'Vuốt ngón cái trên lòng bàn tay\n'
         'từ gốc ngón trỏ sang gốc ngón út\n'
         '   = dấu cách\n\n'
         'Nắm tay rồi mở ra = xóa dấu cuối của mã')


def pt(p):
    return round(p[0]), round(p[1])


class MainWindow:
    def __init__(self, root, app):
        self.root, self.app = root, app
        root.title('Nhập chữ bằng cử chỉ tay')
        self.build_menu()

        self.status = ttk.Label(root, relief='sunken', anchor='w', padding=(6, 2))
        self.status.pack(side='bottom', fill='x')
        main = ttk.Frame(root, padding=8)
        main.pack(fill='both', expand=True)

        # Ảnh camera: tạo PhotoImage một lần rồi paste khung mới vào, không tạo lại mỗi khung
        self.photo = ImageTk.PhotoImage(Image.new('RGB', (WIDTH, HEIGHT), '#202020'))
        ttk.Label(main, image=self.photo).grid(row=0, column=0, sticky='nw')

        side = ttk.Frame(main)
        side.grid(row=0, column=1, sticky='n', padx=(10, 0))
        table = ttk.LabelFrame(side, text='Bảng mã', padding=6)
        table.pack(fill='x')
        letters = [(value, code) for code, value in CODEBOOK.items() if len(value) == 1]
        for i, (char, code) in enumerate(letters):
            ttk.Label(table, text=f'{char} {code:<4}', font=MONO).grid(row=i % 9, column=i // 9, sticky='w', padx=(0, 14))
        ttk.Label(table, text=f'Xóa chữ cuối: {SYMBOL_CODES["BACKSPACE"]}', font=MONO).grid(
            row=9, column=0, columnspan=3, sticky='w', pady=(6, 0))
        guide = ttk.LabelFrame(side, text='Cách dùng', padding=6)
        guide.pack(fill='x', pady=(8, 0))
        ttk.Label(guide, text=GUIDE, justify='left').pack(anchor='w')

        row = ttk.Frame(main)
        row.grid(row=1, column=0, columnspan=2, sticky='we', pady=(8, 0))
        ttk.Label(row, text='Mã đang nhập:').pack(side='left')
        # Mỗi dấu kèm một dấu cách: "1 2 1 2" cần 2*MAX_CODE_LENGTH - 1 ký tự
        self.code = ttk.Label(row, text='-', font=('Consolas', 18, 'bold'), width=2 * MAX_CODE_LENGTH)
        self.code.pack(side='left', padx=6)
        ttk.Button(row, text='Xóa dấu cuối', command=app.delete_digit).pack(side='left')
        ttk.Button(row, text='Xóa mã', command=app.clear_code).pack(side='left', padx=4)
        self.message = ttk.Label(row, foreground='#555555')
        self.message.pack(side='left', padx=10)

        self.text = tk.Text(main, height=3, font=('Segoe UI', 15), wrap='word', undo=True)
        self.text.grid(row=2, column=0, columnspan=2, sticky='we', pady=6)
        buttons = ttk.Frame(main)
        buttons.grid(row=3, column=0, columnspan=2, sticky='w')
        ttk.Button(buttons, text='Đọc và gửi (Ctrl+Enter)', command=app.send).pack(side='left')
        ttk.Button(buttons, text='Đọc lại', command=app.read_last).pack(side='left', padx=6)
        ttk.Button(buttons, text='Xóa văn bản', command=app.clear_text).pack(side='left')

        self.text.bind('<<Modified>>', app.text_changed)
        self.text.bind('<Control-Return>', lambda e: (app.send(), 'break')[1])
        root.bind('<F2>', lambda e: app.reset_gesture())
        root.bind('<F3>', lambda e: app.toggle_pause())
        root.protocol('WM_DELETE_WINDOW', app.close)

    def build_menu(self):
        app = self.app
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label='Xuất văn bản và lịch sử...', command=app.export_text)
        file_menu.add_separator()
        file_menu.add_command(label='Thoát', command=app.close)
        camera_menu = tk.Menu(menubar, tearoff=False)
        camera_menu.add_command(label='Kết nối lại camera', command=app.open_camera)
        camera_menu.add_command(label='Đặt lại nhận diện', accelerator='F2', command=app.reset_gesture)
        camera_menu.add_command(label='Tạm dừng / tiếp tục', accelerator='F3', command=app.toggle_pause)
        trial_menu = tk.Menu(menubar, tearoff=False)
        trial_menu.add_command(label='Bắt đầu đo...', command=app.start_trial)
        trial_menu.add_command(label='Kết thúc đo', command=app.finish_trial)
        menubar.add_cascade(label='Tệp', menu=file_menu)
        menubar.add_cascade(label='Camera', menu=camera_menu)
        menubar.add_cascade(label='Đo thử', menu=trial_menu)
        self.root.config(menu=menubar)

    def draw_feedback(self, rgb, gesture):
        """Vẽ thêm lên ảnh: đường vuốt khi đang vuốt, chấm đỏ ở ngón cái khi đang chạm."""
        p = gesture.hand
        if p is None:
            return
        if gesture.swipe.started is not None:
            cv2.line(rgb, pt(p[5]), pt(p[17]), (255, 200, 0), 3)
        if gesture.target:
            cv2.circle(rgb, pt(p[4]), 9, (255, 70, 70), -1)

    def show_frame(self, rgb):
        self.photo.paste(Image.fromarray(rgb))

    def set_status(self, text):
        if self.status.cget('text') != text:
            self.status.config(text=text)

    def show_code(self, pending, message=None):
        self.code.config(text=' '.join(pending) or '-')
        if message is not None:
            self.notify(message)

    def notify(self, message):
        self.message.config(text=message)

    def get_text(self):
        return self.text.get('1.0', 'end-1c')

    def set_text(self, value):
        if self.get_text() == value:
            return
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', value)
        self.text.see('end')
