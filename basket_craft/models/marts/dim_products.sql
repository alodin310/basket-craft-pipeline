{{ config(materialized='table') }}

select
    product_id,
    product_name,
    description,
    created_at
from {{ ref('stg_products') }}
