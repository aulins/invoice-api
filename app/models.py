from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

class Item(BaseModel):
    name: str
    qty: float = Field(gt=0)
    unit: Optional[str] = "pcs"
    unit_price: float = Field(ge=0)
    discount: float = 0
    tax_rate: float = 0.0
    is_tax_inclusive: bool = False

class Charges(BaseModel):
    shipping: float = 0
    service: float = 0
    rounding: float = 0

class CreateInvoice(BaseModel):
    customer: dict
    items: List[Item]
    charges: Charges = Charges()
    discount_total: float = 0
    tax_strategy: str = "per_item"
    currency: str = "IDR"
    issue_date: date
    due_date: Optional[date] = None
    notes: Optional[str] = None
