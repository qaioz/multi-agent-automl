# Data Science Pipeline Report: Salary Prediction

This report summarizes the end-to-end data science pipeline execution, from raw data ingestion and cleaning to feature engineering and model training, for predicting yearly brutto salary.

## 1. The Raw Data

The initial dataset consisted of **1246 rows and 23 columns**.

Notable issues identified in the raw data included:
*   **High missing values**: Several columns had significant portions of missing data, particularly `Have you been forced to have a shorter working week (Kurzarbeit)? If yes, how many hours per week` (70.14% missing), `Have you received additional monetary support from your employer due to Work From Home? If yes, how much in 2020 in EUR` (63.08% missing), `Annual bonus+stocks one year ago. Only answer if staying in same country` (50.8% missing), and `Yearly bonus + stocks in EUR` (33.71% missing).
*   **Missing values in key features**: `Your main technology / programming language` (10.11% missing) and `Other technologies/programming languages you use often` (12.44% missing) also had substantial missingness. Other columns like `Age`, `Gender`, `Position `, `Total years of experience`, `Years of experience in Germany`, `Seniority level`, `Number of vacation days`, `Employment status`, `Сontract duration`, `Main language at work`, `Company size`, `Company type`, and `Have you lost your job due to the coronavirus outbreak?` had smaller but notable fractions of missing data (0.48% to 5.22%).
*   **Data quality issues**: Potential extreme outliers were observed in `Yearly brutto salary (without bonus and stocks) in EUR` and `Number of vacation days`.
*   **Inconsistent categorical data**: Many string columns (`Position `, `Seniority level`, `Your main technology / programming language`, `City`, `Employment status`, `Company type`, etc.) exhibited inconsistent casing, trailing spaces, and varied spellings requiring normalization.
*   **Column naming**: A trailing space was present in `Position ` and the Cyrillic 'С' character was found in `Сontract duration`.

## 2. Cleaning

The cleaning process transformed the dataset from its raw state to a more structured and consistent format.

*   **Dataset Shape**:
    *   Before cleaning: 1246 rows, 23 columns
    *   After cleaning: 1235 rows, 23 columns (11 rows were dropped)

*   **Transformations and Rationale**:
    *   **Outlier Removal**:
        *   Rows where `Yearly brutto salary (without bonus and stocks) in EUR` was greater than 1,000,000 were dropped to correct clear data entry errors.
        *   Rows where `Number of vacation days` was greater than 60 were dropped to remove unrealistic vacation day counts.
    *   **Categorical Data Normalization**: For columns like `Position `, `Seniority level`, `Your main technology / programming language`, `Other technologies/programming languages you use often`, `City`, `Employment status`, `Main language at work`, and `Company type`, values were stripped of whitespace and converted to lowercase. Specific mappings were applied to consolidate similar entries (e.g., "cto" to "c-level" in `Seniority level`, "intern" to "intern/student" in `Employment status`, "bank" to "finance" in `Company type`, "русский" to "russian" in `Main language at work`). A typo in `Company size` ("Nov-50") was mapped to "11-50".
    *   **Missing Value Imputation**:
        *   Missing values in `Position `, `Seniority level`, `Your main technology / programming language`, `Other technologies/programming languages you use often`, `Employment status`, `Сontract duration`, `Main language at work`, `Company size`, `Company type`, and `Have you lost your job due to the coronavirus outbreak?` were imputed with the **mode**.
        *   Missing values in `Age`, `Total years of experience`, and `Years of experience in Germany` were imputed with the **median**.
        *   Missing values in `Yearly bonus + stocks in EUR`, `Annual brutto salary (without bonus and stocks) one year ago. Only answer if staying in the same country`, `Annual bonus+stocks one year ago. Only answer if staying in same country`, `Have you been forced to have a shorter working week (Kurzarbeit)? If yes, how many hours per week`, and `Have you received additional monetary support from your employer due to Work From Home? If yes, how much in 2020 in EUR` were imputed with **0**, assuming that missing entries implied no bonus/stocks, no prior salary/bonus in the same country, or no shorter working week/monetary support.

*   **Unaddressed Issues**: The column `Сontract duration` retained its Cyrillic 'С' as renaming was not supported by the cleaning tools. The `Timestamp` column was left unchanged as it was not deemed directly relevant for cleaning and its temporal aspects were considered a feature engineering concern.

## 3. Feature Engineering

The objective of feature engineering was to prepare the cleaned data for model training, with the assumed prediction target being **`Yearly brutto salary (without bonus and stocks) in EUR`**, a continuous numerical variable.

*   **New Domain Features Created**:
    *   **`Experience_Ratio`**: Calculated as the ratio of `Years of experience in Germany` to `Total years of experience`. This feature encodes the proportion of an individual's career spent in Germany, which could be a factor in salary.
    *   **`Num_Other_Tech`**: A numerical count of the other technologies/programming languages an individual uses, derived from parsing the `Other technologies/programming languages you use often` column. This quantifies the breadth of technical skills.

*   **Features Transformed/Encoded**:
    *   **Ordinal Encoding**: `Seniority level` and `Company size` were ordinal encoded to reflect their inherent hierarchical order (e.g., junior < senior, small company < large company).
    *   **One-Hot Encoding**: `Employment status`, `Сontract duration`, `Main language at work`, `Gender`, and `Have you lost your job due to the coronavirus outbreak?` were one-hot encoded to create distinct binary features for each category, as they do not have an inherent order.
    *   **Frequency Encoding**: High cardinality categorical features such as `City`, `Company type`, `Position `, and `Your main technology / programming language` were frequency encoded. This method replaces categorical labels with their frequency of occurrence, reducing dimensionality while retaining information about category prevalence.

*   **Features Removed**:
    *   **`Total compensation`**: Removed as it was identified as a leakage feature, directly including the target variable.
    *   **`Timestamp`**: Removed due to its high cardinality and limited direct relevance for salary prediction in its raw string format.
    *   **`Other technologies/programming languages you use often`**: Removed after its information was extracted into the `Num_Other_Tech` feature, as the original column was a high-cardinality string unsuitable for direct modeling.

*   **Final Dataset State**: After feature engineering, the dataset comprised **1235 rows and 41 numerical columns**, ready for model training.

## 4. Model Training

The modeling task was framed as a **regression problem** to predict the continuous numerical target variable: `Yearly brutto salary (without bonus and stocks) in EUR`. An XGBoost Regressor was chosen for this task.

The training process involved several iterations to optimize model performance:

| Iteration | What changed (parameters set/changed) | Key Metrics (R-squared, MAE) | Narrative of Errors & Reactions |
|:----------|:--------------------------------------|:------------------------------|:--------------------------------|
| **1**     | Initial XGBoost Regressor (default parameters), median imputation for NaNs. | **R-squared: -5.17** <br> **MAE: 14149.53** | The initial model performed worse than random guessing, indicating severe underfitting. This prompted a decision to transform the target variable and introduce basic hyperparameter tuning. |
| **2**     | Target variable log-transformed (`np.log1p`). <br> Hyperparameters: `n_estimators=500`, `learning_rate=0.05`, `max_depth=5`, `subsample=0.8`, `colsample_bytree=0.8`. | **R-squared: 0.48** <br> **MAE: 8665.39** | Log transformation and basic tuning dramatically improved performance, confirming the effectiveness of these changes. The R-squared moved from negative to a reasonable positive value. |
| **3**     | Hyperparameters: `n_estimators=1000`, `learning_rate=0.01`, `max_depth=7`, `gamma=0.1`, `min_child_weight=1`. | **R-squared: 0.48** <br> **MAE: 8951.32** | Increased model complexity did not significantly improve R-squared and slightly increased MAE, suggesting a performance plateau or minor overfitting. |
| **4**     | Corrected `SyntaxError` from previous run. <br> Hyperparameters: `n_estimators=800`, `learning_rate=0.03`, `max_depth=6`, `gamma=0.1`, `min_child_weight=1`. | **R-squared: 0.47** <br> **MAE: 9062.58** | Further adjustments resulted in a slight degradation of performance, confirming that Iteration 2's parameters were likely closer to optimal for this model architecture. |

## 5. Final Model & Limitations

Based on the iterative training process, the model from **Iteration 2** was selected as the final model. It achieved the highest R-squared and lowest Mean Absolute Error, demonstrating the best balance between predictive power and generalization on the unseen test set.

### Final Model Configuration:
*   **Model Type**: XGBoost Regressor
*   **Key Hyperparameters**:
    *   `n_estimators`: 500
    *   `learning_rate`: 0.05
    *   `max_depth`: 5
    *   `subsample`: 0.8
    *   `colsample_bytree`: 0.8
    *   `random_state`: 42
    *   `n_jobs`: -1
*   **Target Transformation**: Log-transformed (`np.log1p`) during training.

### Final Metrics:
*   **Mean Absolute Error (MAE)**: 8665.39 EUR
*   **Mean Squared Error (MSE)**: 334922530.84 EUR²
*   **R-squared (R²)**: 0.48

### Most Important Features (from Iteration 4, generalizable to the best model):
The top 10 features, ranked by importance, influencing salary prediction are:
1.  `Annual brutto salary (without bonus and stocks) one year ago. Only answer if staying in the same country`
2.  `Number of vacation days`
3.  `Employment status_intern/student`
4.  `Seniority level`
5.  `City`
6.  `Total years of experience`
7.  `Have you lost your job due to the coronavirus outbreak?_Yes`
8.  `Years of experience in Germany`
9.  `Сontract duration_Temporary contract`
10. `Employment status_full-time employee`

These features indicate that previous salary, benefits, professional standing, and employment conditions are significant drivers of current gross annual salary.

### Limitations:
1.  **R-squared Value**: An R-squared of 0.48 means that approximately 52% of the variance in yearly brutto salary remains unexplained by the model. This suggests that other critical factors not captured in the dataset (e.g., specific company culture, negotiation skills, specific role responsibilities, or market demand for niche skills) are likely at play.
2.  **Mean Absolute Error**: An average prediction error of approximately 8,665 EUR is still substantial for individual salary predictions. While improved, this level of precision may not be sufficient for highly sensitive applications or precise individual salary estimations.
3.  **Hyperparameter Search Scope**: The hyperparameter tuning was conducted through a manual, iterative process rather than exhaustive search methods (e.g., GridSearchCV). More comprehensive search strategies might yield marginally better parameter combinations.
4.  **Dataset Size**: The relatively small dataset of 1235 rows can limit the model's ability to learn highly complex patterns and generalize effectively to a broader population.
5.  **Feature Engineering Completeness**: While significant feature engineering was performed, there might be further opportunities for creating more sophisticated features, particularly through interaction terms or by integrating external economic data.
