from odoo import models, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def search_contacts_by_params(self, search_params):
        """Search for contacts based on given parameters.

        Args:
            search_params (dict): A dictionary of search parameters.
                - email (str): Email of the contact.
                - phone (str): Phone number of the contact.
                - mobile (str): Mobile number of the contact.
                - name (str): Name of the contact.
                - strict_phone (bool): Whether to perform strict phone matching.

        Returns:
            recordset: A recordset of matching partners.
        """
        email = search_params.get("email")
        phone = search_params.get("phone")
        mobile = search_params.get("mobile")
        name = search_params.get("name")
        strict_phone = search_params.get("strict_phone", False)

        domain = []

        if email:
            domain.append(("email", "=", email.strip().lower()))

        if name:
            domain.append(("name", "ilike", name.strip()))

        # Logic for phone and mobile
        operator = "=" if strict_phone else "ilike"

        if phone and mobile:
            domain.append("|")
            domain.append(("phone_sanitized", operator, phone.strip()))
            domain.append(("phone_sanitized", operator, mobile.strip()))
        elif phone:
            domain.append(("phone_sanitized", operator, phone.strip()))
        elif mobile:
            domain.append(("phone_sanitized", operator, mobile.strip()))

        if domain:
            return self.search(domain)
        else:
            return self.browse()

    def create_or_find_contact(self, data):
        """Logic to search or create a contact tailored for the API.

        Args:
            data (dict): The dictionary containing contact details, similar to the JSON body.
                         Expects keys: email, phone, mobile, name, store_name, partner_id, contact_data.

        Returns:
            tuple: (res.partner record, bool is_new)
        """
        # Search existing contact using strict or loose params
        existing_contacts = self.search_contacts_by_params(data)
        if existing_contacts:
            # Return the last found (as per original controller logic) and False for is_new
            return existing_contacts[-1], False

        # Logic for Store Name (specific business rule)
        store_name = data.get("store_name")
        if store_name:
            store_domain = [("name", "=ilike", f"%{store_name}")]
            parent_contact = self.search(store_domain, limit=1)

            if parent_contact:
                return parent_contact, False

            # If store provided but not found
            partner_id = data.get("partner_id")
            if partner_id:
                data.setdefault("contact_data", {})
                data["contact_data"].update(
                    {
                        "type": "other",
                        "parent_id": partner_id,
                    }
                )

        # Prepare creation values
        contact_vals = data.get("contact_data", {})

        # Extract allowed fields from root to contact_vals if not present
        for field in ("name", "email", "phone", "mobile"):
            val = data.get(field)
            if val:
                contact_vals.setdefault(field, val)

        # Ensure company_id is set explicitly for creation from context
        if self.env.context.get("allowed_company_ids"):
            contact_vals["company_id"] = self.env.context["allowed_company_ids"][0]

        # Create new contact
        new_contact = self.create(contact_vals)
        return new_contact, True
