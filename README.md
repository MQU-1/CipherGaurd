# CipherGuard Store

A class project demonstrating multi-layer authentication (Ch3: password storage,
honeywords, keystroke dynamics, TOTP, lockout) and steganographic data hiding
(Ch4: LSB-based audit log and invoices hidden inside PNG image files).

Everything runs locally with no database — user accounts, audit records and
invoices are stored as images and a JSON file inside `data/`.

## Requirements

- Python 3.9+ (tested on 3.11, Windows)
- `pip install -r requirements.txt` (installs `flask` and `pillow`)

## How to run

```
cd CipherGuard
py -m pip install -r requirements.txt
py app.py
```

Then open <http://127.0.0.1:5000> in a browser.

> On macOS/Linux use `python3` instead of `py`.

## Demo accounts (created automatically on first boot)

| Username | Password | Role | Purpose |
| --- | --- | --- | --- |
| `admin` | `AdminCipherGuard1!` | admin | Can view the stego audit log at `/audit` |
| `superadmin` | `SuperAdminTraffic1!` | admin | Can view `/audit` plus the full traffic log at `/traffic` (every request, including all sign-in attempts) |
| `demo` | `DemoHoneyword1!` | user | Honeyword Lab demo (`/dev/honeywords`) |

New accounts can be created at `/register`. The first thing any new user must do
is type a sample password a few times so the keystroke profile can be captured
(JavaScript records hold times and inter-key intervals).

## What the demo shows

1. **Password storage (Ch3)** — passwords are never stored in plaintext. Each
   account stores 20 hashes: 1 real password + 19 decoys (honeywords), all
   salted PBKDF2-100k. Typing a decoy password triggers a `honeyword` alert in
   the audit log (credential-guessing detection).
2. **Honeyword Lab** — log in as any user and open **Honeywords** in the nav to
   see the demo user's decoy list, the PBKDF2 hashes, and to test a candidate
   password. The hashes of real vs. decoy are indistinguishable.
3. **Keystroke dynamics** — every login compares the typing rhythm against the
   enrolled profile. A distant rhythm raises the risk score and flags the
   session as an anomaly.
4. **TOTP two-factor (Ch3)** — `/account` lets a user enable RFC 6238
   time-based codes. After enabling, login requires a 6-digit code from an
   authenticator app (or the `/totp/setup` page shows the current code).
5. **Lockout** — 5 consecutive failed logins lock the account for 300 seconds,
   which also defeats credential stuffing against the honeyword store.
6. **Security questions (classical ciphers)** — password reset uses a question
   whose answer is stored encrypted with a Vigenere or Playfair cipher.
7. **Steganographic audit log (Ch4)** — `/audit` (admin only) shows every event
   (login, honeyword hit, lockout, SQLi probe, honeytoken trap, checkout...).
   The records are appended as hidden bits in `data/audit.png`. Tampering with
   the image corrupts the LSB payload and destroys the trail.
8. **Stego avatars** — each account's avatar image embeds the username in its
   LSBs; `data/avatars/<name>.png` can be decoded with the provided module.
9. **Stego invoices** — every order stores an HMAC-authenticated, stream-cipher
   sealed invoice as hidden bits in `data/invoices.png`. Order pages validate
   the MAC and flag any tampering.
10. **SQLi honeypot** — the header search box feeds a fake SQL engine. Inputs
    that look like injection (`' OR '1'='1`, stacked `DROP`, time-based `sleep()`,
    schema probes...) are compiled into a fake query, never executed, and
    written to the audit trail as an `sqli` event without tipping off the
    attacker. Hidden `honeypot_email` fields on login/register trap scrapers
    and log `honeypot` events.

## Access control

- `/audit`, `/audit/raw`, `/audit/image` — **admin only**
- `/traffic`, `/traffic/raw` — **admin only** (every HTTP request, sign-in attempts and errors)
- `/order/<id>`, `/invoice/<id>/sealed` — owner or admin
- `/dev/honeywords` — any signed-in user (dev diagnostic)

## Traffic log

Every request is appended to `data/traffic.json` (capped at the 2000 most recent):
timestamp, IP, method, path, status code, session user, user agent and referer.
Admins can browse/filter it at `/traffic`, including a dedicated list of every
sign-in and password-reset attempt. Security events stay in the stego `audit.png`,
while the high-volume request log uses a plaintext JSON file.

## Project layout

```
app.py                  # Flask app: all routes, auth, lockout, honeypot monitor
requirements.txt        # flask, pillow
modules/
  password_strength.py  # entropy + common-password scoring (0-4)
  honeywords.py         # decoy generation + PBKDF2 honeyword store
  keystroke.py          # typing-rhythm profile + distance scoring
  totp.py               # RFC 6238 time-based one-time passwords
  cipher_questions.py   # Vigenere / Playfair answer encryption
  crypto_utils.py       # PBKDF2 hashing + sealed (MAC) stream cipher
  stego.py              # LSB embed/extract, audit + invoice image store
  sqli_honeypot.py      # injection-payload scanner + fake query compiler
static/
  css/style.css         # dark storefront theme
  js/keystroke.js       # captures hold/interval timing on password fields
  js/app.js             # cart, toasts, strength meter, audit chart
templates/              # Jinja2 pages (storefront UI)
data/                   # created on first run (users.json, audit.png, invoices.png)
```

## Notes

- Demo keys are placeholders (`PEPPER`, `INVOICE_KEY`, `app.secret_key` in
  `app.py`) — rotate before any real use.
- To reset all state, stop the server and delete the `data/` folder; it is
  recreated on next boot with the demo accounts.
- The `honeywords_dev` plaintext list is stored only for the `demo` user and is
  clearly a dev-only diagnostic that would never ship in production.
