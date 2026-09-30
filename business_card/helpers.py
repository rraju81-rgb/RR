import barcode, qrcode
def qr_path(url, x, y, size):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    q.add_data(url); q.make(fit=True)
    m = q.get_matrix(); n = len(m); c = size / n
    d = "".join(f"M{x+j*c:.3f} {y+i*c:.3f}h{c:.3f}v{c:.3f}h-{c:.3f}z"
                for i, r in enumerate(m) for j, v in enumerate(r) if v)
    return d

def bars(text, x, y, w, h):
    bits = barcode.Code128(text).build()[0]
    c = w / len(bits); out = []; i = 0
    while i < len(bits):
        if bits[i] == "1":
            j = i
            while j < len(bits) and bits[j] == "1": j += 1
            out.append(f"M{x+i*c:.3f} {y}h{(j-i)*c:.3f}v{h}h-{(j-i)*c:.3f}z"); i = j
        else: i += 1
    return "".join(out), len(bits)

def brackets(x1, y1, x2, y2, l, col, sw=.22):
    return (f'<g stroke="{col}" stroke-width="{sw}" fill="none" stroke-linecap="square">'
            f'<path d="M{x1} {y1+l}V{y1}H{x1+l}"/><path d="M{x2-l} {y1}H{x2}V{y1+l}"/>'
            f'<path d="M{x1} {y2-l}V{y2}H{x1+l}"/><path d="M{x2-l} {y2}H{x2}V{y2-l}"/></g>')

