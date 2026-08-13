import json
import os
import random
import struct
import zlib

from PIL import Image

MAGIC = b"CGLOG"

COVER_SIZE = (256, 256)
COVER_SEED = 1337
AVATAR_SIZE = (128, 128)


def _make_cover():
    rng = random.Random(COVER_SEED)
    w, h = COVER_SIZE
    img = Image.new("RGB", (w, h))
    img.putdata([(rng.randrange(0, 256), rng.randrange(0, 256), rng.randrange(0, 256)) for _ in range(w * h)])
    return img


def _capacity(img):
    return img.width * img.height * 3 // 8


def embed_into(img, payload):
    img = img.copy()
    if (len(payload) + 5) * 8 > _capacity(img) * 8:
        raise ValueError("Payload too large for image.")
    header = MAGIC + struct.pack(">I", len(payload))
    stream = bytearray(header + payload)
    flat = list(img.getdata())
    for bit_index, byte in enumerate(stream):
        for shift in range(7, -1, -1):
            bit = (byte >> shift) & 1
            position = bit_index * 8 + (7 - shift)
            pixel_index = position // 3
            channel = position % 3
            value = list(flat[pixel_index])
            value[channel] = (value[channel] & 0xFE) | bit
            flat[pixel_index] = tuple(value)
    img.putdata(flat)
    return img


def extract_from(img):
    flat = list(img.getdata())
    bits = []
    for r, g, b in flat:
        bits.append(r & 1)
        bits.append(g & 1)
        bits.append(b & 1)
    byte_count = (len(flat) * 3) // 8
    data = bytearray()
    for i in range(byte_count):
        byte = 0
        for k in range(8):
            byte = (byte << 1) | bits[i * 8 + k]
        data.append(byte)
        if i >= 8:
            if bytes(data[:5]) != MAGIC:
                return None
            length = struct.unpack(">I", bytes(data[5:9]))[0]
            if len(data) >= 9 + length:
                payload = bytes(data[9:9 + length])
                if len(payload) == length:
                    return payload
                return None
    return None


def encode(payload):
    return embed_into(_make_cover(), payload)


def decode(img):
    return extract_from(img)


def make_avatar(username):
    rng = random.Random(zlib.crc32(username.encode("utf-8")) & 0xFFFFFFFF)
    w, h = AVATAR_SIZE
    base_r = rng.randrange(30, 220)
    base_g = rng.randrange(30, 220)
    base_b = rng.randrange(30, 220)
    pixels = []
    for y in range(h):
        for x in range(w):
            r = (base_r + x * 3 + y * 2) % 256
            g = (base_g + x * 2 + y * 3) % 256
            b = (base_b + (x * x + y * y) % 97 + y * 4) % 256
            pixels.append((r, g, b))
    img = Image.new("RGB", (w, h))
    img.putdata(pixels)
    return embed_into(img, username.encode("utf-8"))


def extract_avatar(img):
    payload = extract_from(img)
    if payload is None:
        return None
    return payload.decode("utf-8", errors="replace")


def ensure_audit_image(path):
    if not os.path.exists(path):
        _make_cover().save(path)


def read_entries(path):
    ensure_audit_image(path)
    with Image.open(path) as img:
        payload = extract_from(img)
    if not payload:
        return []
    try:
        return json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return []


def append_entry(path, entry):
    ensure_audit_image(path)
    entries = read_entries(path)
    entries.append(entry)
    payload = json.dumps(entries, ensure_ascii=False).encode("utf-8")
    encode(payload).save(path)
    return entries
