class ScraperError(RuntimeError):
    """Base class for user-actionable scraper failures."""


class ManifestError(ScraperError):
    """The input manifest is invalid."""


class BrowserAutomationError(ScraperError):
    """Amazon could not be scraped or verified safely."""


class PriceValidationError(ScraperError):
    """Price evidence is missing, ambiguous, or inconsistent."""


class ContentValidationError(ScraperError):
    """AI-authored product content does not satisfy the contract."""


class ImageEvidenceError(ScraperError):
    """Verified product imagery could not be prepared for visual grounding."""


class ShopifyError(ScraperError):
    """A Shopify request or mutation failed."""


class NeedsAttention(ScraperError):
    """Human attention is required before the product can continue."""
