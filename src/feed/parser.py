from lxml import etree as ET
from src.core.models import Product, Param, Delivery
from src.utils.xml_helpers import inner_xml


def parse_heureka_feed(xml_text: str) -> list[Product]:
    parser = ET.XMLParser(recover=True, encoding="utf-8")
    root = ET.fromstring(xml_text.encode("utf-8"), parser=parser)
    products: list[Product] = []

    for item in root.findall(".//SHOPITEM"):
        desc_elem = item.find("DESCRIPTION")
        deliveries = []
        for d in item.findall("DELIVERY"):
            deliveries.append(Delivery(
                delivery_id=d.findtext("DELIVERY_ID", default=""),
                price=d.findtext("DELIVERY_PRICE", default=""),
                price_cod=d.findtext("DELIVERY_PRICE_COD", default=""),
            ))
        params = []
        for p in item.findall("PARAM"):
            params.append(Param(
                name=p.findtext("PARAM_NAME", default=""),
                value=p.findtext("VAL", default=""),
            ))
        products.append(Product(
            item_id=item.findtext("ITEM_ID", default=""),
            title=item.findtext("PRODUCTNAME", default=""),
            description_html=inner_xml(desc_elem),
            url=item.findtext("URL", default=""),
            image_url=item.findtext("IMGURL", default=""),
            additional_images=[x.text or "" for x in item.findall("IMGURL_ALTERNATIVE")],
            price_vat=item.findtext("PRICE_VAT", default=""),
            category_text=item.findtext("CATEGORYTEXT", default=""),
            params=params,
            item_group_id=item.findtext("ITEMGROUP_ID", default=""),
            delivery_date=item.findtext("DELIVERY_DATE", default=""),
            deliveries=deliveries,
            accessories=[x.text or "" for x in item.findall("ACCESSORY")],
            vat=item.findtext("VAT", default=""),
        ))
    return products
