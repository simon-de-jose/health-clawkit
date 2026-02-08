# Nutrition Logging

You're responsible for logging your human's meals with accurate nutritional data. This is an interactive workflow — your human sends you a meal (photo and/or description), and you handle identification, lookup, and logging.

## Prerequisites

1. Database initialized with nutrition table (see `database_setup.md`, step 4)
2. A USDA FoodData Central API key (free)

### Getting a USDA API key

1. Go to https://fdc.nal.usda.gov/api-key-signup
2. Sign up for a free key
3. Store it in your environment so you can use it in API calls

## Workflow

When your human sends you a meal to log:

### 1. Receive and process the input

- If they sent a **photo**: resize it first to save tokens:
  ```bash
  # Run from the project root
  ./scripts/process_meal_photos.sh /path/to/photo.jpg
  # Output: resized images in /tmp/nutrition-photos/
  ```
  Uses macOS `sips` (no extra dependencies). Resizes to max 1920px, compresses to ~85% quality.
- If they sent **text only**: proceed directly to identification

### 2. Identify foods

From the photo/description, identify:
- Main dishes
- Sides
- Sauces and condiments
- Beverages

### 3. Ask clarifying questions

Don't guess — ask your human about:
- **Portion sizes** (cups, oz, pieces, "about a fist-size portion")
- **What was actually consumed** (all of it? left half the rice?)
- **Cooking method** if unclear (fried vs grilled changes the fat profile significantly)
- **Ingredients** for homemade/mixed dishes (break down into components)

### 4. Look up nutrients via USDA API

Search for each food item:
```bash
curl -s "https://api.nal.usda.gov/fdc/v1/foods/search?api_key=$USDA_API_KEY&query=FOOD_NAME&pageSize=3"
```

Get detailed nutrients for a specific food (by FDC ID from search results):
```bash
curl -s "https://api.nal.usda.gov/fdc/v1/food/FDC_ID?api_key=$USDA_API_KEY"
```

**Always query the full nutrient profile.** Don't stop at calories and protein — the micronutrients matter for tracking trends.

### 5. Required nutrients

Extract ALL of these for each food item:

| Category | Nutrients |
|----------|-----------|
| **Macros** | Calories, Protein (g), Carbs (g), Total Fat (g) |
| **Fat breakdown** | Saturated (g), Monounsaturated (g), Polyunsaturated (g) |
| **Carb breakdown** | Fiber (g), Sugar (g) |
| **Minerals** | Sodium (mg), Potassium (mg), Calcium (mg), Iron (mg), Magnesium (mg) |
| **Vitamins** | Vitamin D (mcg), B12 (mcg), C (mg) |
| **Other** | Cholesterol (mg) |

USDA data is per 100g — apply portion multipliers before totaling.

### 6. Present summary for confirmation

Show your human a table before logging:

| Item | Cal | Protein | Carbs | Fat | Sat Fat | Fiber | Sugar | Sodium |
|------|-----|---------|-------|-----|---------|-------|-------|--------|
| Chicken breast (6oz) | 280 | 52g | 0g | 6g | 1.8g | 0g | 0g | 120mg |
| White rice (3/4 cup) | 160 | 3g | 35g | 0.3g | 0.1g | 0.5g | 0g | 1mg |
| **TOTAL** | **440** | **55g** | **35g** | **6.3g** | **1.9g** | **0.5g** | **0g** | **121mg** |

Get their confirmation before inserting.

### 7. Log to database

```bash
cd <project-dir>
.venv/bin/python src/log_nutrition.py --json '{
  "meal_time": "2026-02-07T19:30:00",
  "meal_type": "dinner",
  "meal_name": "Grilled chicken with rice",
  "food_items": [
    {"item": "chicken breast", "portion": "6oz", "calories": 280},
    {"item": "white rice", "portion": "3/4 cup", "calories": 160}
  ],
  "calories": 440,
  "protein_g": 55,
  "carbs_g": 35,
  "fat_total_g": 6.3,
  "fat_saturated_g": 1.9,
  "fat_unsaturated_g": 4.1,
  "fiber_g": 0.5,
  "sugar_g": 0,
  "sodium_mg": 121,
  "source": "photo"
}'
```

## Querying summaries

Your human may ask "what did I eat today?" or "how's my nutrition this week?" Use:

```bash
# Today's nutrition
.venv/bin/python src/nutrition_summary.py --today

# Specific date
.venv/bin/python src/nutrition_summary.py --date 2026-02-07

# JSON output (useful if you want to process the data further)
.venv/bin/python src/nutrition_summary.py --today --json
```

## Common mistakes to avoid

- **Don't skip image resize** — full-resolution photos waste tokens without improving accuracy
- **Don't log partial nutrients** — always get the full profile, not just calories. Your human is tracking trends over time.
- **Don't guess portions** — ask. The biggest source of error is portion estimation.
- **Don't estimate when USDA has the data** — use the API, don't rely on your training knowledge for nutrient values
- **Do break down homemade meals** — query individual ingredients rather than guessing at the dish level
