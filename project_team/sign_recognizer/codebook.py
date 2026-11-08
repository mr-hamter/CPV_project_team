"""Bảng mã 1/2: dùng hết mã ngắn rồi mới tới mã dài hơn."""
from itertools import count, product
from string import ascii_uppercase


def build_codebook(symbols):
    codes = (''.join(code) for length in count(1) for code in product('12', repeat=length))
    return dict(zip(codes, symbols))


# Dấu cách dùng cử chỉ vuốt trên lòng bàn tay nên không cần mã riêng
CODEBOOK = build_codebook((*ascii_uppercase, 'BACKSPACE'))
SYMBOL_CODES = {symbol: code for code, symbol in CODEBOOK.items()}
MAX_CODE_LENGTH = max(map(len, CODEBOOK))


class CodeInput:
    def __init__(self):
        self.pending = ''

    def apply(self, event, text):
        """Xử lý một lệnh, trả về (văn bản mới, thông báo)."""
        if event == 'BACKSPACE':
            if not self.pending:
                return text, 'Mã đang trống.'
            self.pending = self.pending[:-1]
            return text, 'Đã xóa dấu cuối của mã.'
        if event in ('1', '2'):
            if len(self.pending) >= MAX_CODE_LENGTH:
                return text, f'Mã dài tối đa {MAX_CODE_LENGTH} dấu, hãy xác nhận hoặc xóa bớt.'
            self.pending += event
            return text, 'Chạm ngón áp út để xác nhận.'
        if event == 'CONFIRM':
            if not self.pending:
                return text, 'Mã đang trống.'
            value = CODEBOOK.get(self.pending)
            if value is None:
                return text, 'Mã không có trong bảng, hãy sửa lại.'
            self.pending = ''
            if value == 'BACKSPACE':
                return text[:-1], 'Đã xóa ký tự cuối.'
            return text + value, f'Đã nhập chữ {value}.'
        if event == 'SPACE':
            if self.pending:
                return text, 'Còn mã chưa xác nhận, hãy xác nhận hoặc xóa mã rồi mới cách.'
            return text + ' ', 'Đã thêm dấu cách.'
        return text, ''
