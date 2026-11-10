import frappe
from frappe import _
from frappe.model.document import Document
from frappe.website.utils import cleanup_page_name


class ShopProduct(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from shop.shop.doctype.shop_product_collection.shop_product_collection import ShopProductCollection
		from shop.shop.doctype.shop_product_image.shop_product_image import ShopProductImage
		from shop.shop.doctype.shop_product_option.shop_product_option import ShopProductOption

		collections: DF.TableMultiSelect[ShopProductCollection]
		compare_at_price: DF.Currency
		default_variant: DF.Link | None
		description: DF.TextEditor | None
		has_variants: DF.Check
		highlights: DF.SmallText | None
		images: DF.Table[ShopProductImage]
		item: DF.Link
		item_group: DF.Link | None
		options: DF.Table[ShopProductOption]
		product_name: DF.Data | None
		published: DF.Check
		ranking: DF.Int
		short_description: DF.SmallText | None
		slug: DF.Data | None
	# end: auto-generated types

	def before_insert(self):
		if not self.product_name:
			self.product_name = frappe.db.get_value("Item", self.item, "item_name")
		if not self.slug:
			self.slug = cleanup_page_name(self.product_name)

	def validate(self):
		if frappe.db.get_value("Item", self.item, "variant_of"):
			frappe.throw(_("Publish the template item instead of an individual variant"))
		if (
			self.default_variant
			and frappe.db.get_value("Item", self.default_variant, "variant_of") != self.item
		):
			frappe.throw(_("{0} is not a variant of this product").format(frappe.bold(self.default_variant)))
