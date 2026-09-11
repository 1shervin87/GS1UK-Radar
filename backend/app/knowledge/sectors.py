"""Sector definitions, the search query bank and keyword heuristics.

The query bank is deliberately broad ("search the internet in a wide way"). Each query is run
against every enabled connector; results are de-duplicated before analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SECTOR_IDS = ("retail", "construction", "healthcare")


@dataclass(frozen=True)
class Sector:
    id: str
    name: str
    colour: str  # GS1 secondary palette colour for this sector
    description: str
    queries: tuple[str, ...]
    keywords: tuple[str, ...] = field(default_factory=tuple)


SECTORS: dict[str, Sector] = {
    "retail": Sector(
        id="retail",
        name="Retail",
        colour="#F05587",
        description=(
            "Grocery, FMCG, general merchandise, apparel, marketplaces, drinks (DRS), packaging (EPR), "
            "food and product labelling, product safety, Sunrise 2027 and digital product passports."
        ),
        queries=(
            "UK deposit return scheme drinks containers regulations",
            "Exchange for Change deposit return scheme producer barcode registration",
            "Extended Producer Responsibility packaging UK regulations labelling",
            "Windsor Framework Not for EU labelling GB to Northern Ireland goods",
            "UK product safety regulation OPSS General Product Safety",
            "Product Regulation and Metrology Act regulations",
            "UK food labelling regulations change allergen Natasha's Law",
            "HFSS promotions restrictions regulations UK",
            "UK e-invoicing mandate HMRC roadmap",
            "digital product passport UK business ESPR",
            "EU Deforestation Regulation UK exporters due diligence",
            "Border Target Operating Model import controls SPS goods",
            "UK CBAM carbon border adjustment mechanism importers",
            "2D barcodes point of sale retail UK Sunrise 2027",
            "QR codes powered by GS1 UK retailers",
            "online marketplace product safety duties UK",
            "UK retail supply chain traceability regulation",
            "GS1 UK retail",
        ),
        keywords=(
            "deposit return", "drs", "epr", "packaging", "labelling", "labeling", "not for eu",
            "windsor framework", "product safety", "opss", "gpsr", "marketplace", "retailer", "grocery",
            "consumer", "food", "allergen", "hfss", "e-invoicing", "digital product passport", "dpp",
            "eudr", "deforestation", "gtin", "barcode", "qr code", "2d barcode", "sunrise 2027",
        ),
    ),
    "construction": Sector(
        id="construction",
        name="Construction",
        colour="#B78B20",
        description=(
            "Construction products regulation, Building Safety Act and the golden thread, digital product "
            "records and passports, CCPI, PAS 2000, UKCA/CE marking and builders' merchants."
        ),
        queries=(
            "construction products regulation reform UK MHCLG",
            "General Safety Requirement construction products regulations",
            "Building Safety Regulator update golden thread information",
            "Building Safety Act secondary legislation construction products",
            "national regulator for construction products OPSS enforcement",
            "construction product information digital product record QR code",
            "Code for Construction Product Information CCPI",
            "PAS 2000 construction products safe products to market",
            "UKCA CE marking construction products deadline",
            "Construction Products Regulations amendment UK",
            "digital product passport construction products EU",
            "higher-risk buildings regulations golden thread digital",
            "construction product traceability unique identifier",
            "GS1 UK construction",
        ),
        keywords=(
            "construction", "building safety", "golden thread", "bsr", "mhclg", "ccpi", "pas 2000",
            "ukca", "declaration of performance", "construction product", "builders", "merchant",
            "higher-risk building", "hackitt", "grenfell", "digital product record",
        ),
    ),
    "healthcare": Sector(
        id="healthcare",
        name="Healthcare",
        colour="#00B6DE",
        description=(
            "MHRA medical device and IVD regulation (UDI, registration, post-market surveillance), medicines "
            "packaging and barcodes, NHS Scan4Safety, MDOR, NHS Supply Chain and eProcurement."
        ),
        queries=(
            "MHRA medical devices regulations amendment Great Britain",
            "MHRA unique device identifier UDI requirement",
            "MHRA post-market surveillance medical devices guidance",
            "MHRA in vitro diagnostic devices regulation update",
            "MHRA medicines packaging barcode falsified medicines UK",
            "NHS England Scan4Safety barcode scanning trusts",
            "Medical Device Outcomes Registry MDOR mandatory data",
            "NHS Supply Chain inventory management systems programme",
            "NHS eProcurement standards GLN PEPPOL",
            "DHSC MedTech strategy patient implant management",
            "NHS 10 Year Health Plan digital patient safety identification",
            "NHS Federated Data Platform supply chain data",
            "implant cards medical devices UK requirement",
            "Scan4Safety Scotland Wales Northern Ireland",
            "GS1 UK healthcare",
        ),
        keywords=(
            "mhra", "medical device", "udi", "ivd", "medicine", "pharmacy", "nhs", "scan4safety",
            "mdor", "implant", "patient safety", "hospital", "trust", "dhsc", "supply chain", "gsrn",
            "wristband", "eprocurement", "peppol", "fmd", "falsified", "vigilance", "registry",
        ),
    ),
}

CROSS_SECTOR_QUERIES: tuple[str, ...] = (
    "GS1 UK",
    "GS1 standards UK regulation",
    "barcode requirement new UK regulation",
    "unique identifier traceability UK legislation",
    "QR code labelling requirement UK regulation",
    "UK supply chain data standards mandate government",
    "UK product traceability consultation",
    "statutory instrument laid product identification labelling",
)

GS1_KEYWORDS: tuple[str, ...] = (
    "gs1", "gtin", "gln", "sscc", "udi", "barcode", "bar code", "qr code", "2d code", "data matrix",
    "datamatrix", "digital link", "unique identifier", "unique device identifier", "traceability",
    "product identifier", "serialisation", "serialization", "epcis", "gdsn", "digital product passport",
    "digital product record", "data carrier", "scan", "labelling", "labeling", "recall",
)


def all_queries() -> list[tuple[str | None, str]]:
    """Return (sector_hint, query) pairs covering every sector plus cross-sector queries."""
    out: list[tuple[str | None, str]] = []
    for sector in SECTORS.values():
        out.extend((sector.id, q) for q in sector.queries)
    out.extend((None, q) for q in CROSS_SECTOR_QUERIES)
    return out


def load_context_brief() -> str:
    return (Path(__file__).parent / "gs1_context.md").read_text(encoding="utf-8")


def guess_sectors(text: str) -> list[str]:
    """Cheap keyword heuristic used only to pre-tag candidates before the LLM triage."""
    lowered = text.lower()
    hits = [s.id for s in SECTORS.values() if any(k in lowered for k in s.keywords)]
    return hits


def gs1_signal_score(text: str) -> int:
    lowered = text.lower()
    return sum(1 for k in GS1_KEYWORDS if k in lowered)
