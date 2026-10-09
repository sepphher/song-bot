"""python tools.py genkey            -> prints a new Fernet key
   python tools.py encrypt cookies.txt -> writes data/cookies.enc (needs COOKIES_KEY in .env)"""
import os
import sys
from cryptography.fernet import Fernet

if len(sys.argv) >= 2 and sys.argv[1] == "genkey":
    print(Fernet.generate_key().decode())
elif len(sys.argv) == 3 and sys.argv[1] == "encrypt":
    from config import COOKIES_KEY, COOKIES_ENC
    os.makedirs(os.path.dirname(COOKIES_ENC) or ".", exist_ok=True)
    with open(sys.argv[2], "rb") as f:
        enc = Fernet(COOKIES_KEY.encode()).encrypt(f.read())
    with open(COOKIES_ENC, "wb") as f:
        f.write(enc)
    print("saved", COOKIES_ENC, "- now delete the plain cookies file")
else:
    print(__doc__)
