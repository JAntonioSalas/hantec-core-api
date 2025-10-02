
Hantec Ecommerce
-------

Summary
-------

This module provides comprehensive tools to manage sales orders, invoices, shipping information, and customer contacts in Odoo. It includes endpoints for creating and updating various entities, enhancing the overall efficiency and reliability of business processes.


Authors and Maintainers
-----------------------

- Authors: 
  - C&O PROJECTS AND SOLUTIONS

- Maintainers:
  - C&O PROJECTS AND SOLUTIONS

Development Status
------------------

The current development status of this module is:

- Development Status: **Beta**

License
-------

This module is licensed under the OEEL-1 (Odoo Enterprise Edition License v1.0)

Changelog
---------

Version 15.0.0

- Changed the phone suffix length from 4 to 5 in the `create_contact` endpoint to ensure correct matching of existing contacts.
- Changed response type for `/get_states_mexico endpoint`

Version 15.0.0

- Initial release with the following features:
  - Added `/create_schedule_activity_invoice` endpoint.
  - Added `/get_states_mexico` endpoint.
  - Added `/get_inventory_by_sku` endpoint.
  - Added `/get_inventory` endpoint.
  - Added `/send_message_sale_order` endpoint.
  - Added `/create_schedule_activity` endpoint.
  - Added `/confirm_sale_order` endpoint.
  - Added `/send_invoice_by_email/<int:invoice_id>` endpoint.
  - Added `/stamp_invoice/<int:invoice_id>` endpoint.
  - Added `/download_invoice/<int:invoice_id>` endpoint.
  - Added `/get_shipping_info/<model("sale.order"):order>` endpoint.
  - Added `/register_payment_invoice/<model("account.move"):invoice>` endpoint.
  - Added `/invoice_sale_order` endpoint.
  - Added `/update_sale_order` endpoint.
  - Added `/create_sale_order` endpoint.
  - Added `/delivery_address` endpoint.
  - Added `/address_invoice` endpoint.
  - Added `/update_contact` endpoint.
  - Added `/create_contact` endpoint.
