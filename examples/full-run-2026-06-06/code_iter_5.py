import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.impute import SimpleImputer

# Load the dataset
df = pd.read_csv("02_engineered_data.csv")

# Define target and features
target_column = "Yearly brutto salary (without bonus and stocks) in EUR"
X = df.drop(columns=target_column)
y = df[target_column]

# Handle potentially problematic target values before log transformation
# Ensure target values are positive for log transformation
if (y <= 0).any():
    print("Warning: Non-positive target values found. Adjusting them for log transformation.")
    y = y.apply(lambda x: x if x > 0 else 1) # Replace non-positive with 1 to allow log(1)=0

# Apply log transformation to the target variable
y_transformed = np.log1p(y) # log1p handles 0 values gracefully, log(1+x)

# Impute NaN values in features using SimpleImputer for consistency
imputer = SimpleImputer(strategy='median')
X_imputed = pd.DataFrame(imputer.fit_transform(X), columns=X.columns, index=X.index)

# Split data into training and testing sets
X_train, X_test, y_train_transformed, y_test_transformed = train_test_split(X_imputed, y_transformed, test_size=0.2, random_state=42)
y_train, y_test = train_test_split(X_imputed, y, test_size=0.2, random_state=42)[2:] # Keep original y_test for inverse transformation check

# Initialize and train XGBoost Regressor with adjusted hyperparameters
xgb_params = {
    'n_estimators': 800, # Slightly reduced estimators
    'learning_rate': 0.03, # Increased learning rate from 0.01
    'max_depth': 6, # Reduced max_depth from 7
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'gamma': 0.1,
    'min_child_weight': 1,
    'random_state': 42,
    'n_jobs': -1
}
xgb_model = XGBRegressor(**xgb_params)
xgb_model.fit(X_train, y_train_transformed)

# Make predictions on the test set (transformed scale)
y_pred_transformed = xgb_model.predict(X_test)

# Inverse transform predictions to original scale
y_pred = np.expm1(y_pred_transformed) # expm1 is inverse of log1p

# Evaluate the model on the original scale
mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"Mean Absolute Error (original scale): {mae:.2f}")
print(f"Mean Squared Error (original scale): {mse:.2f}")
print(f"R-squared (original scale): {r2:.2f}")

# Get feature importances
feature_importances = xgb_model.feature_importances_
feature_names = X_imputed.columns
importance_df = pd.DataFrame({
    'feature': feature_names,
    'importance': feature_importances
}).sort_values(by='importance', ascending=False)

print("\nTop 10 Feature Importances:")
print(importance_df.head(10).to_string(index=False))

# Prepare and print METRICS_JSON
metrics = {
    "params": xgb_params,
    "metrics": {
        "MAE": mae,
        "MSE": mse,
        "R-squared": r2
    }
}

import json
print(f"METRICS_JSON: {json.dumps(metrics)}")