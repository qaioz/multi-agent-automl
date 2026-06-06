# Feature Engineering Report

## Assumed Prediction Target
The assumed prediction target is **Yearly brutto salary (without bonus and stocks) in EUR**. This is a continuous numerical variable that represents the primary income for individuals and is a common target in compensation analysis. Other features in the dataset are likely to influence this value, making it a suitable target for predictive modeling.

## Feature Engineering Strategy

| Feature | New/Transformed/Removed | What it encodes | Why |
|:---|:---|:---|:---|
| `Total compensation` | Removed | Sum of base salary and bonuses/stocks | Identified as a leakage feature because it directly includes the target variable and other future compensation, making it unsuitable for predicting `Yearly brutto salary (without bonus and stocks) in EUR`. |
| `Experience_Ratio` | New | Proportion of total experience gained in Germany | Created to capture how much of an individual's career was spent in Germany, which could influence salary expectations and offerings. |
| `Num_Other_Tech` | New | Count of other technologies/programming languages used | Created to quantify the breadth of an individual's technical skills, potentially correlating with higher compensation due to versatility. |
| `Seniority level` | Transformed (Ordinal Encoded) | Hierarchical professional standing | Encoded as ordinal to reflect the inherent order in seniority levels (junior to founder), providing a numerical representation for modeling. Some unmapped values were set to NaN. |
| `Company size` | Transformed (Ordinal Encoded) | Company scale | Encoded as ordinal to capture the ordered nature of company sizes, from small to large corporations. Some unmapped values were set to NaN. |
| `Employment status` | Transformed (One-Hot Encoded) | Type of employment | One-hot encoded to represent different employment categories without implying any inherent order, creating separate binary features. |
| `Сontract duration` | Transformed (One-Hot Encoded) | Contract type | One-hot encoded to differentiate between temporary and unlimited contracts without imposing an order. |
| `Main language at work` | Transformed (One-Hot Encoded) | Primary language used in the workplace | One-hot encoded to represent different main languages without implying any inherent order. |
| `Gender` | Transformed (One-Hot Encoded) | Gender identity | One-hot encoded to represent gender categories without implying any inherent order. |
| `Have you lost your job due to the coronavirus outbreak?` | Transformed (One-Hot Encoded) | Impact of COVID-19 on employment | One-hot encoded to capture the binary outcome of job loss due to the pandemic. |
| `City` | Transformed (Frequency Encoded) | Prevalence of each city in the dataset | Frequency encoded to reduce dimensionality while preserving information about the commonality of each city, as one-hot encoding would create too many columns. |
| `Company type` | Transformed (Frequency Encoded) | Prevalence of each company type in the dataset | Frequency encoded for similar reasons as `City`, handling a high cardinality categorical feature efficiently. |
| `Position ` | Transformed (Frequency Encoded) | Prevalence of each job position in the dataset | Frequency encoded to manage the high number of unique job positions and provide a numerical representation. |
| `Your main technology / programming language` | Transformed (Frequency Encoded) | Prevalence of each main technology/programming language | Frequency encoded to handle the high cardinality of programming languages and provide a numerical representation. |
| `Timestamp` | Removed | Time of survey submission | Removed as it is a string with high cardinality and is not directly useful for predicting yearly salary, and its temporal components are unlikely to be strong predictors given the target. |
| `Other technologies/programming languages you use often` | Removed | List of other technologies/programming languages | Removed as its information has been captured by the `Num_Other_Tech` feature, and the original column is a high-cardinality string unsuitable for direct modeling. |

## Final State of the Dataset
- **Shape**: 1235 rows, 41 columns
- **Numeric-ready columns**: All remaining columns are now numerical (float64 or int64) and ready for model training.
- **Columns left as text on purpose**: None. All textual columns that were deemed relevant have been encoded into numerical formats. Irrelevant or redundant textual columns have been removed. The Model Trainer should be aware of the NaN values introduced by ordinal encoding in 'Seniority level' and 'Company size', which may require imputation or specific handling depending on the chosen model.