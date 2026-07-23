"""Constants and permission identifiers for the product catalogue."""

from enum import StrEnum

from django.db import models


class ProductUnit(models.TextChoices):
    """Identify supported product units of measure."""

    EACH = "EACH", "Each"
    PAIR = "PAIR", "Pair"
    SET = "SET", "Set"
    BOX = "BOX", "Box"
    LITRE = "LITRE", "Litre"
    MILLILITRE = "MILLILITRE", "Millilitre"
    KILOGRAM = "KILOGRAM", "Kilogram"
    GRAM = "GRAM", "Gram"
    METRE = "METRE", "Metre"


class ProductPermissionName(StrEnum):
    """Identify product-catalogue permissions."""

    VIEW_PRODUCT_CATEGORY = "product_catalogue.view_productcategory"
    ADD_PRODUCT_CATEGORY = "product_catalogue.add_productcategory"
    CHANGE_PRODUCT_CATEGORY = "product_catalogue.change_productcategory"

    VIEW_PRODUCT = "product_catalogue.view_product"
    ADD_PRODUCT = "product_catalogue.add_product"
    CHANGE_PRODUCT = "product_catalogue.change_product"

    CHANGE_PRODUCT_PRICE = "product_catalogue.change_product_price"
    DEACTIVATE_PRODUCT = "product_catalogue.deactivate_product"
    REACTIVATE_PRODUCT = "product_catalogue.reactivate_product"
