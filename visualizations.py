from calcs_and_sql import (
    get_conn
)
import matplotlib.pyplot as plt
# Fraction module to handle fractional sizes like 1/2 gallon
from fractions import Fraction
import random
import sqlite3


def price_per_unit():
    """
    Creates a histogram showing distribution of price per unit across all products.
    
    Normalizes all product sizes to ounces for fair comparison, handling conversions
    for pounds, gallons, quarts, pints, and liters.
    
    Generates: hist_PPU.png
    
    Author: Both
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
                SELECT items.regular_price AS price, items.size AS size
                FROM items
                WHERE items.regular_price IS NOT NULL
                """)
    
    ppu_list = []

    for row in cur.fetchall():
        try:
            parts = row["size"].split()
            amount_raw = parts[0]
            unit = parts[1].lower().strip()
            ### Get oz, lb, gal, ct
            amount = float(Fraction(amount_raw))
            
            if unit in ['lb', 'lbs', 'pound', 'pounds']:
                amount = amount * 16  # Convert lbs to oz
            elif unit in ['gal', 'gallon']:
                amount = amount * 128 # Convert gal to fl oz
            elif unit in ['qt', 'quart']:
                amount = amount * 32  # Convert qt to fl oz
            elif unit in ['pt', 'pint']:
                amount = amount * 16  # Convert pt to fl oz
            elif unit in ['l', 'liter', 'liters']:
                amount = amount * 33.8 # Convert liters to fl oz

            ppu = row["price"] / amount

            ppu_list.append(ppu)

        except Exception as e:
            continue
            
    conn.close()
    
    if not ppu_list:
        print("No PPU list found")
        return

    # Calculate statistics
    median_ppu = sorted(ppu_list)[len(ppu_list)//2]

    plt.figure(figsize=(10,8))
    plt.hist(ppu_list, bins=15, edgecolor='black', color='#4ECDC4', alpha=0.7)
    
    # Add the vertical line
    plt.axvline(median_ppu, color='red', linestyle='dashed', linewidth=2, label=f'Median: ${median_ppu:.2f}/oz')
    
    plt.title("Distribution of Price Per Unit (Normalized to oz)")
    plt.xlabel("Price Per Unit ($)")
    plt.ylabel("Product Count")
    plt.legend() # Show the label for the line
    plt.savefig("hist_PPU.png")
    plt.show()
    plt.close()

def brand_avg_price():
    """
    Creates a bar chart comparing average prices across different brands.
    
    Brands are randomized in display order to avoid alphabetical bias.
    Uses database JOIN to combine products and items tables.
    
    Generates: avgp_brand_bar.png
    
    Author: Jack
    """
    conn = get_conn()
    cur = conn.cursor()

    # JOIN to get brand and price data together
    cur.execute("""SELECT products.brand AS brand, AVG(items.regular_price) AS avgp
                FROM products
                JOIN items ON products.id = items.product_id
                WHERE items.regular_price IS NOT NULL 
                GROUP BY products.brand
                ORDER BY avgp ASC
                """)
    
    rows = cur.fetchall()
    conn.close()

    brands = [row["brand"] if row["brand"] else "Unknown" for row in rows]
    avg_prices = [row["avgp"] for row in rows]

    # Dynamic height based on number of brands (0.4 inches per brand)
    plt.figure(figsize=(10, max(6, len(brands) * 0.4)))
    
    # Use barh for horizontal bars
    bars = plt.barh(brands, avg_prices, color='skyblue', edgecolor='black')
    
    plt.title("Average Price by Brand (Sorted)", fontsize=14)
    plt.xlabel("Average Price ($)", fontsize=12)
    plt.ylabel("Brand", fontsize=12)
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Add price labels on the ends of bars
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                 f'${width:.2f}', va='center', fontsize=9)

    plt.tight_layout()
    plt.savefig("avgp_brand_bar.png")
    plt.show()
    plt.close()
    '''
    combined = list(zip(brands, avg_prices))
    random.shuffle(combined)
    shuff_brands, shuff_averages = zip(*combined)

    plt.figure(figsize=(10,8))
    plt.bar(shuff_brands, shuff_averages)
    plt.title("Average Prices of Brands")
    plt.xlabel("Brand")
    plt.ylabel("Average Price ($)")
    plt.xticks(rotation=90, fontsize=8)
    plt.tight_layout()
    plt.savefig("avgp_brand_bar.png")
    plt.show()
    plt.close()
'''

def pie_inventory():
    """
    Creates a pie chart showing distribution of product availability levels.
    
    Groups products by stock_level (e.g., IN_STOCK, LOW_STOCK, OUT_OF_STOCK)
    and displays percentage breakdown.
    
    Generates: inventory_pie.png
    
    Author: Both
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT stock_level, COUNT(*) as count
                FROM items
                WHERE stock_level IS NOT NULL
                GROUP BY stock_level
                """)
    
    rows = cur.fetchall()
    stock_list = []

    if not rows:
        print("Inventory data not found.")
        return
    labels = [row["stock_level"].replace('_', ' ').title() for row in rows]
    count = [row["count"] for row in rows]
    total_items = sum(count)

    fig, ax = plt.subplots(figsize=(10,8))

    # Create the pie, but assign it to a variable 'wedges'
    wedges, texts, autotexts = ax.pie(count, labels=labels, autopct='%1.1f%%', 
                                      startangle=140, 
                                      colors=['#66b3ff','#99ff99','#ffcc99'],
                                      pctdistance=0.85,  # Push % labels out
                                      wedgeprops=dict(width=0.4, edgecolor='w')) # width=0.4 makes it a donut

    # Add text in the center hole
    ax.text(0, 0, f"{total_items}\nProducts", ha='center', va='center', fontsize=20, fontweight='bold')

    plt.setp(autotexts, size=10, weight="bold")
    plt.title("Product Availability Breakdown", fontsize=16)
    plt.savefig("inventory_pie.png")
    plt.show()
    plt.close()

# ==================== SPOONACULAR VISUALIZATIONS ====================

def calories_by_cuisine():
    """
    Creates a bar chart comparing average calories across different cuisine types.
    
    Filters cuisines to show only those with at least 2 meals to ensure
    statistical relevance. Displays calorie values on top of each bar.
    
    Generates: calories_by_cuisine.png
    
    Author: Both
    """
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT cuisine_type, AVG(calories) as avg_calories
        FROM meals
        WHERE calories IS NOT NULL AND cuisine_type != 'Unknown'
        GROUP BY cuisine_type
        HAVING COUNT(*) >= 2
        ORDER BY avg_calories DESC
    """)
    
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        print("No cuisine data found for visualization")
        return
    
    cuisines = [row["cuisine_type"] for row in rows]
    avg_cals = [row["avg_calories"] for row in rows]
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(cuisines, avg_cals, color='#FF6B6B', edgecolor='black')
    plt.title("Average Calories by Cuisine Type", fontsize=16, fontweight='bold')
    plt.xlabel("Cuisine Type", fontsize=12)
    plt.ylabel("Average Calories", fontsize=12)
    plt.xticks(rotation=45, ha='right')
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig("calories_by_cuisine.png")
    plt.show()
    plt.close()

def macronutrient_breakdown():
    """
    Creates a stacked bar chart showing macronutrient composition of top meals.
    
    Displays top 10 highest-calorie meals with protein/fat/carbs percentages.
    Uses caloric contribution for accurate percentages:
    - Protein: 4 calories per gram
    - Fat: 9 calories per gram  
    - Carbs: 4 calories per gram
    
    Generates: macronutrient_breakdown.png
    
    Author: Both
    """
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT meal_name, calories, protein_g, fat_g, carbs_g
        FROM meals
        WHERE calories IS NOT NULL AND protein_g IS NOT NULL
        ORDER BY calories DESC
        LIMIT 10
    """)
    
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        print("No meal data found for macronutrient breakdown")
        return
    
    meal_names = []
    protein_pcts = []
    fat_pcts = []
    carbs_pcts = []
    
    for row in rows:
        # Calculate calories from each macro
        protein_cal = row["protein_g"] * 4
        fat_cal = row["fat_g"] * 9
        carbs_cal = row["carbs_g"] * 4
        total_macro_cal = protein_cal + fat_cal + carbs_cal
        
        if total_macro_cal > 0:
            protein_pcts.append((protein_cal / total_macro_cal) * 100)
            fat_pcts.append((fat_cal / total_macro_cal) * 100)
            carbs_pcts.append((carbs_cal / total_macro_cal) * 100)
            
            # Shorten meal names for display
            name = row["meal_name"]
            if len(name) > 25:
                name = name[:22] + "..."
            meal_names.append(name)
    
    if not meal_names:
        print("No valid macronutrient data")
        return
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create stacked bars
    x = range(len(meal_names))
    p1 = ax.bar(x, protein_pcts, label='Protein', color='#4ECDC4')
    p2 = ax.bar(x, fat_pcts, bottom=protein_pcts, label='Fat', color='#FFD93D')
    
    # Calculate bottom for carbs (protein + fat)
    carbs_bottom = [p + f for p, f in zip(protein_pcts, fat_pcts)]
    p3 = ax.bar(x, carbs_pcts, bottom=carbs_bottom, label='Carbs', color='#FF6B6B')
    
    ax.set_title("Macronutrient Breakdown - Top 10 Meals by Calories", 
                 fontsize=16, fontweight='bold')
    ax.set_xlabel("Meal", fontsize=12)
    ax.set_ylabel("Percentage (%)", fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(meal_names, rotation=45, ha='right', fontsize=9)
    ax.legend()
    ax.set_ylim(0, 100)
    
    plt.tight_layout()
    plt.savefig("macronutrient_breakdown.png")
    plt.show()
    plt.close()

def calories_vs_protein_density():
    """
    Creates a scatter plot showing relationship between calories and protein density.
    
    Each point represents one meal, colored by health score (green=healthy, red=unhealthy).
    Protein density = grams of protein per calorie (higher is better for nutrition).
    Includes reference line at 0.05 g/cal indicating good protein content.
     
    Generates: calories_vs_protein_density.png
    
    Author: Both
    """
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT meal_name, calories, protein_g, health_score
        FROM meals
        WHERE calories IS NOT NULL AND protein_g IS NOT NULL
    """)
    
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        print("No meal data found for scatter plot")
        return
    
    calories_list = []
    protein_density_list = []
    health_scores = []
    
    for row in rows:
        calories = row["calories"]
        protein_density = row["protein_g"] / calories if calories > 0 else 0
        
        calories_list.append(calories)
        protein_density_list.append(protein_density)
        health_scores.append(row["health_score"] if row["health_score"] else 50)
    
    plt.figure(figsize=(10, 8))
    
    # Color by health score
    scatter = plt.scatter(calories_list, protein_density_list, 
                         c=health_scores, cmap='RdYlGn', 
                         s=100, alpha=0.6, edgecolors='black')
    
    plt.colorbar(scatter, label='Health Score')
    plt.title("Nutrition Efficiency: Calories vs Protein Density", 
              fontsize=16, fontweight='bold')
    plt.xlabel("Total Calories", fontsize=12)
    plt.ylabel("Protein Density (g protein / calorie)", fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Add reference lines
    plt.axhline(y=0.05, color='gray', linestyle='--', alpha=0.5, 
                label='Good protein density (>0.05)')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("calories_vs_protein_density.png")
    plt.show()
    plt.close()

def make_spoonacular_graphs():
    print("\nMaking Spoonacular Visualizations")
    calories_by_cuisine()
    macronutrient_breakdown()
    calories_vs_protein_density()
    print("Spoonacular Graphs Complete.\n")

def make_kroger_graphs():
    print("\nMaking Kroger Visualizations")
    price_per_unit()
    brand_avg_price()
    pie_inventory()
    print("Graphs Complete.\n")
