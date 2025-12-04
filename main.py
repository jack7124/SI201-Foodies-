from calcs_and_sql import (
    create_kroger_tables,
    get_kroger_token,
    get_kroger_loc,
    fetch_kroger_products,
    clean_and_transf_kroger,
    into_krogerdb,
    save_price_hist,
    kroger_calculations
)

import requests

ZIPCODE = "48104"
SEARCH_TERM = "sugar" 

def main():
    print("First: create tables")
    create_kroger_tables()

    print("\nSecond: Getting tokens")
    access_token = get_kroger_token(
        CLIENT_ID="REDACTED",
        CLIENT_SECRET="REDACTED",
        TOKEN_URL="https://api.kroger.com/v1/connect/oauth2/token"
    )

    print("\nThird: Get store location")
    location_id = get_kroger_loc(access_token, ZIPCODE)

    print("\nFourth: Fetch product data")
    ## Setting limit to 50 but its already limited to 25 insertions to DB within this function
    products = fetch_kroger_products(
        access_token, location_id, term=SEARCH_TERM, limit=50)
    
    print("\nFifth: Cleaning product data")
    cleaned_products = clean_and_transf_kroger(products)

    print("\nSixth: Inserting into DB")
    insert = into_krogerdb(cleaned_products, location_id)
    print(f"Inserted {insert} new items")


    print("\nSeventh: Saving price history")
    save_price_hist()
    print(f"Price history saved")

    print(f"\nEighth: Run calculations")
    kroger_calculations()
    print(f"\nDone")

if __name__ == "__main__":
    main()


