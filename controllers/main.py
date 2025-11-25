from odoo.http import request, Controller, route
import logging, re

logger = logging.getLogger(__name__)


class MainController(Controller):
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
            - marketplace (bool, optional): Value to validate if it is required create different contact
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
        email = data.get("email")
        phone = data.get("phone")
        store_name = data.get("store_name")
        partner_id = data.get("partner_id")
        contact_data = data.get("contact_data", {})

        if data.get("marketplace"):
            name = data.get("name")
            domain = [("name", "=", name)]
            existing_contact = env["res.partner"].search(domain, limit=1)

            if existing_contact:
                return {
                    "message": f"Contact found with ID: {existing_contact.id}",
                    "contact_id": existing_contact.id,
                }
            contact_data["name"] = name
            new_contact = env["res.partner"].create(contact_data)

            return {
                "message": f"New contact created with ID {new_contact.id}",
                "contact_id": new_contact.id,
            }

        if email or phone:
            phone_suffix = phone[len(phone) - 4 :] if phone else None

            domain = []
            if email:
                domain.append(("email", "=", f"{email}"))
            if phone_suffix:
                # Use "like" operator to use the "%" wildcard
                domain.append(("mobile", "like", f"%{phone_suffix}"))

            existing_contact = env["res.partner"].search(domain, limit=1)

            if existing_contact:
                logger.debug("Contact found with ID %s", existing_contact.id)
                return {
                    "message": f"Contact found with ID: {existing_contact.id}.",
                    "contact_id": existing_contact.id,
                }

            if "email" not in contact_data and email:
                contact_data["email"] = email
            if "phone" not in contact_data and phone:
                contact_data["phone"] = phone

        if store_name:
            store_name_suffix = store_name[len(store_name) - 4 :]

            domain = [("name", "=", f"%{store_name_suffix}")]
            existing_contact = env["res.partner"].search(domain, limit=1)

            if existing_contact:
                logger.debug("Contact found with ID %s", existing_contact.id)
                return {
                    "message": f"Contact found with ID: {existing_contact.id}.",
                    "contact_id": existing_contact.id,
                }

            contact_data.update({"type": "other", "parent_id": partner_id})

        new_contact = env["res.partner"].create(contact_data)
        logger.info("New contact created with ID %s", new_contact.id)
        return {
            "message": f"New contact created with ID {new_contact.id}",
            "contact_id": new_contact.id,
        }

    @route(
        '/update_contact/<model("res.partner"):partner>',
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

        # Search for existing address of the given type
        address = env["res.partner"].search(
            [("parent_id", "=", partner_id), ("type", "=", address_type)], limit=1
        )

        if address and not only_create:
            # Update existing address
            address.write(address_data)
        else:
            # Add a new address
            address_data.update({"type": address_type, "parent_id": partner_id})
            address = env["res.partner"].create(address_data)

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

        sale_order_data = {field: data[field] for field in required_fields}

        # Add optional fields
        for field, value in data.items():
            if field not in required_fields:
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
        sale_order = request.env["sale.order"].create(sale_order_vals)

        return {
            "message": f"Sale order created with ID: {sale_order.id}, Team ID: {sale_order.team_id.id}",
            "sale_order_id": sale_order.id,
            "sale_order_name": sale_order.name,
        }

    @route(
        '/update_sale_order/<model("sale.order"):order>',
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

        JSON request body:
            - tracking_number (str): The tracking number to be assigned to the sale order.

        JSON response:
            - message (str): A message indicating that the sale order has been successfully updated.

        Returns:
            dict: A dictionary with a success message.

        """
        tracking_number = request.get_json_data().get("tracking_number")
        order.update({"yuju_carrier_tracking_ref": tracking_number})

        return {
            "message": f"The order with ID: {order.id} has been successfully updated."
        }

    @route(
        '/invoice_sale_order/<model("sale.order"):order>',
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
            .with_context(**context)
            .create({"advance_payment_method": "delivered"})
        )

        # Create invoice
        invoice_wizard.create_invoices()
        invoices = order.invoice_ids

        for invoice in invoices:
            invoice.write(
                {
                    "l10n_mx_edi_cfdi_to_public": data.get("cfdi_to_public", False),
                    "l10n_mx_edi_usage": data.get("code_usage", "G01"),
                }
            )
            if data.get("journal_id"):
                journal_id = data["journal_id"]
                invoice.write({"journal_id": journal_id})
            if data.get("cfdi_origin_id"):
                cfdi_origin_id = data["cfdi_origin_id"]
                invoice.write({"l10n_mx_edi_cfdi_origin": cfdi_origin_id})

        # Confirm invoice
        invoices.action_post()

        return {
            "message": "Invoice created",
            "list_invoices": invoices.read(["name", "date"]),
        }

    @route(
        '/register_payment_invoice/<model("account.move"):invoice>',
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

        register_payment_wizard = request.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=[invoice.id]
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
        '/get_shipping_info/<model("sale.order"):order>',
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
        '/download_invoice/<model("account.move"):invoice>',
        methods=["GET"],
        type="http",
        auth="user",
    )
    def download_invoice(self, invoice=False):
        """Downloads an invoice as a PDF.

        This function generates and downloads a PDF file for the invoice identified by its ID.

        URL parameter:
            - invoice (account.move): The invoice model instance.

        HTTP response:
            - Content-Type: application/pdf
            - Content-Length: The length of the PDF content

        Returns:
            response: An HTTP response with the PDF content of the invoice.

        """
        # Generate the PDF
        pdf_content, _ = request.env["ir.actions.report"]._render_qweb_pdf(
            "account.report_invoice_with_payments", [invoice.id]
        )
        http_headers = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(pdf_content)),
        ]
        return request.make_response(pdf_content, headers=http_headers)

    @route(
        '/stamp_invoice/<model("account.move"):invoice>',
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

        # We use the account.move.send.wizard to process EDI documents (stamping)
        # We simulate the wizard action to trigger the CFDI generation
        send_wizard = request.env["account.move.send.wizard"].create(
            {
                "move_id": invoice.id,
                "checkbox_send_mail": request.get_json_data().get("send_email", False),
            }
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
        '/create_credit_note/<model("account.move"):invoice>',
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

        JSON response:
            - message (str): A message indicating the result.
            - credit_note_id (int): The ID of the created credit note.

        Returns:
            dict: A dictionary with the result.
        """
        data = request.get_json_data()
        reason = data.get("reason", "revertir")
        journal_id = data.get("journal_id", 1)

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
            request.env["account.move.reversal"].with_context(**ctx).create(wizard_vals)
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
                credit_notes = request.env["account.move"].search(domain, limit=1)
                if credit_notes:
                    credit_note_id = credit_notes.id

        # Fallback if action parsing fails
        if not credit_note_id:
            # Find the move that has this invoice as the reversed entry
            credit_note = request.env["account.move"].search(
                [("reversed_entry_id", "=", invoice.id)],
                order="id desc",
                limit=1,
            )
            if credit_note:
                credit_note_id = credit_note.id

        return {
            "message": "Credit note created successfully.",
            "credit_note_id": credit_note_id,
        }

    @route(
        '/confirm_credit_note/<model("account.move"):credit_note>',
        methods=["POST"],
        type="json",
        auth="user",
    )
    def confirm_credit_note(self, credit_note=None):
        """Updates and confirms a draft credit note.

        This function updates a draft credit note with provided values and then confirms (posts) it.
        It specifically handles mapping for common Mexican localization fields if provided.

        URL parameter:
            - credit_note (account.move): The credit note model instance (must be in draft).

        JSON request body:
            - usage (str, optional): The CFDI usage code (e.g., "G02"). Maps to 'l10n_mx_edi_usage'.
            - cfdi_origin (str, optional): The CFDI Origin string (e.g., "01|UUID"). Maps to 'l10n_mx_edi_cfdi_origin'.
            - payment_method_id (int, optional): ID of the payment method. Maps to 'l10n_mx_edi_payment_method_id'.
            - Any other field valid for account.move (e.g., "ref", "date", "invoice_date").

        JSON response:
            - message (str): Success message.
            - credit_note_id (int): ID of the confirmed credit note.
            - name (str): The name/number of the confirmed credit note.
        """
        data = request.get_json_data()
        vals_to_update = {}

        # Helper mapping for common Mexican localization fields based on the image provided
        # This allows sending "usage" instead of the long technical name
        if "usage" in data:
            vals_to_update["l10n_mx_edi_usage"] = data.pop("usage")
        if "cfdi_public" in data:
            vals_to_update["l10n_mx_edi_cfdi_to_public"] = data.pop("cfdi_public")
        if "cfdi_origin" in data:
            vals_to_update["l10n_mx_edi_cfdi_origin"] = data.pop("cfdi_origin")
        if "payment_method_id" in data:
            vals_to_update["l10n_mx_edi_payment_method_id"] = data.pop(
                "payment_method_id"
            )

        # Add any remaining data from the request directly to the update values
        # This allows updating standard fields like 'ref', 'invoice_date', etc.
        vals_to_update.update(data)

        if vals_to_update:
            credit_note.write(vals_to_update)

        # Confirm (Post) the credit note
        credit_note.action_post()

        return {
            "message": f"Credit note {credit_note.name} confirmed successfully.",
            "credit_note_id": credit_note.id,
            "name": credit_note.name,
            "cfdi_origin": credit_note.l10n_mx_edi_cfdi_origin,
        }

    @route(
        '/send_invoice_by_email/<model("account.move"):invoice>',
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
        action = invoice.action_invoice_sent()
        action_context = action["context"]
        invoice_send_wizard = (
            request.env["account.invoice.send"]
            .with_context(action_context, active_ids=[invoice.id])
            .create({"is_print": False})
        )

        # Send the invoice by email
        invoice_send_wizard.send_and_print_action()

        return {"success": "The invoice has been successfully sent."}

    @route(
        '/confirm_sale_order/<model("sale.order"):order>',
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
        order.action_confirm()

        return {"message": f"Sale order with ID: {order.id} successfully confirmed."}

    @route(
        [
            '/create_schedule_activity/<model("sale.order"):order>',
            '/create_schedule_activity_invoice/<model("account.move"):order>',
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
        activity = order.activity_schedule(
            activity_type_id=request.get_json_data().get("activity_type_id"),
            summary=request.get_json_data().get("summary", ""),
            note=request.get_json_data().get("note", ""),
            date_deadline=request.get_json_data().get("date_deadline"),
            user_id=request.get_json_data().get("user_id", request.env.uid),
        )

        return {
            "message": f"Scheduled activity created with ID: {activity.id} for sale order {order.id}."
        }

    @route(
        '/send_message_sale_order/<model("sale.order"):order>',
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
        ["/get_inventory", "/get_inventory_by_sku"],
        methods=["POST", "GET"],
        type="json",
        auth="user",
    )
    def get_inventory(self):
        """Retrieves the inventory details for all products with a SKU or a specific product based on its SKU from a given location.

        This function searches for all products in the Odoo database that have a SKU (default_code not null)
        or searches for a product using the provided SKU, and returns their inventory details from a given location
        in a JSON response.

        JSON request body for POST (if applicable):
            - sku (str, optional): The SKU of the product to search for.
            - location_id (int): The ID of the stock location to filter inventory by.

        JSON response:
            - message (str): A message indicating the action performed.
            - inventory_data (list of dict): A list of dictionaries containing the inventory details for each product, including:
                - name (str): The name of the product.
                - default_code (str): The SKU of the product.
                - qty_available (float): The quantity of the product available.
                - virtual_available (float): The virtual quantity of the product available.

        Returns:
            dict: A dictionary with a message and the inventory details of the products.
        """
        location_id = request.get_json_data().get("location_id") or request.params.get(
            "location_id"
        )
        sku = (
            request.get_json_data().get("sku")
            if request.httprequest.method == "POST"
            else request.params.get("sku")
        )

        if sku:
            domain = [("default_code", "=", sku)]
        else:
            domain = [("default_code", "!=", False)]

        products = (
            request.env["product.product"]
            .with_context(location=int(location_id))
            .search(domain)
        )
        inventory_data = products.read(
            ["name", "default_code", "qty_available", "virtual_available"]
        )

        return {
            "message": "Inventory data retrieved",
            "inventory_data": inventory_data,
        }

    @route(
        '/get_states/<model("res.country"):country>',
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
        sku = request.get_json_data().get("sku")

        product = request.env["product.product"].search(
            [("default_code", "=", sku)], limit=1
        )

        return {
            "message": f"Product found with ID: {product.id}",
            "product_id": product.id,
        }
