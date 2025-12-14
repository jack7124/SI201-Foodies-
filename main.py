"""
SI 201 Foodies - Final Project
Main Pipeline for Data Collection, Analysis, and Visualization

This program collects data from two APIs (Kroger and Spoonacular), stores the data
in a SQLite database, performs calculations, and generates visualizations.

APIs Used:
    - Kroger API: Grocery product prices, brands, and availability
    - Spoonacular API: Recipe nutrition data and meal information

Database:
    - foodproject.db with 4 tables (products, items, price_history, meals)

Output Files:
    - kroger_results.txt: Price analysis and statistics
    - spoonacular_results.txt: Nutrition analysis and meal rankings
    - 6 PNG visualization files

Authors: Vittorio Centore, Jack Miller
Group: SI201 Foodies
"""

from calcs_and_sql import (
    create_kroger_tables,
    get_kroger_token,
    get_kroger_loc,
    fetch_kroger_products,
    clean_and_transf_kroger,
    into_krogerdb,
    save_price_hist,
    kroger_calculations,
    # Spoonacular functions
    create_spoonacular_table,
    fetch_meal_data_spoonacular,
    clean_and_transform_meal_data,
    into_spoonacular_db,
    spoonacular_calculations,
    SPOONACULAR_API_KEY
)
from visualizations import make_kroger_graphs, make_spoonacular_graphs

import requests

# Kroger API Configuration  
ZIPCODE = "48104"
SEARCH_TERMS = ["sugar", "milk", "flour", "eggs", "ham", "water", "bread", "cheese", "butter"]
DB_limit = 25

# Spoonacular API Configuration
MEAL_SEARCH_TERMS = ["pasta", "chicken", "salad", "soup", "vegetarian"]
MEAL_LIMIT = 35  # Number of meals to fetch per search term

def main():
    """
    Main execution function that orchestrates the entire data pipeline.
    
    Workflow:
        1. Kroger API: Fetch product data, store in DB, calculate metrics, visualize
        2. Spoonacular API: Fetch meal data, store in DB, calculate metrics, visualize
    
    Returns:
        None
    
    Authors: Both
    """
    print("="*60)
    print("SI 201 FOODIES - Data Collection & Analysis Pipeline")
    print("="*60)
    
    # ==================== KROGER API WORKFLOW ====================
    print("\n[KROGER API] Starting data collection...")
    
    print("\nFirst: create tables")
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
            access_token, location_id, term=term, limit=25)
        
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
    print(f"\nKroger analysis complete!")

    print("\nSeventh: Generate Kroger visualizations")
    make_kroger_graphs()

    # ==================== SPOONACULAR API WORKFLOW ====================
    print("\n" + "="*60)
    print("[SPOONACULAR API] Starting meal data collection...")
    print("="*60)
    
    print("\nFirst: Create Spoonacular table")
    create_spoonacular_table()
    
    print("\nSecond: Fetch meal data from Spoonacular API")
    total_meals = 0
    
    for search_term in MEAL_SEARCH_TERMS:
        if total_meals >= DB_limit:
            print(f"\nTarget reached for {DB_limit} meals")
            break

        print(f"\nSearching for '{search_term}' recipes...")
        
        raw_meals = fetch_meal_data_spoonacular(
            SPOONACULAR_API_KEY, 
            query=search_term, 
            number=MEAL_LIMIT
        )
        
        if raw_meals:
            print("Third: Cleaning and transforming meal data")
            cleaned_meals = clean_and_transform_meal_data(raw_meals)
            
            print("Fourth: Storing meals in database")
            count = into_spoonacular_db(cleaned_meals)
            total_meals += count
            
            print(f"Added {count} meals. Total in DB: {total_meals}")
        else:
            print(f"No meals found for '{search_term}'")
    
    print(f"\nFifth: Run Spoonacular calculations")
    spoonacular_calculations()
    print("Spoonacular analysis complete!")
    
    print("\nSixth: Generate Spoonacular visualizations")
    make_spoonacular_graphs()
    
    # ==================== COMPLETE ====================
    print("\n" + "="*60)
    print("PIPELINE COMPLETE!")
    print("="*60)
    print("\nGenerated files:")
    print("  - kroger_results.txt")
    print("  - spoonacular_results.txt")
    print("  - hist_PPU.png")
    print("  - avgp_brand_bar.png")
    print("  - inventory_pie.png")
    print("  - calories_by_cuisine.png")
    print("  - macronutrient_breakdown.png")
    print("  - calories_vs_protein_density.png")
    print("\n" + "="*60)

if __name__ == "__main__":
    main()


