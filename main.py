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
SEARCH_TERMS = ["sugar", "milk", "flour", "eggs", "ham", "water"]
DB_limit = 125

def main():
    print("First: create tables")
    create_kroger_tables()

    print("\nSecond: Getting tokens")
    access_token = get_kroger_token(
        "REDACTED_ID",
        "REDACTED_SECRET",
        "https://api.kroger.com/v1/connect/oauth2/token"
    )

    print("\nThird: Get store location")
    location_id = get_kroger_loc(access_token, ZIPCODE)

    print("\nFourth: Fetch product data")
    ## Setting limit to 50 but its already limited to 25 insertions to DB within this function
    total = 0
    for term in SEARCH_TERMS:
        if total >= DB_limit:
            print(f"\nTarget reached for {DB_limit} items")
            break
        print(f"Searching for {term}")

        
        products = fetch_kroger_products(
            access_token, location_id, term=term, limit=50)
        
        if products:
            print("Cleaning data")
    
            cleaned_products = clean_and_transf_kroger(products)
            print(cleaned_products)

            count = into_krogerdb(cleaned_products, location_id)
            total += count

            print(f"\nAdded {count} items. Total in DB: {total}")
        else:
            print("\nNo other products found for this term.")

  
    print("\nFifth: Saving price history")
    save_price_hist()
    print(f"Price history saved")

    print(f"\nSixth: Run calculations")
    kroger_calculations()
    print(f"\nDone")

if __name__ == "__main__":
    main()


