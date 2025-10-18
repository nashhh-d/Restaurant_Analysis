import pandas as pd
import os

# Load the Excel file with error handling
try:
    file_path = "restaurant_data.xlsx"
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found")
        # Handle the error appropriately (exit or use alternative)
    
    xls = pd.ExcelFile(file_path)
    df = xls.parse("Sheet1")
    
    # Check if dataframe is empty
    if df.empty:
        print("Warning: The loaded data is empty")
    
    # Check for required columns
    required_columns = ["order_date", "order_time", "food_item"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Warning: Missing required columns: {missing_columns}")
    
    # 🧼 Step 1: Clean column names
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    # 🗓 Step 2: Convert dates and times
    df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
    df['order_time'] = pd.to_datetime(df['order_time'], format="%H:%M:%S", errors='coerce').dt.time
    
    # 📆 Step 3: Add useful columns
    # Check for null values in order_date before calculating derived columns
    if df['order_date'].notna().any():
        df['day_of_the_week'] = df['order_date'].dt.day_name()
        df['month'] = df['order_date'].dt.month
        df['year'] = df['order_date'].dt.year
    else:
        print("Warning: 'order_date' column contains only null values")
    
    # 🍽 Step 5: Define tagging metadata
    dish_metadata = {
        "grilled chicken": {
            "origin": "Middle Eastern",
            "ingredients": ["chicken", "spices", "olive oil"],
            "seasonality": "All-season"
        },
        "pizza": {
            "origin": "Italian",
            "ingredients": ["flour", "cheese", "tomato", "yeast"],
            "seasonality": "All-season"
        },
        "burger": {
            "origin": "American",
            "ingredients": ["beef", "bun", "lettuce", "cheese"],
            "seasonality": "All-season"
        },
        "shawarma": {
            "origin": "Middle Eastern",
            "ingredients": ["chicken", "garlic", "pita"],
            "seasonality": "All-season"
        },
        "koshari": {
            "origin": "Egyptian",
            "ingredients": ["lentils", "rice", "pasta", "tomato"],
            "seasonality": "Winter"
        },
        "salad": {
            "origin": "Universal",
            "ingredients": ["lettuce", "tomato", "cucumber"],
            "seasonality": "Summer"
        },
        "soup": {
            "origin": "Universal",
            "ingredients": ["broth", "vegetables", "spices"],
            "seasonality": "Winter"
        }
    }
    
    # 🏷 Step 6: Apply dish tags - Performance optimization
    # Create a mapping dictionary for each tag type
    food_origin_map = {k: v.get("origin") for k, v in dish_metadata.items()}
    food_ingredients_map = {k: v.get("ingredients") for k, v in dish_metadata.items()}
    food_seasonality_map = {k: v.get("seasonality") for k, v in dish_metadata.items()}
    
    # Clean food_item column once
    df["food_item_clean"] = df["food_item"].astype(str).str.strip().str.lower()
    
    # Apply mappings
    df["food_origin"] = df["food_item_clean"].map(food_origin_map)
    df["food_ingredients"] = df["food_item_clean"].map(food_ingredients_map)
    df["food_seasonality"] = df["food_item_clean"].map(food_seasonality_map)
    
    # Drop the temporary column
    df.drop(columns=["food_item_clean"], inplace=True)
    
    # ✅ Done! Preview result
    if not df.empty:
        print(df[["food_item", "food_origin", "food_ingredients", "food_seasonality"]].dropna().head())
    
except Exception as e:
    print(f"An error occurred: {str(e)}")

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

try:
    # Validation checks
    if 'food_ingredients' not in df.columns:
        print("Error: 'food_ingredients' column is missing")
        raise KeyError("Missing required column: food_ingredients")
    
    if 'food_quantity' not in df.columns:
        print("Error: 'food_quantity' column is missing")
        raise KeyError("Missing required column: food_quantity")
    
    if 'order_date' not in df.columns:
        print("Error: 'order_date' column is missing")
        raise KeyError("Missing required column: order_date")
    
    # Convert food_quantity to numeric if not already
    df['food_quantity'] = pd.to_numeric(df['food_quantity'], errors='coerce')
    
    # Ensure food_ingredients is a list type before using explode
    # This check prevents errors if food_ingredients is not a list/array type
    valid_ingredients = df['food_ingredients'].apply(lambda x: isinstance(x, (list, np.ndarray)))
    if not valid_ingredients.all():
        print("Warning: Some entries in 'food_ingredients' are not lists")
        # Filter to only include rows where food_ingredients is a list
        df = df[valid_ingredients]
    
    # Proceed with analysis only if we have valid data
    if not df.empty:
        # Explode ingredients so each ingredient gets its own row
        ingredient_df = df[["order_date", "food_quantity", "food_ingredients"]].dropna()
        ingredient_df = ingredient_df.explode("food_ingredients")
        
        # Check if we have data after exploding
        if ingredient_df.empty:
            print("No valid ingredient data to analyze")
            raise ValueError("No valid ingredient data")
        
        # Extract the month for aggregation
        ingredient_df['month'] = ingredient_df['order_date'].dt.to_period("M")
        
        # Group by month and ingredient to get total demand
        monthly_ingredients = (
            ingredient_df.groupby(['month', 'food_ingredients'])['food_quantity']
            .sum()
            .reset_index()
            .rename(columns={"food_ingredients": "ingredient", "food_quantity": "total_quantity"})
        )
        
        # Pivot the data so each ingredient has a column
        ingredient_trend_pivot = monthly_ingredients.pivot(
            index='month', columns='ingredient', values='total_quantity'
        ).fillna(0)
        
        # Handle too many ingredients - keep only top N ingredients by volume if needed
        MAX_INGREDIENTS_TO_PLOT = 10
        if len(ingredient_trend_pivot.columns) > MAX_INGREDIENTS_TO_PLOT:
            print(f"Warning: Too many ingredients. Showing only top {MAX_INGREDIENTS_TO_PLOT} by volume.")
            top_ingredients = ingredient_trend_pivot.sum().nlargest(MAX_INGREDIENTS_TO_PLOT).index
            ingredient_trend_pivot = ingredient_trend_pivot[top_ingredients]
        
        # Smooth trends using a 3-month rolling average
        ingredient_trend_smoothed = ingredient_trend_pivot.rolling(window=3, min_periods=1).mean()
        
        # Plot trends with improved visualization
        plt.figure(figsize=(14, 8))
        ax = ingredient_trend_smoothed.plot(
            figsize=(14, 8), 
            title="Smoothed Monthly Ingredient Demand",
            colormap='tab20'  # Better color differentiation
        )
        
        plt.ylabel("Estimated Quantity Needed")
        plt.xlabel("Month")
        plt.grid(True, alpha=0.3)
        
        # Improve legend readability
        handles, labels = ax.get_legend_handles_labels()
        plt.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, -0.1),
                   ncol=min(5, len(labels)), frameon=True)
        
        plt.tight_layout()
        plt.show()
    else:
        print("Error: No valid data for ingredient analysis")

except Exception as e:
    print(f"An error occurred during ingredient trend analysis: {str(e)}")

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
from collections import defaultdict

try:
    # Validate required columns
    required_columns = ['order_id', 'food_item', 'day_of_the_week', 'order_date', 'food_quantity', 'total_order']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        print(f"Error: Missing required columns for clustering: {missing_columns}")
        raise KeyError(f"Missing columns: {missing_columns}")
    
    # STEP 1: Feature Engineering with validation
    customer_df = df.copy()
    
    # Ensure day_of_the_week and order_date are valid
    if not pd.api.types.is_datetime64_dtype(customer_df['order_date']):
        print("Warning: Converting order_date to datetime")
        customer_df['order_date'] = pd.to_datetime(customer_df['order_date'], errors='coerce')
    
    # Handle NaN values
    customer_df = customer_df.dropna(subset=['order_id', 'food_item', 'order_date'])
    
    if customer_df.empty:
        print("Error: No valid data for clustering after cleaning")
        raise ValueError("No valid data for clustering")
    
    # Map items to healthy/not and festive (as a proxy)
    def tag_health(item):
        if pd.isna(item):
            return 0
        item = str(item).lower()
        return int(any(kw in item for kw in ["salad", "soup", "grilled"]) and "burger" not in item)
    
    def tag_festive(row):
        try:
            # Check for valid day_of_the_week and order_date
            if pd.isna(row['day_of_the_week']) or pd.isna(row['order_date']):
                return 0
            return int(row['day_of_the_week'] in ['Friday', 'Saturday'] or row['order_date'].month in [12, 1])
        except (AttributeError, TypeError):
            return 0
    
    customer_df['is_healthy'] = customer_df['food_item'].apply(tag_health)
    customer_df['is_festive'] = customer_df.apply(tag_festive, axis=1)
    
    # Aggregate at customer (Order ID) level
    try:
        agg = customer_df.groupby('order_id').agg({
            'is_healthy': 'mean',
            'is_festive': 'mean',
            'food_quantity': 'sum',
            'total_order': 'mean',
            'food_item': 'nunique',
            'order_date': 'nunique'
        }).rename(columns={
            'food_quantity': 'total_items',
            'total_order': 'avg_spend',
            'food_item': 'unique_items',
            'order_date': 'active_days'
        }).reset_index()
    except KeyError as e:
        print(f"Error during aggregation: {str(e)}")
        raise
    
    # Check if we have sufficient data
    if len(agg) < 5:  # Arbitrary threshold
        print(f"Warning: Only {len(agg)} customers for clustering, results may not be reliable")
    
    # STEP 2: Find optimal number of clusters
    features = ['is_healthy', 'is_festive', 'total_items', 'avg_spend', 'unique_items', 'active_days']
    
    # Convert to numeric and handle any remaining NaNs
    for feature in features:
        agg[feature] = pd.to_numeric(agg[feature], errors='coerce')
    
    # Fill any NaN values with column means
    agg[features] = agg[features].fillna(agg[features].mean())
    
    # Normalize data
    X = StandardScaler().fit_transform(agg[features])
    
    # Determine optimal number of clusters using silhouette score
    sil_scores = defaultdict(float)
    max_clusters = min(8, len(agg) // 5)  # Don't exceed 8 or num_samples/5
    
    for n_clusters in range(2, max_clusters + 1):
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(X)
        
        try:
            silhouette_avg = silhouette_score(X, cluster_labels)
            sil_scores[n_clusters] = silhouette_avg
            print(f"For n_clusters = {n_clusters}, the silhouette score is {silhouette_avg:.3f}")
        except Exception as e:
            print(f"Error calculating silhouette score for {n_clusters} clusters: {str(e)}")
    
    # Choose optimal number of clusters
    if sil_scores:
        best_n_clusters = max(sil_scores, key=sil_scores.get)
        print(f"\nOptimal number of clusters: {best_n_clusters}")
    else:
        best_n_clusters = 3  # Default fallback
        print("\nFalling back to default 3 clusters")
    
    # STEP 3: Perform final clustering
    kmeans = KMeans(n_clusters=best_n_clusters, random_state=42, n_init=10)
    agg['cluster'] = kmeans.fit_predict(X)
    
    # STEP 4: Enhanced visualization
    # Plot multiple views for better understanding
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # Plot 1: Spend vs Items
    for cluster in agg['cluster'].unique():
        subset = agg[agg['cluster'] == cluster]
        axes[0, 0].scatter(subset['avg_spend'], subset['total_items'], 
                          label=f'Cluster {cluster}', alpha=0.7)
    axes[0, 0].set_title("Spend vs Items by Cluster")
    axes[0, 0].set_xlabel("Average Spend")
    axes[0, 0].set_ylabel("Total Items Ordered")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Plot 2: Health Preference vs Festivity
    for cluster in agg['cluster'].unique():
        subset = agg[agg['cluster'] == cluster]
        axes[0, 1].scatter(subset['is_healthy'], subset['is_festive'], 
                          label=f'Cluster {cluster}', alpha=0.7)
    axes[0, 1].set_title("Health Preference vs Festivity by Cluster")
    axes[0, 1].set_xlabel("Health Preference Score")
    axes[0, 1].set_ylabel("Festivity Score")
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Plot 3: Unique Items vs Active Days
    for cluster in agg['cluster'].unique():
        subset = agg[agg['cluster'] == cluster]
        axes[1, 0].scatter(subset['unique_items'], subset['active_days'], 
                          label=f'Cluster {cluster}', alpha=0.7)
    axes[1, 0].set_title("Menu Variety vs Visit Frequency by Cluster")
    axes[1, 0].set_xlabel("Unique Menu Items Tried")
    axes[1, 0].set_ylabel("Number of Different Visit Days")
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 4: Parallel Coordinates for all features
    from pandas.plotting import parallel_coordinates
    
    # Create a temporary DataFrame for parallel coordinates
    parallel_df = agg[features + ['cluster']].copy()
    
    # Normalize data for parallel coordinates
    for feature in features:
        parallel_df[feature] = (parallel_df[feature] - parallel_df[feature].min()) / \
                             (parallel_df[feature].max() - parallel_df[feature].min())
    
    # Convert cluster to string for proper coloring
    parallel_df['cluster'] = parallel_df['cluster'].astype(str)
    
    try:
        parallel_coordinates(parallel_df, 'cluster', ax=axes[1, 1], alpha=0.5)
        axes[1, 1].set_title("Parallel Coordinates of All Features")
        axes[1, 1].grid(True, alpha=0.3)
    except Exception as e:
        print(f"Error creating parallel coordinates plot: {str(e)}")
        # Alternative plot if parallel coordinates fail
        axes[1, 1].text(0.5, 0.5, "Parallel coordinates plot unavailable", 
                      horizontalalignment='center', fontsize=12)
    
    plt.tight_layout()
    plt.show()
    
    # STEP 5: Interpret clusters with more detail
    # Add cluster sizes
    cluster_sizes = agg['cluster'].value_counts().to_dict()
    
    # Create summary stats
    cluster_summary = agg.groupby('cluster')[features].agg(['mean', 'std', 'min', 'max'])
    
    # Add percentage of total
    for cluster in agg['cluster'].unique():
        print(f"\nCluster {cluster} ({cluster_sizes.get(cluster, 0)} customers, "
              f"{cluster_sizes.get(cluster, 0)/len(agg)*100:.1f}% of total):")
        
        # Print stats for this cluster
        for feature in features:
            mean = cluster_summary.loc[cluster, (feature, 'mean')]
            std = cluster_summary.loc[cluster, (feature, 'std')]
            print(f"  - {feature}: {mean:.2f} (±{std:.2f})")
    
    # Print dataset-wide summary for comparison
    print("\nOverall Average Across All Clusters:")
    for feature in features:
        print(f"  - {feature}: {agg[feature].mean():.2f}")

except Exception as e:
    print(f"An error occurred during customer clustering: {str(e)}")

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV

try:
    # Validate that df exists and has required columns
    required_columns = ['order_date', 'day_of_the_week', 'food_item']
    
    # Check if df exists
    if 'df' not in locals() and 'df' not in globals():
        raise NameError("DataFrame 'df' is not defined. Please load your data first.")
    
    # Check for required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise KeyError(f"Missing required columns: {missing_columns}")
    
    # Create a copy to avoid modifying the original dataframe
    df_context = df.copy()
    
    # Ensure order_date is datetime type
    if not pd.api.types.is_datetime64_dtype(df_context['order_date']):
        print("Converting order_date to datetime format...")
        df_context['order_date'] = pd.to_datetime(df_context['order_date'], errors='coerce')
        
    # Drop rows with NaN in required columns
    initial_rows = len(df_context)
    df_context = df_context.dropna(subset=['order_date', 'day_of_the_week', 'food_item'])
    dropped_rows = initial_rows - len(df_context)
    if dropped_rows > 0:
        print(f"Dropped {dropped_rows} rows with missing values in required columns")
        
    if len(df_context) == 0:
        raise ValueError("No valid data after dropping missing values")
        
    # Add season based on order date with error handling
    def get_season(date):
        if pd.isna(date):
            return np.nan
        try:
            month_num = date.month
            season_num = (month_num % 12) // 3 + 1
            seasons = {1: 'Winter', 2: 'Spring', 3: 'Summer', 4: 'Fall'}
            return seasons.get(season_num, 'Unknown')
        except (AttributeError, TypeError):
            return np.nan
            
    df_context['season'] = df_context['order_date'].apply(get_season)
    
    # Add weekend flag with validation
    valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_check = df_context['day_of_the_week'].isin(valid_days)
    if not day_check.all():
        invalid_days = df_context.loc[~day_check, 'day_of_the_week'].unique()
        print(f"Warning: Found invalid day names: {invalid_days}")
        # Clean up invalid day names
        df_context = df_context[day_check]
    
    df_context['is_weekend'] = df_context['day_of_the_week'].isin(['Friday', 'Saturday', 'Sunday']).astype(int)
    
    # Simulate mood tags with improved error handling
    def simulate_mood(row):
        try:
            if pd.isna(row['season']) or pd.isna(row['is_weekend']):
                return np.nan
                
            if row['season'] == 'Winter' and row['is_weekend'] == 1:
                return 'comfort'
            elif row['season'] == 'Summer' and row['is_weekend'] == 0:
                return 'light'
            elif row['is_weekend'] == 1:
                return 'celebration'
            return 'normal'
        except Exception as e:
            print(f"Error in simulate_mood: {e}")
            return np.nan
            
    df_context['mood'] = df_context.apply(simulate_mood, axis=1)
    
    # Simulate weather tags with validation
    season_to_weather = {'Winter': 'cold', 'Spring': 'mild', 'Summer': 'hot', 'Fall': 'mild'}
    df_context['weather'] = df_context['season'].map(season_to_weather)
    
    # Drop any rows with NaN values in newly created columns
    pre_dropna = len(df_context)
    df_context = df_context.dropna(subset=['season', 'mood', 'weather'])
    if len(df_context) < pre_dropna:
        print(f"Dropped {pre_dropna - len(df_context)} rows with missing values in derived columns")
    
    # Check if we have enough unique food items
    unique_food_items = df_context['food_item'].nunique()
    if unique_food_items < 2:
        raise ValueError(f"Need at least 2 unique food items for classification, but only found {unique_food_items}")
    print(f"Number of unique food items: {unique_food_items}")
    
    # Drop food items with very few occurrences (optional)
    MIN_ITEM_COUNT = 3
    item_counts = df_context['food_item'].value_counts()
    rare_items = item_counts[item_counts < MIN_ITEM_COUNT].index
    if len(rare_items) > 0:
        print(f"Dropping {len(rare_items)} food items with fewer than {MIN_ITEM_COUNT} occurrences")
        df_context = df_context[~df_context['food_item'].isin(rare_items)]
    
    # Define features and target
    features = ['season', 'is_weekend', 'mood', 'weather']
    target = 'food_item'
    
    # Prepare data for model training
    encoded_df = df_context[features + [target]].copy()
    
    # Encode categorical features with improved error handling
    label_encoders = {}
    for col in features + [target]:
        if encoded_df[col].dtype == 'object' or encoded_df[col].dtype.name == 'category':
            try:
                le = LabelEncoder()
                encoded_df[col] = le.fit_transform(encoded_df[col])
                label_encoders[col] = le
            except Exception as e:
                print(f"Error encoding column {col}: {e}")
                raise
    
    # Store feature names for feature importance analysis
    feature_names = features.copy()
    
    # Split data with stratification to handle imbalance
    X = encoded_df[features]
    y = encoded_df[target]
    
    # Check for sufficient data
    if len(X) < 10:  # Arbitrary small threshold
        raise ValueError(f"Only {len(X)} samples available, which is too few for reliable modeling")
    
    # Perform stratified split to handle imbalanced classes
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Training data size: {len(X_train)}, Test data size: {len(X_test)}")
    
    # Check training data balance
    train_class_counts = pd.Series(y_train).value_counts()
    print("\nClass distribution in training data:")
    for class_id, count in train_class_counts.items():
        class_name = label_encoders[target].inverse_transform([class_id])[0]
        print(f"  {class_name}: {count} samples ({count/len(y_train)*100:.1f}%)")
    
    # Perform cross-validation to assess model stability
    cv_scores = []
    try:
        # Define model pipeline with scaling
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', RandomForestClassifier(random_state=42))
        ])
        
        # Simple hyperparameter tuning
        param_grid = {
            'classifier__n_estimators': [50, 100],
            'classifier__max_depth': [None, 10, 20]
        }
        
        # Use grid search with cross-validation
        grid_search = GridSearchCV(
            pipeline, param_grid, cv=5, scoring='accuracy', n_jobs=-1
        )
        
        grid_search.fit(X_train, y_train)
        
        # Get best model
        best_model = grid_search.best_estimator_
        print(f"\nBest parameters: {grid_search.best_params_}")
        
        # CV scores
        cv_scores = grid_search.cv_results_['mean_test_score']
        print(f"Cross-validation accuracy: {grid_search.best_score_:.3f}")
        
    except Exception as e:
        print(f"Error during cross-validation: {e}")
        print("Falling back to default RandomForest model...")
        best_model = RandomForestClassifier(n_estimators=100, random_state=42)
        best_model.fit(X_train, y_train)
    
    # Evaluate on test set
    y_pred = best_model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nTest set accuracy: {accuracy:.3f}")
    
    # Classification report with proper error handling for target names
    try:
        target_names = label_encoders[target].classes_
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=target_names))
    except Exception as e:
        print(f"Error creating classification report with target names: {e}")
        print("\nClassification Report (with numeric labels):")
        print(classification_report(y_test, y_pred))
    
    # Feature importance analysis
    if hasattr(best_model, 'named_steps') and hasattr(best_model.named_steps['classifier'], 'feature_importances_'):
        importances = best_model.named_steps['classifier'].feature_importances_
    elif hasattr(best_model, 'feature_importances_'):
        importances = best_model.feature_importances_
    else:
        importances = None
        
    if importances is not None:
        importance_df = pd.DataFrame({
            'Feature': feature_names,
            'Importance': importances
        }).sort_values('Importance', ascending=False)
        
        print("\nFeature Importance:")
        for _, row in importance_df.iterrows():
            print(f"  {row['Feature']}: {row['Importance']:.3f}")
    
    # Improved recommendation function with error handling
    def recommend_dish(season, is_weekend, mood, weather):
        """
        Recommend a dish based on context features.
        
        Parameters:
        -----------
        season : str
            One of 'Winter', 'Spring', 'Summer', 'Fall'
        is_weekend : int
            1 if weekend, 0 if weekday
        mood : str
            One of 'comfort', 'light', 'celebration', 'normal'
        weather : str
            One of 'cold', 'mild', 'hot'
            
        Returns:
        --------
        str
            Recommended dish name
        """
        try:
            # Validate inputs
            if season not in label_encoders['season'].classes_:
                raise ValueError(f"Invalid season '{season}'. Must be one of {list(label_encoders['season'].classes_)}")
            
            if not isinstance(is_weekend, (int, np.integer)) or is_weekend not in [0, 1]:
                raise ValueError("is_weekend must be 0 or 1")
                
            if mood not in label_encoders['mood'].classes_:
                raise ValueError(f"Invalid mood '{mood}'. Must be one of {list(label_encoders['mood'].classes_)}")
                
            if weather not in label_encoders['weather'].classes_:
                raise ValueError(f"Invalid weather '{weather}'. Must be one of {list(label_encoders['weather'].classes_)}")
                
            # Create input DataFrame
            input_df = pd.DataFrame([{
                'season': label_encoders['season'].transform([season])[0],
                'is_weekend': is_weekend,
                'mood': label_encoders['mood'].transform([mood])[0],
                'weather': label_encoders['weather'].transform([weather])[0]
            }])
            
            # Get top 3 predictions with probabilities
            if hasattr(best_model, 'predict_proba'):
                proba = best_model.predict_proba(input_df)
                top_indices = np.argsort(proba[0])[::-1][:3]
                
                recommendations = []
                for idx in top_indices:
                    dish = label_encoders[target].inverse_transform([idx])[0]
                    probability = proba[0][idx]
                    recommendations.append((dish, probability))
                    
                # Return top dish and show others
                print("\nTop 3 recommendations:")
                for dish, prob in recommendations:
                    print(f"  {dish}: {prob:.2f} probability")
                    
                return recommendations[0][0]  # Return the top dish
            else:
                # Fallback if predict_proba is not available
                pred = best_model.predict(input_df)[0]
                return label_encoders[target].inverse_transform([pred])[0]
                
        except Exception as e:
            print(f"Error in recommend_dish: {e}")
            # Return most common dish as fallback
            most_common = pd.Series(y_train).mode()[0]
            return label_encoders[target].inverse_transform([most_common])[0]
    
    # Example recommendation
    print("\nExample recommendation:")
    recommended = recommend_dish('Winter', 1, 'comfort', 'cold')
    print(f"Final recommendation: {recommended}")
    
    # Save model and encoders for future use (optional)
    # import joblib
    # joblib.dump(best_model, 'dish_recommender_model.pkl')
    # joblib.dump(label_encoders, 'dish_recommender_encoders.pkl')
    
except Exception as e:
    print(f"A critical error occurred: {str(e)}")
    print("Please check your data and ensure all required columns are present.")