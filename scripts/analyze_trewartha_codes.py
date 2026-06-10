"""Simple script to analyze Trewartha climate classification codes in the CSV data.

Shows all unique codes with their frequencies to help design color palettes.
"""
import pandas as pd
import argparse
from collections import Counter

def main():
    parser = argparse.ArgumentParser(description='Analyze Trewartha codes in climate data')
    parser.add_argument('--csv', default='/tmp/climate_classifications.csv', 
                       help='Path to CSV file (default: /tmp/climate_classifications.csv)')
    parser.add_argument('--year-start', type=int, help='Filter by start year (optional)')
    parser.add_argument('--year-end', type=int, help='Filter by end year (optional)')
    args = parser.parse_args()
    
    print(f"Reading data from: {args.csv}")
    
    # Read the CSV file
    df = pd.read_csv(args.csv, usecols=['year', 'trewartha'])
    
    print(f"Total rows in dataset: {len(df)}")
    
    # Filter by year range if specified
    if args.year_start or args.year_end:
        if args.year_start:
            df = df[df['year'] >= args.year_start]
        if args.year_end:
            df = df[df['year'] <= args.year_end]
        print(f"Rows after year filtering: {len(df)}")
    
    # Get all Trewartha codes and their frequencies
    trewartha_counts = df['trewartha'].value_counts()
    
    print(f"\nFound {len(trewartha_counts)} unique Trewartha codes:")
    print("=" * 50)
    
    for code, count in trewartha_counts.items():
        percentage = (count / len(df)) * 100
        print(f"{code:8s} : {count:8d} ({percentage:5.1f}%)")
    
    print("=" * 50)
    print(f"Total data points: {trewartha_counts.sum()}")
    
    # Show first letters (main climate groups)
    print(f"\nMain climate groups (first letter):")
    print("-" * 30)
    first_letters = df['trewartha'].astype(str).str[0].value_counts()
    for letter, count in first_letters.items():
        percentage = (count / len(df)) * 100
        print(f"{letter:2s} : {count:8d} ({percentage:5.1f}%)")

if __name__ == '__main__':
    main()
