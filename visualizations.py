from calcs_and_sql import (
    get_conn
)
import matplotlib.pyplot as plt
## Fraction to account for items with fractions like 1/2 gallon
from fractions import Fraction


def price_per_unit():
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

    plt.figure(figsize=(10,8))
    plt.hist(ppu_list, bins=15, edgecolor='black')
    plt.title("Distribution of Price Per Unit (Normalized to oz)")
    plt.xlabel("Price Per Unit ($)")
    plt.ylabel("Product Count")
    plt.savefig("hist_PPU.png")
    plt.show()
    plt.close()

price_per_unit()
    