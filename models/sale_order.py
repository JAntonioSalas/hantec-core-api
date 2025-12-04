from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def get_shipping_info(self):
        """Retrieve shipping information for the sale order instance.

        This method gathers shipping information related to the sale order, including
        delivery address details and shipping records.

        Returns:
            dict: A dictionary containing the shipping information.
        """
        # Delivery address data
        shipping_address = self.partner_shipping_id
        fields = [
            "name",
            "phone",
            "email",
            "street",
            "street2",
            "city",
            "state_id",
            "zip",
            "country_id",
        ]
        address_data = shipping_address.read(fields)[0] if shipping_address else {}

        # Invoice address data
        invoice_address = self.partner_invoice_id
        invoice_address_data = (
            invoice_address.read(fields)[0] if invoice_address else {}
        )

        # Get related shipping records
        pickings = self.picking_ids

        # Prepare shipping data for the response
        shipping_data = []
        last_picking = None
        for picking in pickings:
            detailed_lines = []
            for move_line in picking.move_line_ids:
                detailed_lines.append(
                    {
                        "id": move_line.id,
                        "product_id": move_line.product_id.id,
                        "product_name": move_line.product_id.name,
                        "quantity": move_line.quantity,
                        "current_quant_id": move_line.quant_id.id,
                        "current_quant_name": move_line.quant_id.display_name,
                    }
                )

            lines_data = [
                {
                    "product_id": line.product_id.id,
                    "product": line.product_id.name,
                    "quantity": line.product_uom_qty,
                    "done": line.quantity,
                    "name": line.name,
                }
                for line in picking.move_ids
            ]

            shipping_info = {
                "name": picking.name,
                "scheduled_date": picking.scheduled_date,
                "state": picking.state,
                "lines": lines_data,
                "address_data": address_data,
                "invoice_address_data": invoice_address_data,
            }
            shipping_data.append(shipping_info)
            last_picking = picking

        if last_picking:
            shipping_data.append(
                {
                    "sales_team": self.team_id.id,
                    "market_place_reference": self.channel_order_reference,
                    "sale_order_name": self.name,
                    "picking_id": last_picking.id,
                    "picking_name": last_picking.name,
                }
            )

        return {"message": "Shipping data retrieved", "shipping_data": shipping_data}
