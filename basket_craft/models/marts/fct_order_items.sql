{{ config(materialized='table') }}

select
    oi.order_item_id,
    oi.order_id,
    o.customer_id,
    oi.product_id,
    cast(o.created_at as date)  as order_date,
    oi.is_primary_item,
    1                           as quantity,
    oi.price_usd                as unit_price,
    oi.cogs_usd,
    oi.price_usd                as line_total
from {{ ref('stg_order_items') }} as oi
left join {{ ref('stg_orders') }} as o
    on oi.order_id = o.order_id
