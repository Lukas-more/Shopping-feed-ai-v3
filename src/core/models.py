from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Param:
    name: str
    value: str

@dataclass
class Delivery:
    delivery_id: str
    price: str
    price_cod: str = ""

@dataclass
class Product:
    item_id: str
    title: str
    description_html: str
    url: str
    image_url: str
    additional_images: List[str] = field(default_factory=list)
    price_vat: str = ""
    category_text: str = ""
    params: List[Param] = field(default_factory=list)
    item_group_id: str = ""
    delivery_date: str = ""
    deliveries: List[Delivery] = field(default_factory=list)
    accessories: List[str] = field(default_factory=list)
    vat: str = ""

    def variant_text(self) -> str:
        if not self.params:
            return ""
        return ", ".join(f"{p.name}: {p.value}" for p in self.params if p.name or p.value)

    def as_prompt_dict(self) -> Dict[str, str]:
        return {
            "item_id": self.item_id,
            "title": self.title,
            "description_html": self.description_html,
            "url": self.url,
            "image_url": self.image_url,
            "price_vat": self.price_vat,
            "category_text": self.category_text,
            "variant_text": self.variant_text(),
            "item_group_id": self.item_group_id,
            "delivery_date": self.delivery_date,
        }
