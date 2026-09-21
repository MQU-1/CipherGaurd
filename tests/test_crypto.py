import pytest

from cipherguard import ciphers, crypto, keystroke, png, stego

PEPPER = "test-pepper"


def test_password_hash_roundtrip():
    stored = crypto.hash_password("Str0ng!Passphrase42")
    assert crypto.verify_password(stored, "Str0ng!Passphrase42")
    assert not crypto.verify_password(stored, "Str0ng!Passphrase43")


@pytest.mark.parametrize("stored", ["", "nonsense", "a$b$c", None])
def test_malformed_hashes_are_rejected(stored):
    assert not crypto.verify_password(stored, "anything")


def test_honeyword_store_hides_the_real_password():
    store, words, real_index = crypto.build_store_with_words("Str0ng!Passphrase42")
    decoy = next(word for index, word in enumerate(words) if index != real_index)

    assert len(store["entries"]) == crypto.DECOY_COUNT + 1
    assert crypto.check_store(store, "Str0ng!Passphrase42") == crypto.REAL
    assert crypto.check_store(store, decoy) == crypto.DECOY
    assert crypto.check_store(store, "never-used-anywhere") == crypto.UNKNOWN


def test_decoys_are_distinct_and_plausible():
    _, words, _ = crypto.build_store_with_words("Str0ng!Passphrase42")
    assert len(set(words)) == len(words)
    assert all(len(word) >= 8 for word in words)


def test_strength_rejects_known_passwords():
    assert crypto.evaluate_strength("password")["score"] == 0
    assert crypto.evaluate_strength("")["score"] == 0
    assert not crypto.evaluate_strength("abc123")["accepted"]


def test_strength_accepts_a_real_passphrase():
    report = crypto.evaluate_strength("Str0ng!Passphrase42")
    assert report["accepted"]
    assert report["entropy"] > 45


def test_seal_roundtrip_and_tamper_detection():
    key = b"unit-test-key"
    sealed = crypto.seal({"order_id": "CG-1", "total": 12.5}, key)

    assert crypto.unseal(sealed, key) == {"order_id": "CG-1", "total": 12.5}
    assert crypto.unseal(sealed, b"wrong-key") is None
    assert crypto.seal_matches(sealed, key, {"total": 12.5})
    assert not crypto.seal_matches(sealed, key, {"total": 99.0})

    body, tag = sealed.split(".")
    assert crypto.unseal(body[:-2] + "AA." + tag, key) is None


def test_vigenere_roundtrip():
    assert ciphers.vigenere_decrypt(ciphers.vigenere_encrypt("attack at dawn", "lemon"), "lemon") == "attackatdawn"


def test_playfair_roundtrip():
    encrypted = ciphers.playfair_encrypt("hide the gold", "cipherguard")
    assert ciphers.playfair_decrypt(encrypted, "cipherguard").startswith("hidethegold")


@pytest.mark.parametrize("cipher", [ciphers.VIGENERE, ciphers.PLAYFAIR])
def test_recovery_answers_are_stored_as_ciphertext(cipher):
    record = ciphers.encrypt_answer("Sparrow", PEPPER, cipher)

    assert "sparrow" not in record["ciphertext"].lower()
    assert ciphers.verify_answer("sparrow", record, PEPPER)
    assert ciphers.verify_answer("SPARROW", record, PEPPER)
    assert not ciphers.verify_answer("seagull", record, PEPPER)
    assert not ciphers.verify_answer("Sparrow", record, "different-pepper")


def test_keystroke_profile_accepts_similar_rhythm():
    samples = [
        {"holds": [80, 85, 78, 90], "intervals": [120, 118, 125]},
        {"holds": [82, 88, 80, 92], "intervals": [122, 115, 127]},
    ]
    profile = keystroke.enroll(samples)

    assert keystroke.is_enrolled(profile)
    matched, distance = keystroke.compare(profile, [81, 86, 79, 91], [121, 117, 126])
    assert matched and distance < keystroke.MATCH_THRESHOLD


def test_keystroke_profile_flags_a_different_typist():
    profile = keystroke.enroll([{"holds": [80, 85, 78, 90], "intervals": [120, 118, 125]}])
    matched, _ = keystroke.compare(profile, [300, 420, 260, 500], [700, 810, 640])
    assert not matched


def test_keystroke_handles_missing_samples():
    profile = keystroke.enroll([{"holds": [80, 85], "intervals": [120]}])
    assert keystroke.compare(profile, [], []) == (False, None)
    assert keystroke.parse("80, 85, ,90") == [80.0, 85.0, 90.0]


def test_png_roundtrip():
    raster = png.Raster(4, 2, bytes(range(24)))
    restored = png.decode(png.encode(raster))

    assert restored.size == (4, 2)
    assert bytes(restored.data) == bytes(range(24))


def test_png_rejects_other_formats():
    with pytest.raises(png.FormatError):
        png.decode(b"GIF89a not really a png")


def test_stego_roundtrip_leaves_the_image_intact_to_the_eye():
    cover = stego.cover()
    carrier = stego.embed(cover, b"the payload")

    assert stego.extract(carrier) == b"the payload"
    assert carrier.size == cover.size
    assert all(abs(a - b) <= 1 for a, b in zip(carrier.data[:2000], cover.data[:2000]))


def test_stego_survives_a_save_and_load(tmp_path):
    path = tmp_path / "carrier.png"
    stego.embed(stego.cover(), b"persisted payload").save(path)
    assert stego.extract(png.load(path)) == b"persisted payload"


def test_stego_refuses_an_oversized_payload():
    with pytest.raises(stego.CapacityError):
        stego.embed(png.new(8, 8), b"x" * 500)


def test_stego_reports_nothing_for_an_unmarked_image():
    assert stego.extract(png.new(32, 32, (7, 9, 11))) is None


def test_audit_records_append_and_survive(tmp_path):
    path = str(tmp_path / "audit.png")
    stego.append_record(path, {"action": "login", "result": "success"})
    stego.append_record(path, {"action": "logout", "result": "success"})

    records = stego.read_records(path)
    assert [record["action"] for record in records] == ["login", "logout"]


def test_avatar_carries_the_username(tmp_path):
    path = tmp_path / "avatar.png"
    stego.make_avatar("taylor").save(path)
    assert stego.read_avatar(path) == "taylor"
