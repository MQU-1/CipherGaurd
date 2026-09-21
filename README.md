# CipherGuard

A web storefront for security hardware and courses. The account system demonstrates layered authentication
(password storage, honeywords, keystroke dynamics, TOTP, lockout, encrypted recovery) and steganographic data
hiding (audit records and invoices embedded in PNG images).

## Running it

Double-click `RUNme ;).py`, or from a terminal:

```
py "RUNme ;).py"
```

The browser opens at <http://127.0.0.1:5000>. Press Ctrl+C in the console window to stop the server.

No installation is required to run the store. Flask and its supporting libraries are bundled in `vendor/` and added
to the import path by `cipherguard/__init__.py`. Everything else is the Python standard library. Requires Python
3.9 or newer; developed and tested on 3.14.

The test suite is the one exception and is optional. See [Tests](#tests).

On macOS or Linux, use `python3 "RUNme ;).py"`.

## Seeded accounts

Created on first boot, along with the `data/` directory.

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `AdminCipherGuard1!` | admin |
| `superadmin` | `SuperAdminTraffic1!` | admin |
| `demo` | `DemoHoneyword1!` | user |

Admin accounts can open the audit trail at `/admin/audit` and the request log at `/admin/traffic`. The `demo`
account is the only one that retains a plaintext copy of its honeyword list, which the lab page at
`/account/honeywords` displays.

## The storefront

Eight hardware products and five courses, with category filters, sorting, search, a cart drawer, checkout and order
history. Courses are single-seat digital items and are not charged delivery. Hardware ships free above the
threshold in `Config.FREE_SHIPPING_THRESHOLD`.

Checkout is a demonstration. No payment is taken and the delivery fields are not stored.

## Security layers

**Password storage.** Passwords are salted and hashed with PBKDF2-SHA256 at 100,000 iterations. No password is
stored in plaintext.

**Honeywords.** Each account stores twenty hashes: one real password and nineteen generated decoys, shuffled. A
sign-in attempt matching a decoy is refused and logged as a `honeyword` event, which is the signal that the
credential file has been cracked and is being tried against the site. In this implementation the index of the real
hash is held in `users.json` alongside the hashes; see [Known limitations](#known-limitations).

**Keystroke dynamics.** Key hold times and inter-key intervals are captured in the browser during registration and
reduced to a per-position mean and standard deviation. Each sign-in is compared against that profile. A mismatch
raises the session risk score and is recorded; it does not block the sign-in.

**Two-factor authentication.** RFC 6238 time-based codes, enrolled at `/account/two-factor` by scanning a QR code.
Verification allows one time step either side of the current counter to tolerate clock drift.

**Lockout.** Five consecutive failures lock an account for 300 seconds. Unknown usernames and incorrect passwords
return the same message. A sign-in attempt for a username that does not exist is checked against a discardable
honeyword store, so it performs the same twenty PBKDF2 verifications as a real account and takes the same time to
answer. Without that, the difference between an instant rejection and a 400 ms one would tell an attacker which
usernames are registered.

**Recovery.** The recovery answer is encrypted with a Vigenère or Playfair cipher under a key derived from a
per-account salt and the site pepper. The plaintext answer is never stored. Three incorrect answers end the flow.

**Injection honeypot.** Search terms matching any of thirteen injection signatures are compiled into a SQL string,
displayed, and discarded without execution. The attempt is written to the audit trail. Hidden `contact_email`
fields on the sign-in and registration forms record submissions from automated clients.

## Data storage

All state is written to `data/`, which is created on first run.

| Path | Contents |
| --- | --- |
| `data/users.json` | Account records: honeyword store, keystroke profile, TOTP state, lockout counters |
| `data/audit.png` | Security events, embedded in the least significant bits |
| `data/invoices.png` | Sealed invoices, embedded the same way |
| `data/traffic.json` | Request log, capped at the 2000 most recent entries |
| `data/avatars/` | Per-account avatars with the username embedded in the pixels |

Invoices are serialised, encrypted with an HMAC-derived keystream and given an HMAC tag before being embedded. The
order page verifies the tag on each view and reports failures. Modifying either carrier image corrupts the embedded
payload, after which the records no longer parse.

Delete `data/` to reset all state.

### PNG codec

`cipherguard/png.py` reads and writes PNG files directly: chunk framing, CRC32 checksums, zlib streams and all five
scanline filter types. It replaces Pillow for two reasons. The steganography requires access to raw channel bytes,
and removing the only compiled dependency is what allows the `vendor/` bundle to work across Python versions. It
reads images produced by other tools, including the Pillow-generated carriers from earlier versions of this
project.

## Layout

```
RUNme ;).py                 Entry point
pyproject.toml              pytest settings
vendor/                     Bundled pure-Python libraries (flask, jinja2, werkzeug, click, qrcode, ...)
cipherguard/
  __init__.py               Application factory, vendor bootstrap, blueprint registration, error handlers
  config.py                 Paths, keys, commercial and lockout settings
  catalog.py                Products and courses
  cart.py                   Session cart and totals
  auth.py                   Accounts, sessions, route guards, lockout, risk scoring
  crypto.py                 PBKDF2 hashing, honeywords, strength scoring, sealed payloads
  ciphers.py                Vigenère and Playfair
  keystroke.py              Typing profile enrolment and distance measurement
  totp.py                   RFC 6238 codes, provisioning URIs, QR rendering
  stego.py                  LSB embedding, audit and invoice carriers, avatars
  png.py                    PNG encoder and decoder
  store.py                  All reads and writes under data/
  monitoring.py             Injection signatures, request inspection, traffic logging
  filters.py                Template filters
  views/                    storefront, auth, account, admin and api blueprints
  static/                   css: base, components, pages · js: store, keystroke, password-strength
  templates/                Jinja templates
tests/                      70 tests covering the cryptography, the storefront and the access rules
```

## Tests

Not required to run or review the store.

`pytest` is the only dependency that is not bundled:

```
py -m pip install pytest
py -m pytest
```

70 tests. Each test module uses its own temporary data directory, so the suite never modifies `data/`.

## Known limitations

**The honeychecker is not a separate service.** In the original honeyword proposal the index of the real hash is
held by an isolated system, so that stealing the credential file gives an attacker no way to tell the decoys from
the real password. Here that index sits in `users.json` next to the hashes, and an attacker who reads the file
reads the index too. Separating it properly needs a second process with its own trust boundary, which is outside
what a single-machine demonstration can show. The decoys still work against an attacker who only guesses at the
login form, which is the case the audit trail is built to catch.

**The demo account stores its honeywords in plaintext.** `demo` keeps its decoy list unencrypted so the lab page
can display it next to the hashes. No other account does this and no real system should.

**The keys are placeholders.** The session key, pepper and invoice key in `config.py` are development defaults and
are committed to the repository.

**The keystroke profile is built from two samples.** That is enough to demonstrate the mechanism and nowhere near
enough to set a threshold responsibly. A real deployment would collect many more and measure false accept and
false reject rates before deciding what the distance cutoff should be.

**This runs on Flask's development server.** Appropriate for a demonstration on one machine, not for deployment.

## Configuration

Read from the environment, with development defaults in `cipherguard/config.py`.

| Variable | Purpose |
| --- | --- |
| `CIPHERGUARD_SECRET` | Flask session signing key |
| `CIPHERGUARD_PEPPER` | Site-wide pepper for recovery answers |
| `CIPHERGUARD_INVOICE_KEY` | Key for sealing invoices |
| `CIPHERGUARD_DATA` | Alternative data directory |

The defaults are placeholders for local use. Changing them invalidates existing recovery answers and invoice seals.

## Access control

| Route | Permitted |
| --- | --- |
| `/admin/audit`, `/admin/traffic` and their JSON views | Administrators |
| `/orders/<id>`, `/orders/<id>/sealed` | The account that placed the order, or an administrator |
| `/account/...` | Any signed-in account |
