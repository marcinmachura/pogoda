#!/bin/bash
# Example usage script for frost detection analysis

echo "Frost Detection Analysis Pipeline"
echo "================================="

# Step 1: Extract Poland temperature data (if not already done)
echo "Step 1: Extracting Poland temperature data..."
#python extract-poland-pq.py --tn_file tn_ens_mean_0.1deg_reg_v31.0e.nc --start_year 1980 --end_year 2023 --output poland_min_temp_1980_2023.parquet

# Step 2: Detect frost patterns and create visualizations
echo "Step 2: Analyzing frost patterns..."
python detect_frost.py --data_file poland-daily-mean001.parquet --output_dir frost_analysis_1980_2023 --period_years 3 --gif_duration 1.5

echo "Analysis complete! Check the frost_analysis_1980_2023 directory for results."