select
    order_id,
    to_timestamp(created_at)  as created_at,
    website_session_id,
    user_id                   as customer_id,
    primary_product_id,
    items_purchased,
    price_usd,
    cogs_usd
from {{ source('raw', 'orders') }}
