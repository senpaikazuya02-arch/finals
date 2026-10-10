import qrcode

text = input("Text to put in the QR: ")
img = qrcode.make(text)
img.save("test_qr.png")
print("Saved test_qr.png")
