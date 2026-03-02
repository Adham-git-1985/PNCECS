import qrcode

qr = qrcode.QRCode(
    version=4,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=4,
)

qr.add_data("https://drive.google.com/drive/folders/1cmsThw8aZ3Oder9ItmX0HOoyu45fe8ec?usp=sharing")
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white")
img.save("drive_pdf_qr.png")

print("تم إنشاء QR Code بنجاح")
