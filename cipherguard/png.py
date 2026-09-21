import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
BIT_DEPTH = 8
COLOUR_RGB = 2
COLOUR_RGBA = 6
CHANNELS = {COLOUR_RGB: 3, COLOUR_RGBA: 4}
COMPRESSION_LEVEL = 6


class FormatError(ValueError):
    pass


class Raster:
    def __init__(self, width, height, data):
        self.width = width
        self.height = height
        self.data = bytearray(data)

    @property
    def size(self):
        return (self.width, self.height)

    def copy(self):
        return Raster(self.width, self.height, bytes(self.data))

    def save(self, path):
        with open(path, "wb") as handle:
            handle.write(encode(self))


def new(width, height, fill=(0, 0, 0)):
    return Raster(width, height, bytes(fill) * (width * height))


def load(path):
    with open(path, "rb") as handle:
        return decode(handle.read())


def decode(blob):
    if not blob.startswith(SIGNATURE):
        raise FormatError("not a PNG file")

    header = None
    compressed = bytearray()
    offset = len(SIGNATURE)

    while offset + 8 <= len(blob):
        length = struct.unpack(">I", blob[offset:offset + 4])[0]
        kind = blob[offset + 4:offset + 8]
        payload = blob[offset + 8:offset + 8 + length]
        offset += 12 + length

        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            compressed += payload
        elif kind == b"IEND":
            break

    if header is None:
        raise FormatError("missing IHDR chunk")

    width, height, depth, colour, compression, filtering, interlace = header
    if depth != BIT_DEPTH or colour not in CHANNELS or compression or filtering or interlace:
        raise FormatError("unsupported PNG variant: depth {} colour {} interlace {}".format(depth, colour, interlace))

    channels = CHANNELS[colour]
    raw = zlib.decompress(bytes(compressed))
    pixels = _unfilter(raw, width, height, channels)
    if channels == 4:
        pixels = _drop_alpha(pixels)
    return Raster(width, height, pixels)


def encode(raster):
    stride = raster.width * 3
    scanlines = bytearray()
    for row in range(raster.height):
        start = row * stride
        scanlines.append(0)
        scanlines += raster.data[start:start + stride]

    header = struct.pack(">IIBBBBB", raster.width, raster.height, BIT_DEPTH, COLOUR_RGB, 0, 0, 0)
    return b"".join([
        SIGNATURE,
        _chunk(b"IHDR", header),
        _chunk(b"IDAT", zlib.compress(bytes(scanlines), COMPRESSION_LEVEL)),
        _chunk(b"IEND", b""),
    ])


def _chunk(kind, payload):
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


def _unfilter(raw, width, height, channels):
    stride = width * channels
    expected = (stride + 1) * height
    if len(raw) < expected:
        raise FormatError("truncated image data")

    out = bytearray(stride * height)
    previous = bytearray(stride)

    for row in range(height):
        source = row * (stride + 1)
        method = raw[source]
        line = bytearray(raw[source + 1:source + 1 + stride])

        if method == 1:
            for index in range(channels, stride):
                line[index] = (line[index] + line[index - channels]) & 0xFF
        elif method == 2:
            for index in range(stride):
                line[index] = (line[index] + previous[index]) & 0xFF
        elif method == 3:
            for index in range(stride):
                left = line[index - channels] if index >= channels else 0
                line[index] = (line[index] + ((left + previous[index]) >> 1)) & 0xFF
        elif method == 4:
            for index in range(stride):
                left = line[index - channels] if index >= channels else 0
                upper_left = previous[index - channels] if index >= channels else 0
                line[index] = (line[index] + _paeth(left, previous[index], upper_left)) & 0xFF
        elif method:
            raise FormatError("unknown filter method {}".format(method))

        out[row * stride:(row + 1) * stride] = line
        previous = line

    return out


def _paeth(left, above, upper_left):
    estimate = left + above - upper_left
    da = abs(estimate - left)
    db = abs(estimate - above)
    dc = abs(estimate - upper_left)
    if da <= db and da <= dc:
        return left
    if db <= dc:
        return above
    return upper_left


def _drop_alpha(pixels):
    out = bytearray(len(pixels) // 4 * 3)
    target = 0
    for source in range(0, len(pixels), 4):
        out[target:target + 3] = pixels[source:source + 3]
        target += 3
    return out
