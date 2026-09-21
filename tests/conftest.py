import pytest

from cipherguard import create_app
from cipherguard.config import Config

HOLDS = "84,88,82,90,86,84,88,85"
INTERVALS = "119,116,122,118,120,117,121"

DEMO = ("demo", "DemoHoneyword1!")
ADMIN = ("admin", "AdminCipherGuard1!")


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("cipherguard-data")

    class TestConfig(Config):
        TESTING = True
        DATA_DIR = data_dir
        USERS_FILE = data_dir / "users.json"
        TRAFFIC_FILE = data_dir / "traffic.json"
        AUDIT_IMAGE = data_dir / "audit.png"
        INVOICE_IMAGE = data_dir / "invoices.png"
        AVATAR_DIR = data_dir / "avatars"

    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sign_in(client):
    def perform(credentials=DEMO, **extra):
        username, password = credentials
        data = {"username": username, "password": password, "holds": HOLDS, "intervals": INTERVALS}
        data.update(extra)
        return client.post("/login", data=data, follow_redirects=True)
    return perform


def text(response):
    return response.get_data(as_text=True)
