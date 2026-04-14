select
    order_item_id,
    to_timestamp(created_at)  as created_at,
    order_id,
    product_id,
    is_primary_item,
    price_usd,
    cogs_usd
from {{ source('raw', 'order_items') }}
