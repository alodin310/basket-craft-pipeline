select
    product_id,
    to_timestamp(created_at)  as created_at,
    product_name,
    description
from {{ source('raw', 'products') }}
