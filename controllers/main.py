from odoo.http import request, Controller, route
from odoo import fields
import logging

logger = logging.getLogger(__name__)


class MainController(Controller):
    @route("/search_contact", methods=["POST"], type="json", auth="user")
    def search_contact(self):
        """Searches for contact based on multiple parameters.

        This function searches for a contacts using various parameters such as email,
        phone, mobile, and name. It implements special handling for phone numbers to ensure
        accurate matching by normalizing and comparing phone digits.

        JSON request body:
            - email (str, optional): The email of the contact.
            - phone (str, optional): The phone number of the contact.
            - mobile (str, optional): The mobile number of the contact.
            - name (str, optional): The name of the contact.
            - strict_phone (bool, optional): If True, performs strict phone matching.
              If False (default), matches last 10 digits

        Returns:
            dict: A dictionary with search results and contact details.
        """
        data = request.get_json_data()
        company_id = data.get("company_id") or request.env.company.id

        contacts = (
            request.env["res.partner"]
            .with_company(company_id)
            .search_contacts_by_params(data)
        )

        contact_data = contacts.read(
            ["name", "email", "phone", "mobile", "create_date"]
        )

        return {
            "message": f"Found {len(contacts)} contacts matching the criteria.",
            "contacts": contact_data,
        }

    @route("/create_contact", methods=["POST"], type="json", auth="user")
    def create_contact(self):
        """Combines the logic of searching and creating contacts based on email, phone, or store name.

        This function first checks if a contact already exists based on the provided
        email, phone, or store name. If a matching contact is found, it returns the contact ID.
        If no matching contact is found, it creates a new contact with the provided data.

        JSON request body:
            - email (str, optional): The email of the contact.
            - phone (str, optional): The phone number of the contact.
            - store_name (str, optional): The store name associated with the contact.
            - name (str, optional): The name of the contact.
            - partner_id (int, optional): The parent ID for the contact.
            - contact_data (dict, optional): Additional contact data.

        JSON response:
            - message (str): A message indicating whether a contact was found or created.
            - contact_id (int): The ID of the found or created contact.

        Returns:
            dict: A dictionary with a message and the contact ID.

        """
        env = request.env
        data = request.get_json_data()
        company_id = data.get("company_id") or env.company.id

        partner = env["res.partner"].with_company(company_id)

        existing_contacts = partner.search_contacts_by_params(data)

        if existing_contacts:
            contact = existing_contacts[-1]
            logger.info("Contact found with ID %s", contact.id)
            return {
                "message": f"Contact found with ID: {contact.id}",
                "contact_id": contact.id,
                "is_new": False,
            }

        store_name = data.get("store_name")
        if store_name:
            store_domain = [("name", "=ilike", f"%{store_name}")]
            parent_contact = partner.search(store_domain, limit=1)

            if parent_contact:
                return {
                    "message": f"Store found with ID: {parent_contact.id}.",
                    "contact_id": parent_contact.id,
                    "is_new": False,
                }

            partner_id = data.get("partner_id")
            if partner_id:
                data.setdefault("contact_data", {})
                data["contact_data"].update(
                    {
                        "type": "other",
                        "parent_id": partner_id,
                    }
                )

        contact_vals = data.get("contact_data", {})

        for field in ("name", "email", "phone", "mobile"):
            val = data.get(field)
            if val:
                contact_vals.setdefault(field, val)

        contact_vals["company_id"] = company_id

        new_contact = partner.create(contact_vals)
        logger.info("Contact created with ID %s", new_contact.id)

        return {
            "message": f"New contact created with ID {new_contact.id}",
            "contact_id": new_contact.id,
            "is_new": True,
        }

    @route(
        "/update_contact/<model('res.partner'):partner>",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def update_contact(self, partner=False):
        """Updates a contact with new values.

        This function updates the details of a specified contact using the values
        provided in the JSON request body.

        JSON request body:
            - partner_id (int): The ID of the contact to be updated.
            - update_vals (dict): A dictionary containing the values to be updated.

        JSON response:
            - message (str): A message indicating that the contact has been successfully updated.

        Returns:
            dict: A dictionary with a success message.

        """
        update_vals = request.get_json_data().get("update_vals")  # Values to update
        partner.write(update_vals)  # Update the contact with the new values
        logger.debug("Contact updated with ID %s", partner.id)

        return {"message": f"Contact with ID: {partner.id} successfully updated."}

    @route(
        ["/create_delivery_address", "/create_invoice_address"],
        methods=["POST"],
        type="json",
        auth="user",
    )
    def create_address(self):
        """Creates or updates the billing or delivery address for a given partner.

        This function creates or updates the billing or delivery address of a specified partner
        using the details provided in the JSON request body.

        JSON request body:
            - partner_id (int): The ID of the partner.
            - address_data (dict): A dictionary containing the address details.
            - address_type (str): The type of address to update or create ("invoice" or "delivery").
            - only_create (bool, optional): A boolean indicating if only creation should be done,
            omitting the update of an existing address (default is False).

        JSON response:
            - message (str): A message indicating that the address has been successfully created or updated.
            - address_id (int): The ID of the created or updated address.

        Returns:
            dict: A dictionary with a success message and the address ID.
        """
        env = request.env
        data = request.get_json_data()
        partner_id = data.get("partner_id")
        address_data = data.get("address_data")
        address_type = data.get("address_type")  # "invoice" or "delivery"
        only_create = data.get("only_create", False)  # Boolean to omit address update
        company_id = data.get("company_id") or request.env.company.id

        # Search for existing address of the given type
        address = (
            env["res.partner"]
            .with_company(company_id)
            .search(
                [("parent_id", "=", partner_id), ("type", "=", address_type)], limit=1
            )
        )

        if address and not only_create:
            # Update existing address
            address.write(address_data)
        else:
            # Add a new address
            address_data.update({"type": address_type, "parent_id": partner_id})
            address = env["res.partner"].with_company(company_id).create(address_data)

        return {
            "message": f"{address_type} address successfully updated/created.",
            "address_id": address.id,
        }

    @route("/create_sale_order", methods=["POST"], type="json", auth="user")
    def create_sale_order(self):
        """Creates a sale order.

        This function creates a sale order using the details provided in the JSON request body.
        The required fields include the customer ID and a list of product lines.

        JSON request body:
            Required fields:
                - partner_id (int): The ID of the customer.
                - product_lines (list of dicts): A list of dictionaries containing product details:
                    - product_id (int): The ID of the product.
                    - product_qty (float): The quantity of the product.
                    - price_unit (float, optional): The unit price of the product (default is 0).
                    - discount (float, optional): The discount on the product (default is 0).
                    - tax_id (int, optional): The tax ID for the product (default is 2).

            Optional fields:
                Any additional fields provided in the request will be considered optional
                and will be added to the sale order if they exist in the sale.order model.

        Returns:
            dict: A dictionary with a success message, the sale order ID, and the sale order name.
        """
        required_fields = ["partner_id", "product_lines"]
        data = request.get_json_data()

        company_id = data.get("company_id") or request.env.company.id

        sale_order_data = {field: data[field] for field in required_fields}

        # Add optional fields
        for field, value in data.items():
            if field not in required_fields and field != "company_id":
                sale_order_data[field] = value

        # Prepare order lines
        order_lines = [
            (
                0,
                0,
                {
                    "product_id": line["product_id"],
                    "product_uom_qty": line["product_qty"],
                    "price_unit": line.get("price_unit", 0),
                    "discount": line.get("discount", 0),
                    "tax_id": [(6, 0, [line.get("tax_id", 2)])],
                },
            )
            for line in sale_order_data["product_lines"]
        ]

        sale_order_vals = {
            "partner_id": sale_order_data["partner_id"],
            "l10n_mx_edi_cfdi_to_public": True,
            "order_line": order_lines,
        }

        if "usage" in data:
            sale_order_vals["l10n_mx_edi_usage"] = data["usage"]

        if "payment_method_id" in data:
            sale_order_vals["l10n_mx_edi_payment_method_id"] = data["payment_method_id"]

        # Add all other valid fields
        for field, value in sale_order_data.items():
            if field not in ["partner_id", "product_lines"]:
                sale_order_vals[field] = value

        # Create sale order
        sale_order = (
            request.env["sale.order"].with_company(company_id).create(sale_order_vals)
        )

        return {
            "message": f"Sale order created with ID: {sale_order.id}, Team ID: {sale_order.team_id.id}",
            "sale_order_id": sale_order.id,
            "sale_order_name": sale_order.name,
        }

    @route(
        "/update_sale_order/<model('sale.order'):order>",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def update_sale_order(self, order=False):
        """Updates a sale order with a tracking number.

        This function updates the tracking number of a specified sale order using the details
        provided in the JSON request body.

        URL parameter:
            - order (sale.order): The sale order model instance.

        JSON response:
            - message (str): A message indicating that the sale order has been successfully updated.

        Returns:
            dict: A dictionary with a success message.

        """
        data = request.get_json_data()
        order.write(data)

        return {
            "message": f"The order with ID: {order.id} has been successfully updated."
        }

    @route(
        "/validate_delivery/<model('sale.order'):order>",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def validate_delivery(self, order=False):
        """Validates the delivery associated with a sale order.

        This function finds the pending delivery orders associated with the sale order,
        sets the quantity done equal to the reserved quantity,
        and validates the picking.

        URL parameter:
            - order (sale.order): The sale order model instance.

        JSON response:
            - message (str): A message indicating the result.
            - validated_pickings (list): List of validated picking IDs.

        Returns:
            dict: A dictionary with the result.
        """
        # Find pickings that are confirmed (Waiting) or assigned (Ready)
        pickings = order.picking_ids.filtered(
            lambda p: p.state in ["confirmed", "assigned"]
        )

        if not pickings:
            return {"message": "No pending deliveries found for this order."}

        validated_ids = []
        for picking in pickings:
            # Set quantities done.
            for move in picking.move_ids:
                # Set the quantity done to match the demand/reserved
                if move.quantity == 0:
                    move.quantity = move.product_uom_qty

            # Validate the picking
            picking.with_company(order.company_id.id).with_context(
                skip_backorder=True
            ).button_validate()
            validated_ids.append(picking.id)

        return {
            "message": f"Successfully validated {len(validated_ids)} delivery orders.",
            "validated_pickings": validated_ids,
        }

    @route(
        "/return_delivery/<model('sale.order'):order>",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def return_delivery(self, order=False):
        """Creates a return for the delivery associated with a sale order.

        This function finds the done delivery orders associated with the sale order
        and creates a return picking.

        URL parameter:
            - order (sale.order): The sale order model instance.

        JSON request body:
            - validate_return (bool, optional): If True, automatically validates the return picking (default False).

        JSON response:
            - message (str): A message indicating the result.
            - return_picking_id (int): The ID of the created return picking.

        Returns:
            dict: A dictionary with the result.
        """
        # Find the delivery that is already done
        picking = order.picking_ids.filtered(
            lambda p: p.state == "done" and p.picking_type_code == "outgoing"
        )

        picking = picking[:1]  # Take only the first one if multiple

        # Create the return wizard context
        context = {
            "active_ids": [picking.id],
            "active_id": picking.id,
            "active_model": "stock.picking",
        }

        # Initialize the return wizard with default values explicitly
        ReturnPicking = (
            request.env["stock.return.picking"]
            .with_company(order.company_id.id)
            .with_context(context)
        )
        default_vals = ReturnPicking.default_get(ReturnPicking._fields.keys())
        return_wizard = ReturnPicking.create(default_vals)

        data = request.get_json_data()
        return_lines = data.get("return_lines")

        # Handle partial returns
        if return_lines:
            # Create a map for easy lookup: {product_id: quantity_to_return}
            requested_products = {
                int(line["product_id"]): float(line["quantity"])
                for line in return_lines
            }

            for line in return_wizard.product_return_moves:
                prod_id = line.product_id.id

                if prod_id in requested_products:
                    line.write({"quantity": requested_products[prod_id]})
                else:
                    # If the product is not in our request list, set quantity to 0 to exclude it
                    line.write({"quantity": 0})

        else:
            # Return all products
            for line in return_wizard.product_return_moves:
                if line.quantity == 0:
                    line.write({"quantity": line.move_id.quantity})

        # Execute the return action
        return_action = return_wizard.action_create_returns()
        return_picking_id = return_action.get("res_id")

        return_picking = (
            request.env["stock.picking"]
            .with_company(order.company_id.id)
            .browse(return_picking_id)
        )

        # Validate if requested
        validate_return = data.get("validate_return", False)

        if validate_return:
            # Set quantities done equal to demand
            for move in return_picking.move_ids:
                move.quantity = move.product_uom_qty

            return_picking.button_validate()
            return {
                "message": f"Return created and validated successfully with ID: {return_picking.id}.",
                "return_picking_id": return_picking.id,
                "name": return_picking.name,
            }

        return {
            "message": f"Return created successfully with ID: {return_picking.id}.",
            "return_picking_id": return_picking.id,
            "name": return_picking.name,
        }

    @route(
        "/invoice_sale_order/<model('sale.order'):order>",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def invoice_sale_order(self, order=False):
        """Creates an invoice for a sale order.

        This function creates an invoice for a specified sale order by its model
        passed in the URL, and creates the invoice order.

        URL parameter:
            - order (sale.order): The sale order model instance.

        JSON request body:
            - code_usage (str): The code usage for the invoice (optional, default is "G01").
            - journal_id (str): The ID for the journey (optional).

        JSON response:
            - message (str): A message indicating that the invoice has been successfully created.
            - list_invoices (list): A list of dictionaries containing the name and date of the created invoices.

        Returns:
            dict: A dictionary with a success message and a list of created invoices.

        """
        data = request.get_json_data()
        context = {
            "active_model": "sale.order",
            "active_ids": [order.id],
            "active_id": order.id,
        }
        invoice_wizard = (
            request.env["sale.advance.payment.inv"]
            .with_company(order.company_id.id)
            .with_context(**context)
            .create({"advance_payment_method": "delivered"})
        )

        # Create invoice
        invoice_wizard.create_invoices()
        invoices = order.invoice_ids.filtered(lambda inv: inv.state == "draft")

        vals = {
            "l10n_mx_edi_cfdi_to_public": data.get("cfdi_to_public", False),
            "l10n_mx_edi_usage": data.get("code_usage", "G01"),
        }

        if data.get("cfdi_origin_id"):
            vals["l10n_mx_edi_cfdi_origin"] = data.get("cfdi_origin_id")

        mapped_keys = ["cfdi_to_public", "code_usage", "cfdi_origin_id"]

        # Add any other data from the request directly to the invoice values
        for key, value in data.items():
            if key not in mapped_keys:
                vals[key] = value

        # Process only the newly created invoice
        if invoices:
            invoices.write(vals)
            invoices.action_post()

        return {
            "message": "Invoice created",
            "list_invoices": invoices.read(["name", "date"]),
        }

    @route(
        "/invoice_purchase_order/<model('purchase.order'):order>",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def invoice_purchase_order(self, order=False):
        """Creates a vendor bill for a purchase order.

        This function creates a vendor bill for a specified purchase order.

        URL parameter:
            - order (purchase.order): The purchase order model instance.

        JSON request body:
            - post (bool, optional): Whether to post/confirm the bill after creation (default False).

        JSON response:
            - message (str): Success message.
            - invoice_id (int): The ID of the created vendor bill.
            - invoice_name (str): The name of the vendor bill.
            - state (str): The state of the invoice

        Returns:
            dict: A dictionary with the result.
        """
        data = request.get_json_data()
        company_id = order.company_id.id
        post_invoice = data.get("post", False)

        # Create vendor bill directly from purchase order
        order.with_company(company_id).action_create_invoice()

        invoice = order.invoice_ids.filtered(lambda inv: inv.state == "draft")[:1]

        # Post the invoice if requested
        if post_invoice:
            invoice_date = data.get("invoice_date", fields.Date.context_today(invoice))
            invoice.with_company(company_id).write({"invoice_date": invoice_date})
            invoice.with_company(company_id).action_post()

        return {
            "message": f"Vendor bill created for purchase order {order.name}.",
            "invoice_id": invoice.id,
            "invoice_name": invoice.name,
            "state": invoice.state,
        }

    @route(
        "/register_payment_invoice/<model('account.move'):invoice>",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def register_payment(self, invoice=False):
        """Registers a payment for an invoice.

        This function registers a payment for a specified invoice using the details
        provided in the JSON request body.

        URL parameter:
            - invoice (account.move): The invoice model instance.

        JSON request body:
            - amount (float): The amount to be paid.
            - journal_id (int): The ID of the payment journal.
            - payment_method_id (int): The ID of the payment method.

        JSON response:
            - success (str): A message indicating that the payment has been successfully registered.

        Returns:
            dict: A dictionary with a success message.

        """
        data = request.get_json_data()
        amount = data.get("amount")
        journal_id = data.get("journal_id")
        payment_method_id = data.get("payment_method_id")

        register_payment_wizard = (
            request.env["account.payment.register"]
            .with_company(invoice.company_id.id)
            .with_context(active_model="account.move", active_ids=[invoice.id])
        )

        wizard = register_payment_wizard.create(
            {
                "amount": amount,
                "journal_id": journal_id,
                "l10n_mx_edi_payment_method_id": payment_method_id,
                "communication": invoice.name,
            }
        )

        # Register the payment
        wizard.action_create_payments()

        return {"success": "The payment has been successfully registered."}

    @route(
        "/get_shipping_info/<model('sale.order'):order>",
        methods=["GET"],
        type="json",
        auth="user",
    )
    def get_shipping_info(self, order=False):
        """Retrieves shipping information for a given sale order.

        This function gathers shipping information related to the specified sale order,
        including delivery address details and shipping records.

        URL parameter:
            - order (sale.order): The sale order model instance.

        JSON response:
            - message (str): A message indicating that the shipping data has been successfully retrieved.
            - shipping_data (list): A list of dictionaries containing shipping information.

        Returns:
            dict: A dictionary with a success message and the shipping data.
        """
        return order.get_shipping_info()

    @route(
        "/download_invoice/<model('account.move'):invoice>",
        methods=["GET"],
        type="http",
        auth="user",
    )
    def download_invoice(self, invoice=False):
        """Downloads an invoice as PDF or XML based on format parameter.

        URL parameter:
            - invoice (account.move): The invoice model instance.
            - format (str): 'pdf' (default) or 'xml'
        """
        format_type = request.params.get("format", "pdf")

        if format_type == "xml":
            attachment = request.env["ir.attachment"].search(
                [
                    ("res_model", "=", "account.move"),
                    ("res_id", "=", invoice.id),
                    ("mimetype", "=", "application/xml"),
                ],
                limit=1,
                order="id desc",
            )
            if not attachment:
                return request.not_found()

            content = attachment.raw
            filename = attachment.name or f"invoice_{invoice.id}.xml"
            content_type = "application/xml"
        else:
            content, _ = request.env["ir.actions.report"]._render_qweb_pdf(
                "account.report_invoice_with_payments", [invoice.id]
            )
            filename = f"invoice_{invoice.id}.pdf"
            content_type = "application/pdf"

        http_headers = [
            ("Content-Type", content_type),
            ("Content-Length", len(content)),
            ("Content-Disposition", f'attachment; filename="{filename}"'),
        ]
        return request.make_response(content, headers=http_headers)

    @route(
        "/stamp_invoice/<model('account.move'):invoice>",
        methods=["POST"],
        auth="user",
        type="json",
    )
    def stamp_invoice(self, invoice=None):
        """Stamps an invoice.

        This function attempts to stamp an invoice identified by its ID. If the invoice
        is already stamped, it returns the UUID of the stamped invoice. Otherwise, it
        tries to stamp the invoice and returns the result.

        URL parameter:
            - invoice (account.move): The invoice model instance.

        JSON response:
            - If the invoice is already stamped:
                - message (str): A message indicating that the invoice is already stamped.
                - UUID (str): The UUID of the stamped invoice.
            - If the stamping process is successful:
                - success (str): A message indicating that the invoice has been successfully stamped.
                - UUID (str): The UUID of the stamped invoice.
            - If the stamping process fails:
                - error (str): A message indicating that the stamping process failed.
                - details (str): The error message from the stamping process.

        Returns:
            dict: A dictionary with the result of the stamping process.

        """
        # Check if the invoice is already stamped
        if invoice.l10n_mx_edi_cfdi_uuid:
            return {
                "message": "The invoice is already stamped.",
                "UUID": invoice.l10n_mx_edi_cfdi_uuid,
            }

        send_email = request.get_json_data().get("send_email", False)

        # We use the account.move.send.wizard to process EDI documents (stamping)
        # We simulate the wizard action to trigger the CFDI generation
        send_wizard = (
            request.env["account.move.send.wizard"]
            .with_company(invoice.company_id.id)
            .create(
                {
                    "move_id": invoice.id,
                    "sending_methods": ["email"] if send_email else False,
                }
            )
        )

        # Call the action to send and print (which includes stamping)
        send_wizard.action_send_and_print(allow_fallback_pdf=False)

        # Check again if the invoice was successfully stamped
        if invoice.l10n_mx_edi_cfdi_uuid:
            return {
                "success": "The invoice has been successfully stamped.",
                "UUID": invoice.l10n_mx_edi_cfdi_uuid,
            }

        # If not stamped immediately, check for errors
        error_message = "Check the chatter for details."
        if hasattr(invoice, "edi_error_message") and invoice.edi_error_message:
            error_message = invoice.edi_error_message

        return {
            "error": "The invoice stamping failed.",
            "details": error_message,
        }

    @route(
        "/create_credit_note/<model('account.move'):invoice>",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def create_credit_note(self, invoice=None):
        """Creates a credit note for an invoice.

        This function creates a credit note (reversal) for a specified invoice using the
        account.move.reversal wizard.

        URL parameter:
            - invoice (account.move): The invoice model instance to be reversed.

        JSON request body:
            - reason (str): The reason for the credit note.
            - date (str, optional): The reversal date (YYYY-MM-DD).
            - journal_id (int, optional): The ID of the specific journal to use.
            - confirm (bool, optional): Whether to confirm the credit note after creation.

        JSON response:
            - message (str): A message indicating the result.
            - credit_note_id (int): The ID of the created credit note.

        Returns:
            dict: A dictionary with the result.
        """
        data = request.get_json_data()
        reason = data.get("reason", "revertir")
        journal_id = data.get("journal_id", 1)
        confirm = data.get("confirm", False)

        # Context is required for the wizard to know which invoice to reverse
        ctx = {
            "active_model": "account.move",
            "active_ids": [invoice.id],
            "active_id": invoice.id,
        }

        wizard_vals = {
            "reason": reason,
            "journal_id": journal_id,
        }

        # Create the wizard
        reversal_wizard = (
            request.env["account.move.reversal"]
            .with_company(invoice.company_id.id)
            .with_context(**ctx)
            .create(wizard_vals)
        )

        # Execute the reversal action
        action = reversal_wizard.refund_moves()

        credit_note_id = None

        # Attempt to retrieve the created credit note ID from the action returned
        if isinstance(action, dict):
            if action.get("res_id"):
                credit_note_id = action["res_id"]
            elif action.get("domain"):
                domain = action["domain"]
                credit_notes = (
                    request.env["account.move"]
                    .with_company(invoice.company_id.id)
                    .search(domain, limit=1)
                )
                if credit_notes:
                    credit_note_id = credit_notes.id

        # Fallback if action parsing fails
        if not credit_note_id:
            # Find the move that has this invoice as the reversed entry
            credit_note = (
                request.env["account.move"]
                .with_company(invoice.company_id.id)
                .search(
                    [("reversed_entry_id", "=", invoice.id)],
                    order="id desc",
                    limit=1,
                )
            )
            if credit_note:
                credit_note_id = credit_note.id

        # Confirm if requested
        if confirm:
            credit_note = request.env["account.move"].browse(credit_note_id)
            credit_note.with_company(invoice.company_id.id).action_post()

        return {
            "message": "Credit note created successfully.",
            "credit_note_id": credit_note_id,
            "name": credit_note.name,
            "state": credit_note.state,
            "cfdi_origin": credit_note.l10n_mx_edi_cfdi_origin,
        }

    @route(
        "/update_credit_note/<model('account.move'):credit_note>",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def update_credit_note(self, credit_note=None):
        """Updates and confirms a draft credit note.

        This function updates a draft credit note with provided values and then confirms (posts) it.
        It specifically handles mapping for common Mexican localization fields if provided.

        URL parameter:
            - credit_note (account.move): The credit note model instance.

        JSON request body:
            - update_vals (dict, optional): Values to update
            - confirm (bool, optional): Whether to confirm the credit note after updating.

        JSON response:
            - message (str): Success message.
            - credit_note_id (int): ID of the confirmed credit note.
            - name (str): The name/number of the confirmed credit note.
            - state (str): The state of the confirmed credit note.
        """
        data = request.get_json_data()
        update_vals = data.get("update_vals", {})
        confirm = data.get("confirm", False)

        if update_vals:
            field_mapping = {
                "usage": "l10n_mx_edi_usage",
                "cfdi_public": "l10n_mx_edi_cfdi_to_public",
                "cfdi_origin": "l10n_mx_edi_cfdi_origin",
                "payment_method_id": "l10n_mx_edi_payment_method_id",
            }
            vals_to_write = {}
            for key, value in update_vals.items():
                vals_to_write[field_mapping.get(key, key)] = value

            credit_note.with_company(credit_note.company_id.id).write(vals_to_write)

        # Confirm (Post) the credit note
        if confirm:
            credit_note.with_company(credit_note.company_id.id).action_post()

        return {
            "message": f"Credit note {credit_note.name} confirmed successfully.",
            "credit_note_id": credit_note.id,
            "name": credit_note.name,
            "cfdi_origin": credit_note.l10n_mx_edi_cfdi_origin,
            "state": credit_note.state,
        }

    @route(
        "/send_invoice_by_email/<model('account.move'):invoice>",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def send_invoice_by_email(self, invoice=False):
        """Sends an invoice by email.

        This function sends an invoice identified by its ID via email, using the
        invoice sending wizard in Odoo.

        URL parameter:
            - invoice (account.move): The invoice model instance.

        JSON response:
            - success (str): A message indicating that the invoice has been successfully sent.

        Returns:
            dict: A dictionary with a success message.

        """
        send_wizard = (
            request.env["account.move.send.wizard"]
            .with_company(invoice.company_id.id)
            .create({"move_id": invoice.id, "sending_methods": ["email"]})
        )

        # Send the invoice by email
        send_wizard.action_send_and_print(allow_fallback_pdf=False)

        return {"success": "The invoice has been successfully sent."}

    @route(
        "/confirm_sale_order/<model('sale.order'):order>",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def confirm_sale_order(self, order=False):
        """Confirms a sale order.

        This function confirms a sale order identified by its model instance
        passed in the URL, and confirms the order.

        URL parameter:
            - order (sale.order): The sale order model instance.

        JSON response:
            - message (str): A confirmation message indicating the action performed.

        Returns:
            dict: A dictionary with a confirmation message.

        """
        # Confirm the sale order
        order.with_company(order.company_id.id).action_confirm()

        return {"message": f"Sale order with ID: {order.id} successfully confirmed."}

    @route(
        [
            "/create_schedule_activity/<model('sale.order'):order>",
            "/create_schedule_activity_invoice/<model('account.move'):order>",
        ],
        methods=["POST"],
        type="json",
        auth="user",
    )
    def create_schedule_activity(self, order=False):
        """Creates a scheduled activity associated with an existing sale order or invoice.

        This function creates a scheduled activity in Odoo related to a specific sale order
        or invoice, using the details provided in the JSON request body.

        JSON request body:
            - activity_type_id (int): ID of the activity type.
            - summary (str, optional): Summary text of the activity.
            - date_deadline (str): Deadline date for the activity in 'YYYY-MM-DD' format.
            - note (str, optional): Note for the activity.
            - user_id (int, optional): ID of the user assigned to the activity. If not provided, the current user's ID is used.

        JSON response:
            - message (str): A confirmation message with the ID of the scheduled activity and the sale order or invoice ID.

        Returns:
            dict: A dictionary with a confirmation message.
        """
        data = request.get_json_data()
        activity = order.activity_schedule(
            activity_type_id=data.get("activity_type_id"),
            summary=data.get("summary", ""),
            note=data.get("note", ""),
            date_deadline=data.get("date_deadline"),
            user_id=data.get("user_id", request.env.uid),
        )

        return {
            "message": f"Scheduled activity created with ID: {activity.id} for sale order {order.id}."
        }

    @route(
        "/send_message_sale_order/<model('sale.order'):order>",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def send_message_sale_order(self, order=False):
        """Sends a message to a specific sale order.

        This function posts a message to the chatter of a sale order identified by its model
        passed in the URL, and post the message in sale order

        URL parameter:
            - order (sale.order): The sale order model instance.

        JSON request body:
            - message_body (str): The content of the message to be posted.

        JSON response:
            - message (str): A confirmation message indicating the action performed.

        Returns:
            dict: A dictionary with a confirmation message.

        """
        message_body = request.get_json_data().get("message_body")
        # Post the message in the sale order chatter
        order.message_post(body=message_body)
        logger.debug("Message posted in sale order with ID %s", order.id)

        return {
            "message": f"Message successfully posted in sale order with ID: {order.id}."
        }

    @route(
        "/get_inventory_by_lot",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def get_inventory_by_lot(self):
        """Retrieves inventory details by lot number or serial number.

        This function searches for stock lots/serial numbers and returns their inventory details
        including location, product, and available quantities.

        JSON request body for POST:
            - serial_name (str, optional): The lot/serial number to search for.
            - location_name (str, optional): The name of the stock location to filter by.
            - location_id (int, optional): The ID of the stock location to filter by.
            - product_id (int, optional): The ID of the product to filter by.
            - company_id (int, optional): The company ID.

        JSON response:
            - message (str): A message indicating the action performed.
            - inventory_data (list of dict): A list of dictionaries containing:
                - lot_name (str): The lot/serial number.
                - product_name (str): The name of the product.
                - product_sku (str): The SKU of the product.
                - location_name (str): The name of the location.
                - quantity (float): The quantity available in that location.
                - product_qty (float): Total quantity for the lot.

        Returns:
            dict: A dictionary with a message and the inventory details.
        """
        data = request.get_json_data()

        serial_name = data.get("serial_name")
        location_name = data.get("location_name")
        location_id = data.get("location_id")
        product_id = data.get("product_id")
        company_id = data.get("company_id") or request.env.company.id

        # Build domain for search
        domain = []

        if serial_name:
            domain.append(("name", "=", serial_name))

        if location_name:
            location = (
                request.env["stock.location"]
                .with_company(company_id)
                .search([("complete_name", "=", location_name)], limit=1)
            )
            if location:
                location_id = location.id

        if product_id:
            domain.append(("product_id", "=", int(product_id)))

        # Search for lots/serial numbers
        lots = request.env["stock.lot"].with_company(company_id).search(domain)

        inventory_data = []

        for lot in lots:
            # Get quants (stock quantities) for this lot
            quant_domain = [("lot_id", "=", lot.id)]

            if location_id:
                quant_domain.append(("location_id", "=", int(location_id)))

            # Only get quants from internal locations with available quantity
            quant_domain.extend(
                [("location_id.usage", "=", "internal"), ("quantity", ">", 0)]
            )

            quants = (
                request.env["stock.quant"].with_company(company_id).search(quant_domain)
            )

            for quant in quants:
                inventory_data.append(
                    {
                        "lot_id": lot.id,
                        "lot_name": lot.name,
                        "product_id": lot.product_id.id,
                        "product_name": lot.product_id.name,
                        "product_sku": lot.product_id.default_code or "",
                        "location_id": quant.location_id.id,
                        "location_name": quant.location_id.complete_name,
                        "quantity": quant.quantity,
                        "reserved_quantity": quant.reserved_quantity,
                        "available_quantity": quant.quantity - quant.reserved_quantity,
                    }
                )

        return {
            "message": f"Found {len(inventory_data)} inventory records for the given lot/serial numbers.",
            "inventory_data": inventory_data,
        }

    @route(
        "/update_move_line_quant_by_name",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def update_move_line_quant_by_name(self):
        """Updates the 'quant_id' field in a stock move line using the displayed name.

        JSON request body:
            - move_line_id (int): The ID of the stock.move.line record to modify.
            - quant_name (str): The name of the quant as displayed in the interface (e.g., "Location - Lot").

        JSON response:
            - message (str): Success or error message.
        """
        data = request.get_json_data()
        move_line_id = data.get("move_line_id")
        serial_name = data.get("serial_name")
        location_name = data.get("location_name")
        company_id = data.get("company_id") or request.env.company.id

        move_line = (
            request.env["stock.move.line"].with_company(company_id).browse(move_line_id)
        )

        domain = [
            ("product_id", "=", move_line.product_id.id),
            ("location_id.usage", "=", "internal"),
            ("location_id.complete_name", "=", location_name),
            ("lot_id.name", "=", serial_name),
        ]

        target_quant = (
            request.env["stock.quant"].with_company(company_id).search(domain, limit=1)
        )

        # Update the field 'quant_id' and 'location_id' in the move line
        if target_quant:
            move_line.write(
                {
                    "quant_id": target_quant.id,
                    "location_id": target_quant.location_id.id,
                }
            )

            if move_line.picking_id:
                move_line.picking_id.write({"location_id": target_quant.location_id.id})

            return {
                "message": f"Product move line {move_line_id} updated to quant {target_quant.id}."
            }
        return {
            "message": f"Not found quant for product move line {move_line_id} with the given details."
        }

    @route(
        "/get_states/<model('res.country'):country>",
        methods=["GET"],
        type="json",
        auth="user",
    )
    def get_states(self, country):
        """Retrieves the list of states in the specified country.

        This function retrieves the list of states associated with the given country in the Odoo database
        and returns them in a JSON response.

        URL parameter:
            - country (res.country): The country model instance.

        JSON response:
            - message (str): A message indicating the action performed.
            - states_list (list of dict): A list of dictionaries containing the IDs, names, and codes of the states.

        Returns:
            dict: A dictionary with a message and the list of states.
        """
        states = country.state_ids
        states_list = states.read(["name", "code"])

        return {
            "message": f"List states from {country.name}",
            "states_list": states_list,
        }

    @route(
        "/get_localities/<model('res.country.state'):state>",
        methods=["GET"],
        type="json",
        auth="user",
    )
    def get_localities(self, state):
        """Retrieves the list of localities in the specified state.

        This function retrieves the list of localities associated with the given state in the Odoo database
        and returns them in a JSON response.

        URL parameter:
            - state (res.country.state): The state model instance.

        JSON response:
            - message (str): A message indicating the action performed.
            - localities_list (list of dict): A list of dictionaries containing the IDs and names of the localities.

        Returns:
            dict: A dictionary with a message and the list of localities.
        """
        localities = request.env["l10n_mx_edi.res.locality"].search(
            [("state_id", "=", state.id)]
        )
        localities_list = localities.read(["name", "code"])

        return {
            "message": f"List localities from {state.name}",
            "localities_list": localities_list,
        }

    @route("/get_product_id", methods=["POST"], type="json", auth="user")
    def get_product_id(self):
        """Get Product ID by Internal Reference.

        This endpoint receives an internal reference (default_code) and returns the corresponding product ID if it exists.

        JSON request body:
            - sku (str): The internal reference of the product (default_code).

        JSON response:
            - product_id (int): The ID of the product if found.
            - message (str): A message indicating the result.
        """
        data = request.get_json_data()
        sku = data.get("sku")
        company_id = data.get("company_id") or request.env.company.id

        product = (
            request.env["product.product"]
            .with_company(company_id)
            .search([("default_code", "=", sku)], limit=1)
        )

        return {
            "message": f"Product found with ID: {product.id}",
            "product_id": product.id,
        }

    @route("/create_purchase_order", methods=["POST"], type="json", auth="user")
    def create_purchase_order(self):
        """Creates and confirms a purchase order.

        This function creates a purchase order using the details provided in the JSON request body
        and automatically confirms it after creation.

        JSON request body:
            Required fields:
                - partner_id (int): The ID of the vendor/supplier.
                - product_lines (list of dicts): A list of dictionaries containing product details:
                    - product_id (int): The ID of the product.
                    - product_qty (float): The quantity of the product.
                    - price_unit (float, optional): The unit price of the product (default is 0).

            Optional fields:
                - company_id (int, optional): The company ID. Defaults to the current company.
                - user_id (int, optional): The user ID. Defaults to the current user.
                - date_planned (str, optional): The planned date for the purchase order.
                - picking_type_id (int, optional): The picking type ID.

        JSON response:
            - message (str): A success message with the purchase order ID and name.
            - purchase_order_id (int): The ID of the created purchase order.
            - purchase_order_name (str): The name/number of the purchase order.
            - state (str): The state of the purchase order (should be "purchase" after confirmation).

        Returns:
            dict: A dictionary with a success message and purchase order details.
        """
        data = request.get_json_data()
        company_id = data.get("company_id") or request.env.company.id

        # Prepare order lines for purchase order
        order_lines = [
            (
                0,
                0,
                {
                    "product_id": line["product_id"],
                    "product_qty": line["product_qty"],
                    "price_unit": line.get("price_unit", 0),
                },
            )
            for line in data["product_lines"]
        ]

        # Prepare purchase order values
        purchase_order_vals = {
            "partner_id": data["partner_id"],
            "order_line": order_lines,
        }

        # Optional fields
        optional_field_mapping = {
            "company_id": "company_id",
            "user_id": "user_id",
            "date_planned": "date_planned",
            "picking_type_id": "picking_type_id",
        }

        for data_key, vals_key in optional_field_mapping.items():
            if data_key in data:
                purchase_order_vals[vals_key] = data[data_key]

        # Create purchase order
        purchase_order = (
            request.env["purchase.order"]
            .with_company(company_id)
            .create(purchase_order_vals)
        )
        logger.info("Purchase order created with ID %s", purchase_order.id)

        # Confirm the purchase order
        purchase_order.button_confirm()
        logger.info("Purchase order with ID %s confirmed", purchase_order.id)

        return {
            "message": f"Purchase order created and confirmed with ID: {purchase_order.id}",
            "purchase_order_id": purchase_order.id,
            "purchase_order_name": purchase_order.name,
            "state": purchase_order.state,
        }

    @route(
        "/cancel_purchase_order/<model('purchase.order'):order>",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def cancel_purchase_order(self, order=False):
        """Cancels a purchase order.

        This function cancels a purchase order identified by its model instance
        passed in the URL.

        URL parameter:
            - order (purchase.order): The purchase order model instance.

        JSON response:
            - message (str): A confirmation message indicating the action performed.
            - purchase_order_id (int): The ID of the cancelled purchase order.
            - state (str): The state of the purchase order.

        Returns:
            dict: A dictionary with a confirmation message and purchase order details.
        """
        order.with_company(order.company_id.id).button_cancel()
        logger.info("Purchase order with ID %s cancelled", order.id)

        return {
            "message": f"Purchase order with ID: {order.id} successfully cancelled.",
            "purchase_order_id": order.id,
            "state": order.state,
        }

    @route(
        "/get_reception_lines/<model('stock.picking'):picking>",
        methods=["GET"],
        type="json",
        auth="user",
    )
    def get_reception_lines(self, picking=False):
        """Retrieves the move lines for a reception picking.

        Returns the essential data needed to assign lot/serial numbers before validation.

        URL parameter:
            - picking (stock.picking): The reception picking model instance.

        JSON response:
            - picking_id (int): The ID of the picking.
            - picking_name (str): The name of the picking.
            - move_lines (list of dict): List of move lines with:
                - move_line_id (int): The ID of the stock.move.line.
                - product_sku (str): The internal reference of the product.
                - quantity (float): The demanded quantity.

        Returns:
            dict: A dictionary with the picking info and move lines.
        """
        move_lines_data = [
            {
                "move_line_id": line.id,
                "product_sku": line.product_id.default_code or "",
                "quantity": line.move_id.product_uom_qty,
            }
            for line in picking.move_line_ids
        ]

        return {
            "message": f"Reception lines from {picking.id}",
            "picking_id": picking.id,
            "picking_name": picking.name,
            "move_lines": move_lines_data,
        }

    @route(
        "/validate_reception/<model('stock.picking'):picking>",
        methods=["POST"],
        type="json",
        auth="user",
    )
    def validate_reception(self, picking=False):
        """Validates a reception with lot/serial number assignment.

        Assigns lot/serial numbers to move lines and validates the picking.
        Creates the lot if it does not exist.

        URL parameter:
            - picking (stock.picking): The reception picking model instance.

        JSON request body:
            - move_lines (list of dicts): List of move lines with lot/serial info:
                - move_line_id (int): The ID of the stock.move.line.
                - lot_name (str): The lot/serial number to assign.

        JSON response:
            - message (str): Success message.
            - picking_id (int): The ID of the picking.
            - picking_name (str): The name of the picking.
            - state (str): The state of the picking after validation.

        Returns:
            dict: A dictionary with the result of the reception validation.
        """
        data = request.get_json_data()
        move_lines_data = data.get("move_lines", [])
        company_id = picking.company_id.id

        for line_data in move_lines_data:
            move_line_id = line_data.get("move_line_id")
            lot_name = line_data.get("lot_name")

            if not move_line_id or not lot_name:
                continue

            move_line = (
                request.env["stock.move.line"]
                .with_company(company_id)
                .browse(move_line_id)
            )

        # Create the lot/serial number
        lot = (
            request.env["stock.lot"]
            .with_company(company_id)
            .create(
                {
                    "name": lot_name,
                    "product_id": move_line.product_id.id,
                    "company_id": company_id,
                }
            )
        )

        move_line.write(
            {
                "lot_id": lot.id,
                "quantity": move_line.move_id.product_uom_qty,
            }
        )

        picking.with_company(company_id).with_context(
            skip_backorder=True
        ).button_validate()

        return {
            "message": f"Reception {picking.name} validated successfully.",
            "picking_id": picking.id,
            "picking_name": picking.name,
            "state": picking.state,
        }

    @route("/get_product_stock", methods=["GET"], type="http", auth="user")
    def get_product_stock(self):
        """Retrieves detailed stock information for products by SKU and location.

        Supports two modes:
        1. Single product: Provide SKU to get stock for a specific product
        2. All products: Omit SKU to get stock for all products at the location

        URL parameters:
            - sku (str, optional): Product SKU. If not provided, returns all products.
            - location_id (int): Stock location ID.
            - company_id (int, optional): Company ID. Defaults to current company.

        Returns:
            JSON response: Stock information for the product(s) at the specified location.
        """
        sku = request.params.get("sku")
        location_id = request.params.get("location_id")
        company_id = int(request.params.get("company_id") or request.env.company.id)

        result = (
            request.env["stock.quant"]
            .with_company(company_id)
            .get_stock_by_location(int(location_id), sku)
        )
        return request.make_json_response(result)
