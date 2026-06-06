# Data Cleaning Report

## Dataset Shape
- Before cleaning: 1246 rows, 23 columns
- After cleaning: 1235 rows, 23 columns

## Decisions Table

| Column | Issue (with the evidence) | Action | Why |
|---|---|---|---|
| Yearly brutto salary (without bonus and stocks) in EUR | Extreme outlier values (e.g., 99,999,999,999.0) | Drop rows where salary > 1,000,000 | Correct clear data entry errors and preserve valid high salaries. |
| Number of vacation days | Extreme outlier values (e.g., 365.0, 99.0) and 0.0 | Drop rows where vacation days > 60 | Remove unrealistic vacation day counts while keeping plausible ones. |
| Position | Trailing space in column name, 143 unique values with inconsistent casing and possible duplicates. | Normalize: strip whitespace, lowercase all values; impute missing with mode. | Standardize categories and handle missing values without losing information. |
| Seniority level | 22 unique values with inconsistent casing ("CTO" vs. "C-level"), similar meanings ("Entry level" vs. "Junior"), and irrelevant entries ("Self employed"). | Normalize: strip whitespace, lowercase all values; Map "cto", "c-level executive manager" to "c-level"; "entry level", "intern", "working student", "student" to "junior"; "self employed", "no idea, there are no ranges in the firm " to null; "manager" to "middle"; impute missing with mode. | Standardize and consolidate seniority levels for better analysis. |
| Your main technology / programming language | 253 unique values with inconsistent casing and spaces (e.g., "Python", "python", "Python "). | Normalize: strip whitespace, lowercase all values; impute missing with mode. | Reduce variety and standardize programming language entries. |
| Other technologies/programming languages you use often | 559 unique values with inconsistent casing and spaces. | Normalize: strip whitespace, lowercase all values; impute missing with mode. | Basic standardization to prepare for potential feature engineering. |
| City | 118 unique values with inconsistent spelling (e.g., "Stuttgart" vs. "Stuttgart ", "Düsseldorf" vs. "Dusseldorf"). | Normalize: strip whitespace, lowercase all values. | Standardize city names for consistent categorical data. |
| Employment status | 11 unique values with inconsistent casing and redundant descriptions (e.g., "Intern" vs. "working student", complex full-time/part-time/freelancing entry). | Normalize: strip whitespace, lowercase all values; Map "intern", "working student", "werkstudent", and specific student entry to "intern/student"; "full-time position, part-time position, & self-employed (freelancing, tutoring)" to "mixed employment"; "company director" to "founder/director"; impute missing with mode. | Consolidate and clarify employment categories. |
| Сontract duration | Cyrillic 'С' in column name, '0' as an invalid entry. | Map "0" to null; impute missing with mode. | Correct invalid entry and handle missing values. |
| Main language at work | 14 unique values with inconsistent casing (e.g., "Russian" vs. "Русский") and multiple language entries. | Normalize: strip whitespace, lowercase all values; Map "русский" to "russian"; all mixed language entries to "multiple"; impute missing with mode. | Standardize language entries and group mixed languages. |
| Company size | "Nov-50" typo. | Map "nov-50" to "11-50"; impute missing with mode. | Correct typo for accurate company size categories. |
| Company type | 62 unique values with inconsistent casing (e.g. "Corporation" vs. "Corporation "), ambiguous descriptions, and related terms not grouped. | Normalize: strip whitespace, lowercase all values; Map "bank", "finance", "fintech" to "finance"; "corporate incubator" to "startup"; "full-time position in education, part-time position in at a data startup" to null; impute missing with mode. | Standardize company types and consolidate similar categories. |
| Age | 27 missing values (2.17% missing_frac) | Impute missing with median. | Small fraction of missing data; median is robust to outliers. |
| Total years of experience | 16 missing values (1.28% missing_frac) | Impute missing with median. | Small fraction of missing data; median is robust to outliers. |
| Years of experience in Germany | 32 missing values (2.57% missing_frac) | Impute missing with median. | Small fraction of missing data; median is robust to outliers. |
| Yearly bonus + stocks in EUR | 420 missing values (33.71% missing_frac) | Impute missing with 0. | Assume missing means no bonus/stocks. |
| Annual brutto salary (without bonus and stocks) one year ago. Only answer if staying in the same country | 362 missing values (29.05% missing_frac) | Impute missing with 0. | Assume missing means no prior salary in same country. |
| Annual bonus+stocks one year ago. Only answer if staying in same country | 633 missing values (50.8% missing_frac) | Impute missing with 0. | Assume missing means no prior bonus/stocks in same country. |
| Have you been forced to have a shorter working week (Kurzarbeit)? If yes, how many hours per week | 874 missing values (70.14% missing_frac) | Impute missing with 0. | Assume missing means not forced to have a shorter working week. |
| Have you received additional monetary support from your employer due to Work From Home? If yes, how much in 2020 in EUR | 786 missing values (63.08% missing_frac) | Impute missing with 0. | Assume missing means no additional monetary support. |
| Have you lost your job due to the coronavirus outbreak? | 20 missing values (1.61% missing_frac) | Impute missing with mode. | Small fraction of missing data; mode is appropriate for categorical. |

## What I did NOT fix and why
- **Timestamp**: Left as is. While it could be converted to datetime, it's not directly used for analysis in this cleaning phase.
- **Gender**: Left as is. The categories are clean, and the missing count is small enough not to warrant imputation without further context.
- **Yearly brutto salary (without bonus and stocks) in EUR** (after initial outlier removal): The remaining maximum value of 760,000 EUR, while high, is plausible for top positions and not clearly a data entry error.
- **Yearly bonus + stocks in EUR** (after initial outlier removal): The remaining maximum of 1,150,000 EUR is plausible for high-level compensation packages.
- **Annual bonus+stocks one year ago**: The maximum of 300,000 EUR is plausible for high-level compensation and not a clear outlier.
- **Your main technology / programming language** (after normalization): While the number of unique values was reduced, a more granular mapping was deemed a feature engineering task rather than a cleaning task, as it would require domain expertise to group similar languages or identify primary vs. secondary usage.
- **Other technologies/programming languages you use often** (after normalization): Similar to 'Your main technology / programming language', further detailed categorization or parsing of multi-technology entries is considered a feature engineering task.
- **Columns with Cyrillic 'С'**: I noted that column renaming was not supported by the available tools, therefore I had to proceed with the original column name `Сontract duration` rather than `Contract duration` for the mapping and imputation steps. This is a known limitation.
