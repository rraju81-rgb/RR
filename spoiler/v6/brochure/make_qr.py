"""Regenerate the brochure QR codes (run from spoiler/v6/brochure). Change the links here if the contact details change."""
import segno

LINKS = {
    'qr_whatsapp': 'https://wa.me/919900611996',
    'qr_instagram': 'https://instagram.com/c6_customization',
}
for name, url in LINKS.items():
    q = segno.make(url, error='m')
    q.save(f'assets/{name}.svg', scale=4, border=1, dark='#0a0b0e', light='#ffffff')
    print(name, url, q.designator)
