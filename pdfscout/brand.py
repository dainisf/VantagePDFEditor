"""Product branding shared by the desktop app, web build and installer."""

PRODUCT_NAME = "Vantage PDF Editor"
SHORT_NAME = "PDF Editor"
PUBLISHER = "DTR Networks, Inc."
EXE_NAME = "VantagePDFEditor"
WEBSITE = "https://dtrvantage.com/tools/pdf-editor/"
TOOLKIT_URL = "https://dtrvantage.com/tools/"
VANTAGE_URL = "https://dtrvantage.com/"
# AGPL-3.0: users must be able to get the corresponding source code.
SOURCE_URL = "https://github.com/dainisf/VantagePDFEditor"
LICENSE_NAME = "GNU AGPL-3.0-or-later"


def as_dict() -> dict:
    return {
        "product": PRODUCT_NAME,
        "short_name": SHORT_NAME,
        "publisher": PUBLISHER,
        "website": WEBSITE,
        "toolkit_url": TOOLKIT_URL,
        "vantage_url": VANTAGE_URL,
        "source_url": SOURCE_URL,
        "license": LICENSE_NAME,
    }
