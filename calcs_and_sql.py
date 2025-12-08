import base64
import requests
import datetime
import matplotlib.pyplot as plt
import sqlite3

db_path = "foodproject.db"
db_insert_limit = 25
CLIENT_ID = "REDACTED_ID"
CLIENT_SECRET = "REDACTED_SECRET"

# Spoonacular API Configuration
SPOONACULAR_API_KEY = "REDACTED_KEY"


def get_conn():
    """
    Establishes and returns a connection to the SQLite database.
    
    Returns:
        sqlite3.Connection: Database connection object with Row factory enabled
                           for dictionary-like row access
    
    Author: Both (shared utility function)
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def create_kroger_tables():
    """
    Creates three tables for Kroger product data if they don't already exist.
    
    Tables created:
        - products: Stores unique product information (UPC, description, brand)
        - items: Stores location-specific product details (prices, stock, size)
        - price_history: Stores historical price data for tracking trends
    
    The products and items tables share product_id as a foreign key relationship.
    
    Returns:
        None
    
    Author: Jack
    """
    conn = get_conn()
    c = conn.cursor()

    # Create products table - stores unique product information
    # UPC stands for Universal Product Code (barcode identifier)
    products_table = """CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upc TEXT,
    description TEXT,
    brand TEXT)"""

    c.execute(products_table)

    # Create items table - stores location-specific product details
    # Using REALs for prices as they are decimal values (floats)
    items_table = """CREATE TABLE IF NOT EXISTS items(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    location_id TEXT,
    regular_price REAL,
    promo_price REAL,
    stock_level TEXT,
    size TEXT,
    FOREIGN KEY(product_id) REFERENCES products(id))"""

    c.execute(items_table)

    # Create price history table - tracks price changes over time
    price_history_table = """CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    price REAL,
    date TEXT,
    FOREIGN KEY(product_id) REFERENCES products(id))"""

    c.execute(price_history_table)

    conn.commit()
    conn.close()
    
    
    
    
def create_spoonacular_table():
    """
    Creates the meals table for Spoonacular recipe data if it doesn't exist.
    
    Table created:
        - meals: Stores recipe nutrition data including macronutrients,
                cuisine type, health scores, and ingredient information
    
    Returns:
        None
    
    Author: Vittorio
    """
    conn = get_conn()
    c = conn.cursor()

    # Create meals table - stores recipe and nutrition information
    # meal_id is UNIQUE to prevent duplicate recipes
    # REAL types used for numeric nutrition values (calories, macronutrients)
    meals_table = """CREATE TABLE IF NOT EXISTS meals(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meal_id INTEGER UNIQUE,
    meal_name TEXT,
    serving_size TEXT,
    calories REAL,
    protein_g REAL,
    fat_g REAL,
    carbs_g REAL,
    cuisine_type TEXT,
    health_score REAL,
    diet_labels TEXT,
    ingredients_list TEXT,
    meal_url TEXT)"""

    c.execute(meals_table)
    conn.commit()
    conn.close()


def get_kroger_token(client_id, client_secret, token_url):
    """
    Authenticates with Kroger API using OAuth 2.0 client credentials flow.
    
    Args:
        client_id (str): Kroger API client ID
        client_secret (str): Kroger API client secret
        token_url (str): OAuth token endpoint URL
    
    Returns:
        str: Access token for authenticated API requests
    
    Raises:
        SystemExit: If authentication fails
    
    Author: Jack
    """
    # Encode client credentials in Base64 for Basic Authentication
    # Format: "client_id:client_secret" -> base64 encoding
    TOKEN_URL = "https://api.kroger.com/v1/connect/oauth2/token"
    auth_str = f"{client_id}:{client_secret}"
    auth_b64 = base64.b64encode(auth_str.encode("ascii")).decode("ascii")

    # Set up authorization headers using Basic auth scheme
    headers_auth = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Request client credentials grant type with product scope
    data_auth = {
        "grant_type": "client_credentials",
        "scope": "product.compact"  # Scope for product catalog access
    }

    print("Requesting Production Access Token...")
    try: 
        response_token = requests.post(token_url, headers=headers_auth, data=data_auth)
        response_token.raise_for_status()  # Raise exception for 4xx/5xx status codes
        access_token = response_token.json()["access_token"]
        print("   Success! Production Token acquired.\n")
        return access_token
    except requests.exceptions.HTTPError as e:
        print(f"     Auth failed: {e}")
        print(f"     Server Response: {response_token.text}")
        exit()  # Exit program if authentication fails

def fetch_kroger_products(access_token, location_id, term="sugar", limit=50):
    """
    Fetches product data from Kroger API based on search term and location.
    
    Args:
        access_token (str): OAuth2 access token from get_kroger_token()
        location_id (str): Kroger store location ID
        term (str): Search term for products (default: "sugar")
        limit (int): Maximum number of products to return (default: 50)
    
    Returns:
        list: List of product dictionaries with price, brand, and availability data
    
    Raises:
        SystemExit: If API request fails
    
    Author: Jack
    """
    url = "https://api.kroger.com/v1/products"
    
    # Set authorization header with Bearer token
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Configure API request parameters for filtered product search
    params = {
        "filter.term": term,                  # Search keyword
        "filter.locationId": location_id,    # Specific store location
        "filter.limit": limit                 # Max results to return
    }

    try: 
        response_token = requests.get(url, headers=headers, params=params)
        response_token.raise_for_status()  # Raise exception for HTTP errors
        data = response_token.json()["data"]  # Extract product array from response
        print("   Success! Product data acquired.\n")
        return data
    except requests.exceptions.HTTPError as e:
        print(f"     Auth failed: {e}")
        print(f"     Server Response: {response_token.text}")
        exit()  # Exit if unable to fetch product data

def get_kroger_loc(access_token, zipcode):
    """
    Finds the nearest Kroger store location based on ZIP code.
    
    Args:
        access_token (str): OAuth2 access token from get_kroger_token()
        zipcode (str): US postal ZIP code to search near
    
    Returns:
        str: Location ID of the nearest Kroger store
    
    Raises:
        SystemExit: If no location found or API request fails
    
    Author: Jack
    """
    url = "https://api.kroger.com/v1/locations"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"filter.zipCode.near": zipcode}  # Search for stores near this ZIP
    
    print("Finding Kroger Location")
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # Raise exception for HTTP errors
    data = response.json()["data"]  # Extract location array from response

    # Exit if no stores found in the area
    if not data:
        print("No location found.")
        exit()

    # Use the first (closest) location from results
    location = data[0]
    print(f"Store found: {location['name']} (ID: {location['locationId']})")
    return location["locationId"]
    
def clean_and_transf_kroger(raw_products):
    """
    Extracts and structures relevant data from raw Kroger API product response.
    
    Args:
        raw_products (list): List of raw product dictionaries from Kroger API
    
    Returns:
        list: List of cleaned product dictionaries with extracted fields:
              upc, description, brand, regular_price, promo_price, stock_level, size
    
    Author: Jack
    """
    cleaned = []

    for product in raw_products:
        # Extract first item from items array (location-specific data)
        item = product.get("items", [{}])[0]
        
        # Try multiple price sources in order of preference
        # Some products have "price", others have "nationalPrice"
        price_obj = item.get("price") or item.get("nationalPrice") or {}
        
        # Build cleaned product dictionary with all required fields
        cleaned.append({
            "upc": product.get("upc"),              # Universal Product Code
            "description": product.get("description"),  # Product name/description
            "brand": product.get("brand"),          # Brand name

            "regular_price": price_obj.get("regular"),  # Regular retail price
            "promo_price": price_obj.get("promo"),      # Promotional price (if any)
            "stock_level": (item.get("inventory") or {}).get("stockLevel"),  # Availability status
            "size": item.get("size")                # Product size (e.g., "16 oz")
        })
        
    return cleaned 

def into_krogerdb(products, location_id):
    conn = get_conn()
    cur = conn.cursor()
    inserted = 0

    for product in products:
        if inserted >= db_insert_limit:
            break 

        try:
            if product.get("regular_price") is None:
                raise ValueError(f"Skipping {product.get('description')}: Missing Price")
            
            cur.execute("""INSERT OR IGNORE INTO products (upc, description, brand)
                        VALUES (?, ?, ?) """,
                        (product["upc"], product["description"], product["brand"]))
            
            
            
            
            
            
            cur.execute("SELECT id FROM products WHERE upc = ?", (product['upc'],))
            row = cur.fetchone()

            if row is None:
                raise ValueError(f"Database error: Could not retrieve ID for UPC {product['upc']}")

        
            product_id = row["id"]
        



            cur.execute(f"""
                    INSERT OR IGNORE INTO items (
                        product_id, location_id,
                        regular_price, promo_price, stock_level, size
                    )
                    VALUES (?,?,?,?,?,?)""", 
                    (
                    product_id,
                    location_id,
                    product["regular_price"],
                    product["promo_price"],
                    product["stock_level"],
                    product["size"]
                ))
        
            inserted += 1
        except Exception as weird_error:
            print(f"\nError processing item: {weird_error}")
            continue

    conn.commit()
    conn.close()
    return inserted

def save_price_hist():
    conn = get_conn()
    cur = conn.cursor()

    today = str(datetime.date.today())

    cur.execute("""SELECT items.product_id AS product_id, items.regular_price
    FROM items WHERE items.regular_price IS NOT NULL""")

    rows = cur.fetchall()

    for row in rows:
        cur.execute(f"""
                    INSERT INTO price_history (product_id, price, date)
                    VALUES ({row["product_id"]}, {row["regular_price"]}, '{today}')
                    """
                    )
        
    conn.commit()
    conn.close()


def kroger_calculations():
    """
    Calculates key metrics from Kroger product data and writes results to file.
    
    Calculations performed:
        - Price per unit (dollars per ounce/gram) for all products
        - Cheapest product by unit price
        - Average price across all products
        - Brand comparison (average price by brand)
    
    Uses database JOIN to combine products and items tables.
    Writes all calculated results to 'kroger_results.txt'.
    
    Returns:
        None
    
    Author: Jack
    """
    conn = get_conn()
    cur = conn.cursor()

    out = []

    #### CALCULATION 1: Price per unit ####
    # JOIN products and items tables to get description, size, and price together
    cur.execute(""" 
                SELECT products.description, items.size, items.regular_price
                FROM products
                JOIN items on products.id = items.product_id """)
    price_per_unit= []

    for row in cur.fetchall():
        size = row['size']  # e.g., "16 oz"
        price = row['regular_price']  # e.g., 3.99

        if size and price:
            try:
                # Extract numeric amount from size string (e.g., "16" from "16 oz")
                amount = float(size.split()[0])
                # Calculate price per unit (e.g., $0.25 per oz)
                unit_amount = round(price / amount, 4)
                price_per_unit.append((row["description"], unit_amount))
            except:
                continue  # Skip products with invalid size format

    out.append(f"Computed price per unit for {len(price_per_unit)} products")

    #### CALCULATION 2: Find cheapest item ####
    if price_per_unit:
        # Find minimum price per unit using lambda function
        cheapest = min(price_per_unit, key=lambda x: x[1])
        out.append(f"The cheapest item found out of {len(price_per_unit)} products is {cheapest[0]} (${cheapest[1]})")
    
    
    #### Average price 
    cur.execute("""SELECT AVG(regular_price) AS average 
                FROM items WHERE regular_price IS NOT NULL
                
                """
                )
    avg_price = cur.fetchone()["average"]
    out.append(f"Average price of all products: {round(avg_price, 2)}")

    #### brand comparison

    cur.execute("""SELECT products.brand, AVG(items.regular_price) AS avg_price
                FROM products
                JOIN items on products.id = items.product_id
                WHERE items.regular_price IS NOT NULL
                GROUP BY products.brand""")
    
    brands = cur.fetchall()
    out.append(f"Brand comparison for {len(brands)} brands complete.")

    with open("kroger_results.txt", 'w') as fh:
        for line in out:
            fh.write(line + '\n')
    
    conn.close()
    print("Kroger calculations complete and saved in kroger_results.txt")


# ==================== SPOONACULAR API FUNCTIONS ====================

def fetch_meal_data_spoonacular(api_key, query="pasta", number=25):
    """
    Fetches recipe and nutrition data from Spoonacular API.
    
    Args:
        api_key (str): Spoonacular API authentication key
        query (str): Search term for recipes (default: "pasta")
        number (int): Maximum number of recipes to return (default: 25)
    
    Returns:
        list: List of recipe dictionaries with full nutrition data and ingredients,
              or empty list if no results or API error occurs
    
    Author: Vittorio
    """
    url = "https://api.spoonacular.com/recipes/complexSearch"
    
    # Configure API request with nutrition and ingredient data enabled
    params = {
        "apiKey": api_key,
        "query": query,
        "number": number,
        "addRecipeNutrition": "true",  # Include detailed nutrition information
        "fillIngredients": "true"       # Include ingredient lists
    }
    
    try:
        print(f"   Fetching recipes for '{query}'...")
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        
        # Check if results exist in response
        if "results" in data and data["results"]:
            print(f"   Success! Found {len(data['results'])} recipes")
            return data["results"]
        else:
            print(f"   No results found for '{query}'")
            return []
            
    except requests.exceptions.HTTPError as e:
        print(f"   API request failed: {e}")
        print(f"   Response: {response.text}")
        return []
    except Exception as e:
        print(f"   Error: {e}")
        return []

def clean_and_transform_meal_data(raw_meals):
    """Extract and structure meal data from Spoonacular API response"""
    cleaned = []
    
    for meal in raw_meals:
        try:
            nutrition = meal.get("nutrition", {})
            nutrients = nutrition.get("nutrients", [])
            
            # Extract macronutrients
            calories = next((n["amount"] for n in nutrients if n["name"] == "Calories"), None)
            protein = next((n["amount"] for n in nutrients if n["name"] == "Protein"), None)
            fat = next((n["amount"] for n in nutrients if n["name"] == "Fat"), None)
            carbs = next((n["amount"] for n in nutrients if n["name"] == "Carbohydrates"), None)
            
            # Extract cuisines (join if multiple)
            cuisines = meal.get("cuisines", [])
            cuisine_type = cuisines[0] if cuisines else "Unknown"
            
            # Extract diet labels
            diets = meal.get("diets", [])
            diet_labels = ", ".join(diets) if diets else "None"
            
            # Extract ingredients
            ingredients = meal.get("nutrition", {}).get("ingredients", [])
            ingredients_list = ", ".join([ing.get("name", "") for ing in ingredients[:10]])  # Limit to 10
            
            cleaned.append({
                "meal_id": meal.get("id"),
                "meal_name": meal.get("title"),
                "serving_size": f"{meal.get('servings', 1)} serving(s)",
                "calories": calories,
                "protein_g": protein,
                "fat_g": fat,
                "carbs_g": carbs,
                "cuisine_type": cuisine_type,
                "health_score": meal.get("healthScore"),
                "diet_labels": diet_labels,
                "ingredients_list": ingredients_list,
                "meal_url": meal.get("sourceUrl", "")
            })
            
        except Exception as e:
            print(f"   Error processing meal: {e}")
            continue
    
    return cleaned

def into_spoonacular_db(meals):
    """Insert cleaned meal data into the database"""
    conn = get_conn()
    cur = conn.cursor()
    inserted = 0
    
    for meal in meals:
        try:
            # Skip meals without essential nutrition data
            if meal.get("calories") is None or meal.get("protein_g") is None:
                print(f"   Skipping {meal.get('meal_name')}: Missing nutrition data")
                continue
            
            cur.execute("""
                INSERT OR IGNORE INTO meals (
                    meal_id, meal_name, serving_size, calories,
                    protein_g, fat_g, carbs_g, cuisine_type,
                    health_score, diet_labels, ingredients_list, meal_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                meal["meal_id"],
                meal["meal_name"],
                meal["serving_size"],
                meal["calories"],
                meal["protein_g"],
                meal["fat_g"],
                meal["carbs_g"],
                meal["cuisine_type"],
                meal["health_score"],
                meal["diet_labels"],
                meal["ingredients_list"],
                meal["meal_url"]
            ))
            
            inserted += 1
            
        except Exception as e:
            print(f"   Error inserting meal: {e}")
            continue
    
    conn.commit()
    conn.close()
    return inserted

def spoonacular_calculations():
    """Calculate nutrition metrics from meal data"""
    conn = get_conn()
    cur = conn.cursor()
    
    out = []
    
    # Get all meals
    cur.execute("""
        SELECT meal_name, calories, protein_g, fat_g, carbs_g, 
               cuisine_type, health_score
        FROM meals
        WHERE calories IS NOT NULL AND protein_g IS NOT NULL
    """)
    
    meals = cur.fetchall()
    
    if not meals:
        print("No meal data found in database")
        conn.close()
        return
    
    out.append(f"=== SPOONACULAR NUTRITION ANALYSIS ===\n")
    out.append(f"Total meals analyzed: {len(meals)}\n")
    
    # 1. Macronutrient percentages and protein density
    nutrition_data = []
    for meal in meals:
        calories = meal["calories"]
        protein = meal["protein_g"]
        fat = meal["fat_g"]
        carbs = meal["carbs_g"]
        
        # Calculate calories from each macronutrient
        protein_cal = protein * 4
        fat_cal = fat * 9
        carbs_cal = carbs * 4
        total_macro_cal = protein_cal + fat_cal + carbs_cal
        
        # Calculate percentages
        if total_macro_cal > 0:
            protein_pct = (protein_cal / total_macro_cal) * 100
            fat_pct = (fat_cal / total_macro_cal) * 100
            carbs_pct = (carbs_cal / total_macro_cal) * 100
        else:
            protein_pct = fat_pct = carbs_pct = 0
        
        # Protein density
        protein_density = protein / calories if calories > 0 else 0
        
        # Health category
        if calories < 400 and meal["health_score"] >= 50:
            health_category = "healthy"
        elif calories < 600 and meal["health_score"] >= 30:
            health_category = "moderately healthy"
        else:
            health_category = "less healthy"
        
        # Nutrition index (weighted: 60% health score, 40% protein density)
        nutrition_index = (meal["health_score"] * 0.6) + (protein_density * 100 * 0.4)
        
        nutrition_data.append({
            "name": meal["meal_name"],
            "protein_pct": protein_pct,
            "fat_pct": fat_pct,
            "carbs_pct": carbs_pct,
            "protein_density": protein_density,
            "health_category": health_category,
            "nutrition_index": nutrition_index,
            "cuisine": meal["cuisine_type"]
        })
    
    # 2. Average calories, protein, health score by cuisine
    cur.execute("""
        SELECT cuisine_type,
               AVG(calories) as avg_calories,
               AVG(protein_g) as avg_protein,
               AVG(health_score) as avg_health_score,
               COUNT(*) as count
        FROM meals
        WHERE calories IS NOT NULL
        GROUP BY cuisine_type
        ORDER BY avg_health_score DESC
    """)
    
    cuisine_stats = cur.fetchall()
    
    out.append("\n--- Average Nutrition by Cuisine ---")
    for stat in cuisine_stats:
        out.append(f"{stat['cuisine_type']}: "
                  f"Avg Calories: {stat['avg_calories']:.1f}, "
                  f"Avg Protein: {stat['avg_protein']:.1f}g, "
                  f"Avg Health Score: {stat['avg_health_score']:.1f} "
                  f"({stat['count']} meals)")
    
    # 3. Health category distribution
    health_categories = {}
    for item in nutrition_data:
        cat = item["health_category"]
        health_categories[cat] = health_categories.get(cat, 0) + 1
    
    out.append("\n--- Health Category Distribution ---")
    for category, count in health_categories.items():
        out.append(f"{category.title()}: {count} meals ({count/len(meals)*100:.1f}%)")
    
    # 4. Top nutrition index meals
    top_meals = sorted(nutrition_data, key=lambda x: x["nutrition_index"], reverse=True)[:5]
    out.append("\n--- Top 5 Meals by Nutrition Index ---")
    for i, meal in enumerate(top_meals, 1):
        out.append(f"{i}. {meal['name']} (Score: {meal['nutrition_index']:.2f})")
    
    # 5. Average macronutrient breakdown across all meals
    avg_protein_pct = sum(d["protein_pct"] for d in nutrition_data) / len(nutrition_data)
    avg_fat_pct = sum(d["fat_pct"] for d in nutrition_data) / len(nutrition_data)
    avg_carbs_pct = sum(d["carbs_pct"] for d in nutrition_data) / len(nutrition_data)
    
    out.append(f"\n--- Average Macronutrient Breakdown ---")
    out.append(f"Protein: {avg_protein_pct:.1f}%")
    out.append(f"Fat: {avg_fat_pct:.1f}%")
    out.append(f"Carbs: {avg_carbs_pct:.1f}%")
    
    # Write results to file
    with open("spoonacular_results.txt", 'w') as fh:
        for line in out:
            fh.write(line + '\n')
    
    conn.close()
    print("Spoonacular calculations complete and saved in spoonacular_results.txt")
