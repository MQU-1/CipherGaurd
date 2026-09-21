import json
import os
import random
import struct
import zlib

from cipherguard import png

MAGIC = b"CGLOG"
HEADER_SIZE = len(MAGIC) + 4
COVER_SIZE = (512, 512)
COVER_SEED = 1337
AVATAR_SIZE = (160, 160)


class CapacityError(ValueError):
    pass


def capacity(raster):
    return len(raster.data) // 8 - HEADER_SIZE


def embed(raster, payload):
    channels = bytearray(raster.data)
    stream = MAGIC + struct.pack(">I", len(payload)) + payload
    if len(stream) * 8 > len(channels):
        raise CapacityError("payload of {} bytes exceeds cover capacity".format(len(payload)))

    for index, byte in enumerate(stream):
        base = index * 8
        for offset in range(8):
            channels[base + offset] = (channels[base + offset] & 0xFE) | ((byte >> (7 - offset)) & 1)

    return png.Raster(raster.width, raster.height, channels)


def extract(raster):
    channels = raster.data
    if len(channels) < HEADER_SIZE * 8:
        return None

    header = _read(channels, 0, HEADER_SIZE)
    if header[:len(MAGIC)] != MAGIC:
        return None

    length = struct.unpack(">I", header[len(MAGIC):HEADER_SIZE])[0]
    if (HEADER_SIZE + length) * 8 > len(channels):
        return None
    return _read(channels, HEADER_SIZE, length)


def ensure_carrier(path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        cover().save(path)


def read_records(path):
    if not os.path.exists(path):
        return []
    payload = extract(png.load(path))
    if not payload:
        return []
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return []


def append_record(path, record):
    ensure_carrier(path)
    carrier = png.load(path)
    records = read_records(path)
    records.append(record)

    payload = _serialise(records)
    while len(records) > 1 and len(payload) > capacity(carrier):
        records.pop(0)
        payload = _serialise(records)

    embed(carrier, payload).save(path)
    return records


def cover():
    width, height = COVER_SIZE
    noise = random.Random(COVER_SEED).randbytes(width * height * 3)
    return png.Raster(width, height, noise)


def make_avatar(username):
    rng = random.Random(zlib.crc32(username.encode("utf-8")))
    width, height = AVATAR_SIZE
    base = (rng.randrange(40, 210), rng.randrange(60, 190), rng.randrange(70, 200))

    pixels = bytearray(width * height * 3)
    position = 0
    for y in range(height):
        for x in range(width):
            drift = 0.55 + 0.45 * (x + y) / (width + height)
            pixels[position] = int(base[0] * drift) & 0xFF
            pixels[position + 1] = int(base[1] * drift) & 0xFF
            pixels[position + 2] = int(base[2] * drift) & 0xFF
            position += 3

    return embed(png.Raster(width, height, pixels), username.encode("utf-8"))


def read_avatar(path):
    payload = extract(png.load(path))
    if payload is None:
        return None
    return payload.decode("utf-8", errors="replace")


def _serialise(records):
    return json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _read(channels, start, count):
    data = bytearray()
    for index in range(start, start + count):
        base = index * 8
        byte = 0
        for offset in range(8):
            byte = (byte << 1) | (channels[base + offset] & 1)
        data.append(byte)
    return bytes(data)
