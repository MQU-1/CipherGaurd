from dataclasses import dataclass

PRODUCT = "product"
COURSE = "course"


@dataclass(frozen=True)
class Product:
    slug: str
    name: str
    tagline: str
    price: float
    category: str
    artwork: str
    description: str
    highlights: tuple
    specs: tuple
    lead_time: str
    rating: float
    reviews: int
    featured: bool = False
    kind: str = PRODUCT

    @property
    def summary(self):
        return self.tagline


@dataclass(frozen=True)
class Course:
    slug: str
    code: str
    name: str
    tagline: str
    price: float
    level: str
    duration: str
    instructor: str
    description: str
    outcomes: tuple
    lessons: tuple
    enrolled: int
    featured: bool = False
    kind: str = COURSE
    category: str = "Courses"

    @property
    def summary(self):
        return self.tagline

    @property
    def lesson_count(self):
        return len(self.lessons)


PRODUCTS = (
    Product(
        slug="cipherlock-padlock",
        name="CipherLock Padlock",
        tagline="Hardened shackle with a rotating six-digit challenge",
        price=89.00,
        category="Locks",
        artwork="padlock",
        description=(
            "A boron-carbide shackle wrapped around a mechanism that expects a fresh code every thirty seconds. "
            "Pair it once with the CipherGuard app and the lock never stores a static combination again."
        ),
        highlights=(
            "Rolling code derived on-device, never transmitted",
            "Ten wrong attempts and the keypad sleeps for five minutes",
            "IP66 body, rated for outdoor gates and storage units",
        ),
        specs=(
            ("Body", "Forged brass, powder coated"),
            ("Shackle", "9 mm boron carbide"),
            ("Battery", "CR2032, roughly 18 months"),
            ("Weight", "412 g"),
        ),
        lead_time="Ships in 2 business days",
        rating=4.8,
        reviews=214,
        featured=True,
    ),
    Product(
        slug="honeyjar-safe",
        name="HoneyJar Backup Safe",
        tagline="Two compartments: one real, nineteen convincing decoys",
        price=249.00,
        category="Locks",
        artwork="safe",
        description=(
            "A recovery-phrase safe built on the honeyword idea. Nineteen decoy drawers open on the wrong code and "
            "quietly log the attempt; only the enrolled sequence reaches the sealed compartment."
        ),
        highlights=(
            "Decoy drawers are indistinguishable from the real one",
            "Tamper log survives on the internal counter, not on paper",
            "Steel plate door with anti-drill collar",
        ),
        specs=(
            ("Dimensions", "310 x 240 x 180 mm"),
            ("Wall", "4 mm cold-rolled steel"),
            ("Anchoring", "Four floor bolts included"),
            ("Warranty", "5 years"),
        ),
        lead_time="Ships in 4 business days",
        rating=4.6,
        reviews=87,
        featured=True,
    ),
    Product(
        slug="playfair-safe-box",
        name="Playfair Deposit Box",
        tagline="Digraph dial, machined to a quarter-degree",
        price=119.00,
        category="Locks",
        artwork="box",
        description=(
            "A desk-sized deposit box that opens on a Playfair pair rather than a number. The dial is machined from a "
            "single billet, so the detents feel identical whether the pair is right or wrong."
        ),
        highlights=(
            "25-letter square engraved on the inner face",
            "No electronics, nothing to firmware-update",
            "Felt-lined tray for keys, drives and cards",
        ),
        specs=(
            ("Dimensions", "240 x 160 x 90 mm"),
            ("Finish", "Brushed aluminium"),
            ("Mechanism", "Mechanical digraph dial"),
            ("Weight", "1.9 kg"),
        ),
        lead_time="Ships in 2 business days",
        rating=4.4,
        reviews=63,
    ),
    Product(
        slug="timechip-watch",
        name="TimeChip Authenticator Watch",
        tagline="RFC 6238 codes on your wrist, no phone in the loop",
        price=179.00,
        category="Wearables",
        artwork="watch",
        description=(
            "Six digits, thirty seconds, sapphire glass. The secret is written once over NFC and then locked into a "
            "secure element that has no read path."
        ),
        highlights=(
            "Holds eight separate TOTP secrets",
            "Secure element with no export path",
            "Two-week battery on a single charge",
        ),
        specs=(
            ("Case", "38 mm stainless steel"),
            ("Display", "1.1 in memory LCD"),
            ("Water rating", "5 ATM"),
            ("Strap", "20 mm quick-release"),
        ),
        lead_time="Ships in 3 business days",
        rating=4.7,
        reviews=341,
        featured=True,
    ),
    Product(
        slug="faraday-sleeve",
        name="Faraday Travel Sleeve",
        tagline="Silence every radio in the bag, not just the phone",
        price=45.00,
        category="Wearables",
        artwork="sleeve",
        description=(
            "Nickel-copper ripstop with a double roll-top closure. Enough attenuation to keep a key fob, a phone and "
            "two access cards off the air while you move."
        ),
        highlights=(
            "60 dB attenuation from 800 MHz to 5 GHz",
            "Fits a 6.9 in phone plus cards",
            "Machine washable outer shell",
        ),
        specs=(
            ("Material", "Nickel-copper ripstop"),
            ("Closure", "Double roll-top"),
            ("Size", "215 x 115 mm"),
            ("Weight", "78 g"),
        ),
        lead_time="Ships tomorrow",
        rating=4.5,
        reviews=502,
    ),
    Product(
        slug="stegovault-frame",
        name="StegoVault Picture Frame",
        tagline="A photo on the wall, a keyfile in the pixels",
        price=129.00,
        category="Desk",
        artwork="frame",
        description=(
            "An e-ink frame that writes your recovery data into the least significant bits of whatever image you "
            "display. Anyone looking sees the photograph; the payload comes back out with your passphrase."
        ),
        highlights=(
            "Up to 96 KB of payload per displayed image",
            "Payload sealed with HMAC before it is embedded",
            "USB-C, no network radio of any kind",
        ),
        specs=(
            ("Panel", "7.3 in colour e-ink"),
            ("Storage", "8 GB internal"),
            ("Ports", "USB-C data and power"),
            ("Mount", "Desk stand and wall plate"),
        ),
        lead_time="Ships in 3 business days",
        rating=4.3,
        reviews=129,
    ),
    Product(
        slug="vigenere-desk-cipher",
        name="Vigenère Desk Cipher",
        tagline="Solid brass tableau for people who still work on paper",
        price=64.00,
        category="Desk",
        artwork="wheel",
        description=(
            "Two concentric brass rings and a knurled edge that lands cleanly on every letter. Sold with a pad of "
            "single-use keyword strips."
        ),
        highlights=(
            "Machined brass, 96 mm diameter",
            "Includes 50 tear-off keyword strips",
            "Sits flat, weighted base",
        ),
        specs=(
            ("Material", "Solid brass"),
            ("Diameter", "96 mm"),
            ("Weight", "540 g"),
            ("Included", "Keyword strip pad")
        ),
        lead_time="Ships tomorrow",
        rating=4.9,
        reviews=76,
    ),
    Product(
        slug="entropy-dice",
        name="Entropy Dice Set",
        tagline="Five casino-grade dice and a wordlist that fits in a pocket",
        price=28.00,
        category="Desk",
        artwork="dice",
        description=(
            "Passphrases you can audit by hand. Five precision dice, a printed 7776-word list and a card that shows "
            "how many rolls buy how many bits."
        ),
        highlights=(
            "Razor-edge dice, balanced to 0.01 mm",
            "7776-word list printed on tear-resistant stock",
            "Entropy reference card included",
        ),
        specs=(
            ("Dice", "5 x 16 mm precision"),
            ("Wordlist", "7776 entries, 64 pages"),
            ("Case", "Waxed canvas roll"),
            ("Weight", "180 g"),
        ),
        lead_time="Ships tomorrow",
        rating=4.8,
        reviews=188,
    ),
)

COURSES = (
    Course(
        slug="password-storage-done-right",
        code="CG-101",
        name="Password Storage Done Right",
        tagline="Salting, stretching and the arithmetic behind a survivable breach",
        price=89.00,
        level="Foundation",
        duration="4h 20m",
        instructor="Dr. Lina Haddad",
        description=(
            "Start from a plaintext table and finish with a store that costs an attacker real money. We build the "
            "hashing pipeline by hand, measure it, then break the versions we got wrong."
        ),
        outcomes=(
            "Pick work factors from a threat model instead of a blog post",
            "Explain salt, pepper and stretching without hand-waving",
            "Migrate a live password table without locking anyone out",
        ),
        lessons=(
            ("Why plaintext survived so long", "18m"),
            ("Hashes, salts and rainbow tables", "26m"),
            ("PBKDF2 line by line", "34m"),
            ("Choosing an iteration count", "22m"),
            ("Peppers and where to keep them", "19m"),
            ("Migrating a live table", "31m"),
            ("Breach simulation workshop", "48m"),
        ),
        enrolled=1840,
        featured=True,
    ),
    Course(
        slug="honeywords-and-decoys",
        code="CG-140",
        name="Honeywords and Decoy Credentials",
        tagline="Turn a stolen password file into an alarm system",
        price=79.00,
        level="Foundation",
        duration="3h 05m",
        instructor="Marcus Reyes",
        description=(
            "Honeywords cost almost nothing and tell you the moment a hash dump gets cracked. We generate decoys that "
            "hold up to inspection, then wire the alarm into an incident workflow."
        ),
        outcomes=(
            "Generate decoys an attacker cannot rank",
            "Separate the checker from the credential store",
            "Route a decoy hit to the right responder in minutes",
        ),
        lessons=(
            ("The economics of a cracked dump", "16m"),
            ("Generating believable decoys", "28m"),
            ("Keeping the index somewhere else", "24m"),
            ("False positives and user friction", "21m"),
            ("Alerting without tipping the attacker", "26m"),
            ("Lab: build a honeyword store", "40m"),
        ),
        enrolled=960,
        featured=True,
    ),
    Course(
        slug="keystroke-dynamics",
        code="CG-210",
        name="Keystroke Dynamics in Production",
        tagline="Behavioural signals that help, and the ones that just annoy people",
        price=119.00,
        level="Intermediate",
        duration="6h 05m",
        instructor="Dr. Priya Anand",
        description=(
            "Typing rhythm is a weak signal used well, or a support nightmare used badly. We collect samples, fit a "
            "profile, tune thresholds against real error rates and decide what the system does when it is unsure."
        ),
        outcomes=(
            "Capture timing data without wrecking the login form",
            "Read an ROC curve and set a threshold you can defend",
            "Design a step-up flow for ambiguous sessions",
        ),
        lessons=(
            ("What the timing data actually contains", "22m"),
            ("Collecting samples in the browser", "30m"),
            ("Building the enrolment profile", "35m"),
            ("Distance measures and their failure modes", "38m"),
            ("False accept versus false reject", "29m"),
            ("Step-up authentication that people accept", "27m"),
            ("Lab: tune a live threshold", "45m"),
            ("Accessibility and fairness review", "26m"),
        ),
        enrolled=1220,
    ),
    Course(
        slug="steganography-covert-channels",
        code="CG-240",
        name="Steganography and Covert Channels",
        tagline="Hiding data in plain sight, and finding it again",
        price=99.00,
        level="Intermediate",
        duration="5h 15m",
        instructor="Yusuf Karim",
        description=(
            "Least significant bits, capacity limits and the statistics that give an amateur away. Both directions: "
            "we embed a tamper-evident audit trail, then attack it."
        ),
        outcomes=(
            "Embed and recover payloads without visible artefacts",
            "Compute capacity and pick a carrier honestly",
            "Detect naive LSB work with a histogram",
        ),
        lessons=(
            ("Carriers, payloads and capacity", "24m"),
            ("LSB embedding from scratch", "33m"),
            ("Framing and length headers", "21m"),
            ("Sealing the payload before hiding it", "28m"),
            ("Statistical detection of LSB work", "36m"),
            ("Lab: a tamper-evident audit image", "42m"),
        ),
        enrolled=780,
    ),
    Course(
        slug="defensible-login",
        code="CG-320",
        name="Designing a Defensible Login",
        tagline="The whole flow: credentials, factors, lockout, recovery, logging",
        price=149.00,
        level="Advanced",
        duration="8h 30m",
        instructor="Dr. Lina Haddad",
        description=(
            "The capstone. Every layer from this catalogue assembled into one sign-in path, with the failure cases "
            "written down first: lockout, recovery, device loss, and the audit trail that has to survive all three."
        ),
        outcomes=(
            "Sequence factors so the cheap checks run first",
            "Write lockout rules that stop stuffing without helping enumeration",
            "Build recovery that is not the weakest link",
            "Produce an audit trail that stands up after an incident",
        ),
        lessons=(
            ("Threat model for a sign-in page", "26m"),
            ("Ordering the layers", "31m"),
            ("TOTP end to end", "44m"),
            ("Rate limits, lockout and enumeration", "38m"),
            ("Account recovery without a back door", "40m"),
            ("Risk scoring from real signals", "35m"),
            ("Audit trails that survive an incident", "33m"),
            ("Capstone review and critique", "52m"),
        ),
        enrolled=640,
        featured=True,
    ),
)

ITEMS = PRODUCTS + COURSES

_BY_SLUG = {item.slug: item for item in ITEMS}

CATEGORIES = ("Locks", "Wearables", "Desk")

LEVELS = ("Foundation", "Intermediate", "Advanced")

SORT_OPTIONS = (
    ("featured", "Featured"),
    ("price-asc", "Price, low to high"),
    ("price-desc", "Price, high to low"),
    ("name", "Alphabetical"),
)


def find(slug):
    return _BY_SLUG.get(slug)


def products(category=None, sort="featured"):
    selection = [item for item in PRODUCTS if not category or item.category == category]
    return arrange(selection, sort)


def courses(level=None):
    return [item for item in COURSES if not level or item.level == level]


def featured_products(limit=4):
    ranked = [item for item in PRODUCTS if item.featured] + [item for item in PRODUCTS if not item.featured]
    return ranked[:limit]


def featured_courses(limit=3):
    ranked = [item for item in COURSES if item.featured] + [item for item in COURSES if not item.featured]
    return ranked[:limit]


def related(item, limit=3):
    if item.kind == COURSE:
        pool = [other for other in COURSES if other.slug != item.slug]
    else:
        pool = [other for other in PRODUCTS if other.slug != item.slug and other.category == item.category]
        pool += [other for other in PRODUCTS if other.slug != item.slug and other.category != item.category]
    seen = []
    for candidate in pool:
        if candidate not in seen:
            seen.append(candidate)
    return seen[:limit]


def search(term):
    needle = (term or "").strip().lower()
    if not needle:
        return []
    return [item for item in ITEMS if needle in item.name.lower() or needle in item.tagline.lower()
            or needle in item.description.lower()]


def arrange(items, sort):
    if sort == "price-asc":
        return sorted(items, key=lambda item: item.price)
    if sort == "price-desc":
        return sorted(items, key=lambda item: item.price, reverse=True)
    if sort == "name":
        return sorted(items, key=lambda item: item.name)
    return sorted(items, key=lambda item: (not item.featured, item.name))
