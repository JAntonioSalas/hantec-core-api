
Hantec Core API
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

License
-------

This module is licensed under the OEEL-1 (Odoo Enterprise Edition License v1.0)

Changelog
---------

Version 18.0.0.0.1

- Initial release with the following features:
- Added `/create_schedule_activity_invoice` endpoint.
- Added `/get_states` endpoint.
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

Version 18.0.0.0.2

- Data retrieval on all endpoints was updated to the "get_json_data" method.
- Invoice creation has been updated to version 18.0 at `invoice_sale_order` endpoint.
- Added `/create_credit_note/<model("account.move"):invoice>` endpoint.
- Added `/update_credit_note/<model("account.move"):invoice>` endpoint.
- Added `/search_contact` endpoint.
- Added `/create_delivery_address` endpoint.
- Added `/create_invoice_address` endpoint.
- Added `/validate_delivery/<model("sale.order"):order>` endpoint.
- Added `/return_delivery/<model("sale.order"):order>` endpoint.
- Added `/get_inventory_by_lot` endpoint.
- Added `/update_move_line_quant_by_name` endpoint.
- Added `/get_product_id` endpoint.
- Added `/get_product_stock` endpoint.
- Added `/get_localities` endpoint.
