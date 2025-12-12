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
