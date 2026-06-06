
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Load the dataset
df = pd.read_csv("02_engineered_data.csv")

# Define target and features
target_column = "Yearly brutto salary (without bonus and stocks) in EUR"
X = df.drop(columns=target_column)
y = df[target_column]

# Handle NaN values: Impute with median for numerical columns
# Although the report says all columns are numeric-ready, NaN values from ordinal encoding are mentioned.
for col in X.columns:
    if X[col].isnull().any():
        if pd.api.types.is_numeric_dtype(X[col]):
            X[col] = X[col].fillna(X[col].median())
        else:
            # If there are any non-numeric columns somehow, handle them (though report says none)
            X[col] = X[col].fillna(X[col].mode()[0]) # For categorical, impute with mode

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Initialize and train XGBoost Regressor
# Using default parameters for the first run
xgb_model = XGBRegressor(random_state=42)
xgb_model.fit(X_train, y_train)

# Make predictions on the test set
y_pred = xgb_model.predict(X_test)

# Evaluate the model
mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"Mean Absolute Error: {mae:.2f}")
print(f"Mean Squared Error: {mse:.2f}")
print(f"R-squared: {r2:.2f}")

# Prepare and print METRICS_JSON
metrics = {
    "params": {
        "n_estimators": xgb_model.n_estimators,
        "learning_rate": xgb_model.learning_rate,
        "max_depth": xgb_model.max_depth,
        "subsample": xgb_model.subsample,
        "colsample_bytree": xgb_model.colsample_bytree
    },
    "metrics": {
        "MAE": mae,
        "MSE": mse,
        "R-squared": r2
    }
}

import json
print(f"METRICS_JSON: {json.dumps(metrics)}")
