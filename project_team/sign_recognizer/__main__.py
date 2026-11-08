import argparse
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description='Nhập chữ bằng cử chỉ tay (mã 1/2)')
    parser.add_argument('--camera', type=int, default=0)
    parser.add_argument('--threshold', type=float, default=.28,
                        help='khoảng cách chạm / kích thước lòng bàn tay')
    parser.add_argument('--report', metavar='CSV', help='tính kết quả đánh giá từ file trials.csv')
    args = parser.parse_args(argv)
    if args.camera < 0 or not .05 <= args.threshold <= .6:
        parser.error('camera phải >= 0, threshold trong khoảng .05 đến .6')
    try:
        if args.report:
            from .evaluation import report
            print(report(args.report))
        else:
            from .recognizer import SignRecognizer
            SignRecognizer(args.camera, args.threshold).run()
        return 0
    except (ImportError, RuntimeError, OSError, ValueError) as exc:
        print(f'Lỗi: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
