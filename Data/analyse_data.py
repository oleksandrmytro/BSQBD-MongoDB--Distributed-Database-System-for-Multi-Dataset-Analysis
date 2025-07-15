# analyse_data_modified.py
import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import LogLocator, LogFormatterMathtext

# 1. Paths to files
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"   # raw CSV files
CLEAN_DIR = BASE_DIR      # save cleaned CSVs here
CLEAN_DIR.mkdir(exist_ok=True)

files = {
    "amazon": "amazon.csv",
    "googleplaystore": "googleplaystore.csv",
    "vgsales": "vgsales.csv",
    "reviews": "googleplaystore_user_reviews.csv"
}

# 2. Cleaning functions
def clean_amazon(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["price_before_discount"] = (
        df["actual_price"].str.replace(r"[^\d.]", "", regex=True).astype(float)
    )
    df["price_after_discount"] = (
        df["discounted_price"].str.replace(r"[^\d.]", "", regex=True).astype(float)
    )
    df["discount_percentage"] = df["discount_percentage"].str.rstrip("%").astype(float)

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.dropna(subset=["rating"]).reset_index(drop=True)

    df["rating_count"] = (
        df["rating_count"].str.replace(",", "", regex=False)
        .pipe(pd.to_numeric, errors="coerce").fillna(0).astype(int)
    )

    df = df.drop(columns=["actual_price", "discounted_price"])
    return df


def clean_google(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
    df["Installs"] = pd.to_numeric(
        df["Installs"].str.replace(r"[+,]", "", regex=True),
        errors="coerce"
    )

    df["Price"] = pd.to_numeric(df["Price"].str.replace(r"\$", "", regex=True), errors="coerce")
    df = df.dropna(subset=["Rating", "Installs"]).reset_index(drop=True)

    df["Installs"] = df["Installs"].astype(int)
    return df

def clean_vgsales(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.dropna(subset=["Year", "Global_Sales"]).reset_index(drop=True)
    df["Year"] = df["Year"].astype(int)
    return df

def clean_reviews(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["Sentiment"]).copy()

    df["Translated_Review"] = df["Translated_Review"].fillna("").astype(str).str.strip()

    df = df[df["Translated_Review"].str.len() > 0]
    df = df[~df["Translated_Review"].str.fullmatch(r"\d+")]

    df["Sentiment_Polarity"]    = pd.to_numeric(df["Sentiment_Polarity"],    errors="coerce")
    df["Sentiment_Subjectivity"]= pd.to_numeric(df["Sentiment_Subjectivity"],errors="coerce")

    df = df.dropna(subset=["Sentiment_Polarity","Sentiment_Subjectivity"]).reset_index(drop=True)
    return df

clean_map = {
    "amazon": clean_amazon,
    "googleplaystore": clean_google,
    "vgsales": clean_vgsales,
    "reviews": clean_reviews
}

# 3. Load, clean, and save datasets
print("-> Cleaning and saving datasets...")
data = {}
for key, fname in files.items():
    raw_path = RAW_DIR / fname
    clean_path = CLEAN_DIR / fname
    print(f"Loading:  {raw_path}")
    df_raw = pd.read_csv(raw_path, encoding="utf-8")
    df_clean = clean_map[key](df_raw)
    print(f"Saving:   {clean_path}\n")
    df_clean.to_csv(clean_path, index=False, encoding="utf-8")
    data[key] = df_clean
print("✓ All files cleaned and saved.\n")

# 4. Amazon dataset diagnostics and statistics
amazon = data["amazon"]
print("--- Amazon Dataset Diagnostics ---")
# Preview and describe price columns
display_cols = ['price_before_discount', 'price_after_discount']
print(amazon[display_cols].head(5))
print(amazon[display_cols].describe())

# Filter out the top 1% of price_before_discount for mean calculation
p99 = amazon['price_before_discount'].quantile(0.99)
amazon_filtered = amazon[amazon['price_before_discount'] <= p99].copy()
print(f"Filtering out price_before_discount > {p99:.2f} (99th percentile)\n")

# Convert prices from INR to USD (adjust the rate as needed)
INR_TO_USD_RATE = 90.75  # 1 USD = 90.75 INR
amazon_filtered.loc[:, 'price_before_usd'] = amazon_filtered['price_before_discount'] / INR_TO_USD_RATE
amazon_filtered.loc[:, 'price_after_usd']  = amazon_filtered['price_after_discount']  / INR_TO_USD_RATE

# Compute averages on filtered USD data
print("--- Amazon Dataset Statistics (filtered) ---")
avg_before = amazon_filtered['price_before_usd'].mean()
avg_after  = amazon_filtered['price_after_usd'].mean()
avg_pct    = amazon_filtered['discount_percentage'].mean()
print(f"Average price before discount: {avg_before:.2f} USD")
print(f"Average price after discount:  {avg_after:.2f} USD")
print(f"Average discount percentage:    {avg_pct:.2f}%")

# Validate discount calculation from price columns
calc_pct = (
    (amazon_filtered['price_before_discount'] - amazon_filtered['price_after_discount'])
    / amazon_filtered['price_before_discount'] * 100
).mean()
print(f"Calculated average discount from prices: {calc_pct:.2f}%")

# Ratings summary on filtered set
print(f"Average rating: {amazon_filtered['rating'].mean():.2f} stars")
print(f"Median rating:  {amazon_filtered['rating'].median():.2f} stars")

# 5. Google Play Store statistics
google = data["googleplaystore"]
print("--- Google Play Store Dataset Statistics ---")
print(f"Total apps: {google.shape[0]}")
print(f"Number of categories: {google['Category'].nunique()}")
# Top 3 categories by app count
top_gp = google['Category'].value_counts().head(3)
print("Top 3 categories by app count:")
for cat, cnt in top_gp.items():
    print(f"  {cat}: {cnt} apps")
# Least represented categories
least_gp = google['Category'].value_counts().nsmallest(2).index.tolist()
print(f"On the other hand, least represented categories are {least_gp[0]} and {least_gp[1]}.")
# Ratings summary
missing_ratings_pct = google['Rating'].isna().mean() * 100
print(f"Percentage of apps without rating: {missing_ratings_pct:.2f}%")
print(f"Average rating (rated apps only): {google['Rating'].mean():.2f} stars")
# Installs summary
print(f"Median installs: {google['Installs'].median():,}")
# Free vs Paid apps
free_pct = (google['Type'] == 'Free').mean() * 100
paid_pct = (google['Type'] == 'Paid').mean() * 100
print(f"Free apps: {free_pct:.1f}%, Paid apps: {paid_pct:.1f}%")
print(f"Average price of paid apps: {google[google['Type'] == 'Paid']['Price'].mean():.2f} USD")
# Correlation between installs and rating
corr_installs_rating = google[['Installs', 'Rating']].corr().iloc[0, 1]
print(f"Correlation between installs and rating: {corr_installs_rating:.2f}")

# 6. Video Game Sales dataset statistics
vgsales = data["vgsales"]
print("--- Video Game Sales Dataset Statistics ---")
print(f"Total games: {vgsales.shape[0]}")
print(f"Year range: {vgsales['Year'].min()}–{vgsales['Year'].max()}")
print(f"Average global sales: {vgsales['Global_Sales'].mean():.2f} million")
print(f"Median global sales: {vgsales['Global_Sales'].median():.2f} million")
print(f"Total global sales: {vgsales['Global_Sales'].sum():.2f} million")
# Top games
top_games = vgsales.groupby('Name')['Global_Sales'].sum().sort_values(ascending=False).head(3)
print("Top 3 games by global sales:")
for name, sales in top_games.items():
    print(f"  {name}: {sales:.2f} million")
# Region sales
total_by_region = vgsales[['NA_Sales', 'EU_Sales', 'JP_Sales', 'Other_Sales']].sum()
print("Sales by region:")
for region, sales in total_by_region.items():
    pct = sales / vgsales['Global_Sales'].sum() * 100
    print(f"  {region}: {sales:.2f}M ({pct:.1f}%)")
# Top publishers
top_pubs = vgsales.groupby('Publisher')['Global_Sales'].sum().sort_values(ascending=False).head(3)
print("Top 3 publishers by global sales:")
for pub, sales in top_pubs.items():
    print(f"  {pub}: {sales:.2f} million")
# Genre distribution
print("Genre distribution:")
print(vgsales['Genre'].value_counts())

# 7. Plots
# Amazon — Boxplots of prices in USD (filtered)
palette_amazon = {'price_before_usd': '#4C72B0', 'price_after_usd': '#DD8452'}
fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
for ax, col in zip(axes, ['price_before_usd', 'price_after_usd']):
    series = amazon_filtered[col].dropna()
    sample = series.sample(frac=0.2, random_state=42)
    sns.boxplot(y=series, ax=ax, color=palette_amazon[col], showfliers=False)
    sns.stripplot(y=sample, ax=ax, color='black', size=5, alpha=0.6, jitter=0.25)
    ax.set_yscale('log')
    ax.yaxis.set_major_locator(LogLocator(base=10))
    ax.yaxis.set_major_formatter(LogFormatterMathtext())
    ax.set_title(col.replace('_', ' ').title())
    ax.set_ylabel('Price (USD, log scale)')
fig.suptitle('Amazon — Prices in USD (filtered)', fontsize=16)
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.show()

# Amazon — Discount Percentage Histogram
plt.figure(figsize=(6, 4))
amazon_filtered['discount_percentage'].dropna().hist(bins=25)
plt.title('Amazon — Discount Percentage Distribution')
plt.xlabel('Discount Percentage (%)')
plt.ylabel('Frequency')
plt.tight_layout()
plt.show()

# Amazon — Top 10 Categories by Avg Rating
avg_rating = (amazon_filtered.groupby('category')['rating']
              .mean().sort_values(ascending=False).head(10))
short_labels = [c.split('|')[-1] for c in avg_rating.index]
plt.figure(figsize=(8, 5))
ax = plt.gca()
ax.barh(short_labels, avg_rating)
ax.invert_yaxis()
plt.title('Amazon — Top 10 Categories by Avg Rating')
plt.xlabel('Average Rating')
plt.tight_layout()
plt.subplots_adjust(left=0.3)
plt.show()

# Amazon — Scatter: Price After Discount vs Rating
plt.figure(figsize=(6, 4))
plt.scatter(amazon_filtered['price_after_usd'], amazon_filtered['rating'], alpha=0.4)
plt.title('Amazon — Price After Discount vs Rating')
plt.xlabel('Price After Discount (USD)')
plt.ylabel('Rating')
plt.tight_layout()
plt.show()

# Google Play Store — Top 10 Categories by App Count
plt.figure(figsize=(8, 4))
google['Category'].value_counts().head(10).plot(kind='bar')
plt.title('Google Play — Top 10 Categories by App Count')
plt.xlabel('Category')
plt.ylabel('Number of Apps')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()

# Google Play Store — App Rating Distribution
plt.figure(figsize=(6, 4))
google['Rating'].dropna().hist(bins=20)
plt.title('Google Play — App Rating Distribution')
plt.xlabel('Rating')
plt.ylabel('Frequency')
plt.tight_layout()
plt.show()

# Google Play Store — Rating Boxplot for Top 5 Categories
top5 = google['Category'].value_counts().head(5).index
data_bp = [google[google['Category'] == c]['Rating'].dropna() for c in top5]
plt.figure(figsize=(8, 4))
plt.boxplot(data_bp, tick_labels=top5)
plt.title('Google Play — Rating Distribution (Top 5 Categories)')
plt.ylabel('Rating')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()

# Google Play Store — Installs vs Rating Scatter
plt.figure(figsize=(6, 4))
plt.scatter(google['Installs'], google['Rating'], alpha=0.5)
plt.xscale('log')
plt.title('Google Play — Installs vs Rating')
plt.xlabel('Installs (log scale)')
plt.ylabel('Rating')
plt.tight_layout()
plt.show()

# Video Game Sales — Total Global Sales by Year
plt.figure(figsize=(6, 4))
vgsales.groupby('Year')['Global_Sales'].sum().plot()
plt.title('VG Sales — Total Global Sales by Year')
plt.xlabel('Year')
plt.ylabel('Global Sales (million)')
plt.tight_layout()
plt.show()

# Video Game Sales — Top 10 Publishers by Global Sales
plt.figure(figsize=(8, 4))
vgsales.groupby('Publisher')['Global_Sales'].sum().sort_values(ascending=False).head(10).plot(kind='bar')
plt.title('VG Sales — Top 10 Publishers by Global Sales')
plt.xlabel('Publisher')
plt.ylabel('Global Sales (million)')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()

# Video Game Sales — Genre Distribution Pie Chart
plt.figure(figsize=(6, 6))
vgsales['Genre'].value_counts().plot(kind='pie', autopct='%1.1f%%', startangle=140)
plt.title('VG Sales — Genre Distribution')
plt.ylabel('')
plt.tight_layout()
plt.show()

# Video Game Sales — Top 10 Games by Global Sales
plt.figure(figsize=(8, 4))
top10_games = vgsales.groupby('Name')['Global_Sales'].sum().sort_values(ascending=False).head(10)
top10_games.plot(kind='bar')
plt.title('VG Sales — Top 10 Games by Global Sales')
plt.xlabel('Game Name')
plt.ylabel('Global Sales (million)')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()

# Google Play Store Reviews — Sentiment Polarity vs Review Length
reviews = data["reviews"]
# Compute review length and average sentiment polarity
reviews["Length"] = reviews["Translated_Review"].astype(str).str.len()
grouped_reviews = reviews.groupby("Length")["Sentiment_Polarity"].mean()

# Plot: Sentiment Polarity vs Review Length
plt.figure(figsize=(8, 5))
plt.scatter(grouped_reviews.index, grouped_reviews.values, alpha=0.5)
plt.title("Google Play Store Reviews — Sentiment Polarity vs Review Length")
plt.xlabel("Review Length")
plt.ylabel("Sentiment Polarity")
plt.tight_layout()
plt.show()
