"""Pydantic entities of the Borealis Manufacturing synthetic dataset.

These models are the published shape of every JSONL file ``jai_foundry.generate`` writes
and every row ``jai_foundry.load`` inserts into the ``foundry`` Postgres schema.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Anomaly = Literal["none", "price_mismatch", "duplicate", "maverick"]
NewsSignal = Literal["financial_distress", "recall", "sanction", "positive"]
SupplierTier = Literal[1, 2, 3]


class Tenant(BaseModel):
    id: str
    name: str
    region: str


class Supplier(BaseModel):
    id: str
    tenant_id: str
    name: str
    category: str
    tier: SupplierTier
    country: str
    certifications: list[str] = Field(default_factory=list)
    annual_revenue_usd: float
    risk_score: int = Field(ge=0, le=100)
    red_flag: bool = False
    payment_terms_days: int


class PricePoint(BaseModel):
    month: str  # "YYYY-MM"
    price: float


class Item(BaseModel):
    id: str
    tenant_id: str
    sku: str
    name: str
    category: str
    unit_price: float  # latest price, equals price_history[-1].price
    price_history: list[PricePoint]


class Contract(BaseModel):
    id: str
    tenant_id: str
    supplier_id: str
    title: str
    category: str
    start_date: date
    end_date: date
    value_usd: float
    payment_terms_days: int
    clause_text: str


class PurchaseOrder(BaseModel):
    id: str
    tenant_id: str
    supplier_id: str
    item_id: str
    qty: int
    unit_price: float
    total: float
    ordered_at: datetime
    anomaly: Anomaly = "none"


class Invoice(BaseModel):
    id: str
    tenant_id: str
    po_id: str
    amount: float
    invoiced_at: datetime
    anomaly: Anomaly = "none"


class RFxLineItem(BaseModel):
    item_id: str
    name: str
    qty: int


class Bid(BaseModel):
    supplier_id: str
    total: float
    lead_time_days: int


class RFxEvent(BaseModel):
    id: str
    tenant_id: str
    title: str
    category: str
    line_items: list[RFxLineItem]
    invited_supplier_ids: list[str]
    bids: list[Bid]
    awarded_supplier_id: str
    cycle_days: int


class PolicyDoc(BaseModel):
    id: str
    name: str
    markdown: str


class NewsSnippet(BaseModel):
    id: str
    supplier_id: str
    published_at: datetime
    headline: str
    body: str
    signal: NewsSignal


class SellerPersona(BaseModel):
    id: str
    name: str
    style: str
    price_floor_pct: float  # will not go below this percentage of list price
    concession_step_pct: float  # typical concession per negotiation round
    max_rounds: int
