# OpenNutrition Dataset

## Overview

The OpenNutrition Dataset is a comprehensive collection of food and nutrition data provided in TSV (Tab-Separated Values) format. This dataset contains nutritional information for a wide variety of foods, including macronutrients, ingredients, and sourcing information.

## File Structure

This package contains:

- `opennutrition_foods.tsv`: The main dataset file in TSV format
- `LICENSE-ODbL.txt`: The Open Database License v1.0
- `LICENSE-DbCL.txt`: The Database Contents License v1.0
- `README.md`: This file

### Data Format

The dataset is provided as a tab-separated values (TSV) file with the following fields:

- `id`: Unique identifier for each food item (starts with "fd\_")
- `name`: Food item name
- `alternate_names`: Alternative names for the food item (JSON array)
- `description`: Text description of the food
- `type`: Food type (everyday, grocery, prepared, restaurant)
- `source`: Source information (JSON array)
- `serving`: Serving size information (JSON object)
- `nutrition_100g`: Nutritional information per 100g (JSON object)
- `ean_13`: EAN-13 barcode number
- `labels`: Food labels such as raw, canned, sweetened etc. (JSON array)
- `package_size`: Package size information (JSON object)
- `ingredients`: Ingredient list
- `ingredient_analysis`: Ingredient analysis including allergens (JSON object)

## Licensing

This OpenNutrition Dataset is made available under the Open Database License: http://opendatacommons.org/licenses/odbl/1.0/. Any rights in individual contents of the database are licensed under a modified version of the Database Contents License: http://opendatacommons.org/licenses/dbcl/1.0/. Please review the complete LICENSE-DbCL.txt file included in this package for the full terms.

### Attribution Requirements

If you display, publish, or otherwise make available any data from the OpenNutrition Dataset, you must provide clear and visible attribution to "OpenNutrition" with a link to https://www.opennutrition.app in each of the following locations:

1. On every page, screen, or interface where any data from the OpenNutrition Dataset is displayed to users
2. In your application's listing on distribution platforms (such as Google Play Store, Apple App Store, or similar platforms)
3. On your application's or product's website (if any)
4. In the "legal" or "about" section of your application or product

Consolidated attribution (providing attribution in only one location while displaying data in multiple locations) does not satisfy these requirements.

### Share-Alike Requirements

Any Derivative Database that you create using the OpenNutrition Dataset must also be shared under the same license terms (ODbL). The best way to comply with this requirement is to contribute your modifications or enhancements back to OpenNutrition.

## Data Sources

Portions of the OpenNutrition dataset incorporate data from Open Food Facts. This data is made available under the Open Database License: http://opendatacommons.org/licenses/odbl/1.0/.

When using OpenNutrition data that originates from Open Food Facts, the following attribution must be maintained:
"(c) Open Food Facts contributors" with a link to https://world.openfoodfacts.org/terms-of-use or https://world.openfoodfacts.org

## Contact Information

For questions, support, or to report issues with the dataset:

- Email: opensource@opennutrition.app
- Website: https://www.opennutrition.app

To contribute to the dataset or provide corrections, please contact us at opensource@opennutrition.app. We may choose to provide additional tools to facilitate collaboration in the future based on demand.
