from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_ENV_PATH = PACKAGE_ROOT / ".env"

IGNORE_TYPES = (
    "Customization Confirmation",
    "Note to seller (Optional)",
    "Other requirements",
    "Review Photo Before Final Finish",
    "Additional Note for Seller",
    "Custom Tier Size Confirmation",
    "Driftwood may differ from photos. We'll message the best raw piece. Check messages?",
    "Select Package",
    "Communication",
    "Comunication",
    "Product will slightly different as shown in pictures, please check your MESSAGES to confirm order!",
    "Live edge wood may differ from photos. We'll message the best raw piece. Check messages?",
)

DEFAULT_OPTION_TYPES = ("size", "choose size", "select size", "select width")

SIZE_CONFIG = {
    "standing": {
        "PREM": [('50"W x 45"H x 8"D', "3906"), ('65"W x 60"H x 9"D', "4426"),
                 ('75"W x 65"H x 10"D', "4947"), ('89"W x 80"H x 10-12"D', "5468")],
        "LOW": [('45"W x 45"H x 8"D', "2343"), ('59"W x 50"H x 9"D', "2864"),
                ('75"W x 65"H x 10"D', "3385"), ('89"W x 80"H x 10-12"D', "3906")],
    },
    "corner": {
        "LUXURY": [('49"W x 55"H x 8"D', "4687"), ('60"W x 60"H x 10"D', "5128"),
                   ('75"W x 69"H x 12"D', "5581"), ('90"W x 82"H x 12"D', "6034")],
        "PREM": [('49"W x 55"H x 8"D', "2983"), ('60"W x 60"H x 10"D', "3783"),
                 ('75"W x 69"H x 12"D', "4583"), ('90"W x 82"H x 12"D', "5483")],
        "LOW": [('49"W x 55"H x 8"D', "2391"), ('60"W x 60"H x 10"D', "2991"),
                ('75"W x 69"H x 12"D', "3783"), ('90"W x 82"H x 12"D', "4591")],
    },
    "floating": {
        "PREM": [('45"W x 45"H x 8"D', "1653"), ('55"W x 55"H x 8"D', "1953"),
                 ('65"W x 65"H x 10"D', "2245"), ('80"W x 80"H x 10-12"D', "2675")],
        "LOW": [('45"W x 45"H x 8"D', "1553"), ('55"W x 55"H x 8"D', "1653"),
                ('65"W x 65"H x 10"D', "2045"), ('80"W x 80"H x 10-12"D', "2375")],
    },
}


@dataclass(frozen=True)
class Settings:
    env_path: Path = DEFAULT_ENV_PATH
    profile_dir: Path = PACKAGE_ROOT / ".runtime" / "browser-profile"
    runs_dir: Path = PACKAGE_ROOT / "runs"
    logo_path: Path = PACKAGE_ROOT / "assets" / "logo.png"
    max_combinations: int = 100
    price_tolerance: Decimal = Decimal("0.01")
    headless: bool = False
    browser_timeout_ms: int = 30_000
    amazon_postal_code: str = "10001"

