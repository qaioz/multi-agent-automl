# Model Training Report

## Target Column and Framing Choice
The target column chosen for this task is **`Yearly brutto salary (without bonus and stocks) in EUR`**. This was an explicit recommendation from the Feature Engineering Report and represents a continuous numerical variable, making the problem a **regression** task. The objective is to predict an individual's gross annual salary.

## Iteration-by-Iteration Summary

### Iteration 1: Initial Baseline Model
- **Output observed**: The initial model yielded an extremely poor R-squared of **-5.17** and a Mean Absolute Error (MAE) of **14149.53**. This indicated that the default XGBoost Regressor performed worse than simply predicting the mean of the target variable, suggesting severe underfitting or issues with the target variable's distribution.
- **Changes made**: I hypothesized that the target variable's distribution (salary) might be heavily skewed. I decided to apply a **log transformation** (`np.log1p`) to the target variable to make its distribution more Gaussian-like. I also decided to introduce some basic **hyperparameter tuning** for XGBoost, setting `n_estimators=500`, `learning_rate=0.05`, and `max_depth=5` to move away from default and provide a more robust starting point. NaN values in features were imputed with the median using `SimpleImputer` for consistency.
- **Outcome**: The model's performance improved dramatically, as detailed in Iteration 2.

### Iteration 2: Log Transformation and Basic Tuning
- **Output observed**: The R-squared increased significantly to **0.48**, and the MAE dropped to **8665.39**. This confirmed that the log transformation of the target variable and the initial hyperparameter adjustments were very effective in improving the model's predictive power.
- **Changes made**: Given the substantial improvement, I aimed to further optimize the hyperparameters for potentially better performance. I decided to increase `n_estimators` to 1000, decrease `learning_rate` to 0.01 for more gradual learning, and increase `max_depth` to 7 to allow for capturing more complex patterns. I also added `gamma` (0.1) and `min_child_weight` (1) for additional regularization.
- **Outcome**: The changes in hyperparameters did not lead to a significant improvement, and in some cases, slightly degraded performance, as detailed in Iteration 3.

### Iteration 3: Further Hyperparameter Tuning (Increased Complexity)
- **Output observed**: The R-squared remained effectively at **0.48** (specifically 0.4826), and the MAE slightly increased to **8951.32**. This indicated that increasing model complexity with the chosen hyperparameters did not result in better generalization and might have led to slight overfitting or a plateau in performance.
- **Changes made**: Recognizing the plateau and slight increase in MAE, I aimed to simplify the model slightly to improve generalization. I decided to reduce `max_depth` to 6 and increase `learning_rate` back to 0.03. I also planned to extract and print feature importances to gain insights into the most influential features.
- **Outcome**: The execution failed due to a `SyntaxError` related to incorrect quote escaping, preventing evaluation of the hyperparameter changes.

### Iteration 4: Syntax Fix and Adjusted Hyperparameters (Reduced Complexity)
- **Output observed**: The previous run failed due to a `SyntaxError`. The current run successfully executed. The R-squared slightly decreased to **0.47**, and the MAE increased to **9062.58**. This confirmed that further adjustments to the hyperparameters did not improve the model and slightly degraded its performance compared to Iteration 2's results.
- **Changes made**: The syntax error was fixed. No further changes to model hyperparameters were made as the results suggested a performance plateau.
- **Outcome**: The model's performance slightly declined, confirming that the hyperparameters from Iteration 2 were likely closer to the optimal sweet spot for this dataset within the chosen model architecture. This iteration also provided valuable feature importances.

## Final Model and Metrics
Based on the iterative process, the model from **Iteration 2** demonstrated the best balance of performance (highest R-squared and lowest MAE) without significant overfitting. Although Iteration 3 had a marginally higher R-squared, the MAE was also higher, and the subsequent attempts showed degradation. Therefore, the model with the following parameters is considered the best:

**Hyperparameters:**
```json
{
    "n_estimators": 500,
    "learning_rate": 0.05,
    "max_depth": 5,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "n_jobs": -1
}
```

**Final Metrics:**
```json
{
    "MAE": 8665.39,
    "MSE": 334922530.84,
    "R-squared": 0.48
}
```

## Most Important Features (from Iteration 4, though relevant for the best model)
The top 10 most important features, indicating their influence on salary prediction, are:
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

It is clear that past salary is a dominant predictor, followed by benefits (`Number of vacation days`), employment status, professional seniority, and geographical/experience factors.

## Limitations
1.  **R-squared Value**: While an R-squared of 0.48 is a reasonable improvement from the baseline, it implies that roughly 52% of the variance in salary is still unexplained by the current features and model. This suggests that other influential factors not present in the dataset (e.g., specific company, negotiation skills, niche skills, precise role responsibilities) or more complex interactions are at play.
2.  **MAE**: An average error of ~8,665 EUR, while improved, is still significant for salary prediction, indicating that the model's predictions might not be precise enough for individual-level decision-making without further refinement.
3.  **Hyperparameter Search**: The hyperparameter tuning was relatively manual and not exhaustive. More advanced techniques like GridSearchCV or RandomizedSearchCV could potentially find slightly better parameter combinations, but these are computationally intensive and were limited by the sandbox environment.
4.  **Data Size**: The dataset size (1235 rows) is relatively small for complex predictive tasks, which can limit the model's ability to learn very subtle patterns and generalize well.
5.  **Feature Engineering**: Although an initial feature engineering phase was completed, there might be opportunities for more sophisticated feature creation, especially around interactions between existing features or external data sources, that could further boost model performance.