from odoo import models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def get_stock_by_location(self, location_id, sku=None):
        """Get stock information for products at a specific location.

        Args:
            location_id (int): Stock location ID
            sku (str, optional): Product SKU. If provided, returns only that product.

        Returns:
            dict: Stock information for product(s) at the location
        """
        # Build domain
        domain = [("location_id", "=", location_id)]
        product = None
        
        if sku:
            product = self.env["product.product"].search(
                [("default_code", "=", sku)], limit=1
            )
            if not product:
                return {
                    "error": "Product not found",
                    "message": f"No product found with SKU: {sku}",
                }
            domain.append(("product_id", "=", product.id))
        else:
            domain.append(("product_id.default_code", "!=", False))

        # Get quants
        quants = self.search(domain)

        # Single product mode
        if sku:
            return self._build_single_product_response(quants, product, location_id)

        # All products mode
        return self._build_all_products_response(quants, location_id)

    def _build_single_product_response(self, quants, product, location_id):
        """Build response for single product query."""
        location = self.env["stock.location"].browse(location_id)
        return {
            "message": "Stock information retrieved successfully",
            "product_id": product.id,
            "product_name": product.name,
            "sku": product.default_code,
            "location_id": location.id,
            "location_name": location.complete_name,
            "on_hand_qty": sum(q.quantity for q in quants),
            "reserved_qty": sum(q.reserved_quantity for q in quants),
            "available_qty": sum(q.quantity - q.reserved_quantity for q in quants),
            "stock_details": [self._build_quant_detail(q) for q in quants],
        }

    def _build_all_products_response(self, quants, location_id):
        """Build response for all products query."""
        location = self.env["stock.location"].browse(location_id)
        products_stock = {}

        for quant in quants:
            pid = quant.product_id.id
            if pid not in products_stock:
                products_stock[pid] = {
                    "product_id": pid,
                    "product_name": quant.product_id.name,
                    "sku": quant.product_id.default_code,
                    "on_hand_qty": 0,
                    "reserved_qty": 0,
                    "available_qty": 0,
                    "stock_details": [],
                }

            products_stock[pid]["on_hand_qty"] += quant.quantity
            products_stock[pid]["reserved_qty"] += quant.reserved_quantity
            products_stock[pid]["available_qty"] += (
                quant.quantity - quant.reserved_quantity
            )
            products_stock[pid]["stock_details"].append(self._build_quant_detail(quant))

        return {
            "message": f"Stock information retrieved for {len(products_stock)} products",
            "location_id": location.id,
            "location_name": location.complete_name,
            "total_products": len(products_stock),
            "products": list(products_stock.values()),
        }

    def _build_quant_detail(self, quant):
        """Build detailed information for a single quant."""
        return {
            "quant_id": quant.id,
            "lot_id": quant.lot_id.id if quant.lot_id else None,
            "lot_name": quant.lot_id.name if quant.lot_id else None,
            "package_id": quant.package_id.id if quant.package_id else None,
            "package_name": quant.package_id.name if quant.package_id else None,
            "on_hand_qty": quant.quantity,
            "reserved_qty": quant.reserved_quantity,
            "available_qty": quant.quantity - quant.reserved_quantity,
        }
