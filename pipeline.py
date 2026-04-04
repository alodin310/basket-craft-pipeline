from extract import extract
from transform import transform

print("=== Basket Craft Pipeline ===")
print("\n[1/2] Extract: MySQL → staging")
extract()
print("\n[2/2] Transform: staging → analytics")
transform()
print("\nPipeline complete.")
