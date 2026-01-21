import pandas as pd
import numpy as np
import sys
import os

BUCKET_MID_DICT = {
    "0..1": 0.5, "2..3": 2.5, "4..7": 5.5, "8..15": 11.5, "16..31": 23.5,
    "32..63": 47.5, "64..127": 95.5, "128..255": 191.5, "256..511": 383.5,
    "512..1023": 767.5, "1024..2047": 1535.5
}

bucket_columns = list(BUCKET_MID_DICT.keys())
bucket_values = list(BUCKET_MID_DICT.values())

def process_and_add_percentiles(input_file: str, output_file: str):
    # Determine the separator (space, tab, or comma)
    # The provided data looks like fixed-width or space-separated data
    try:
        # Use sep='\s+' to handle variable whitespace/tabs
        df = pd.read_csv(input_file, sep=',', engine='python', header=0)
    except Exception as e:
        print(f"Could not read file with space separator, attempting comma separation. Error: {e}")
        try:
            df = pd.read_csv(input_file, sep=',', engine='python')
        except Exception as e_csv:
            print(f"Could not read file with comma separator either. Error: {e_csv}")
            return

    # --- Data Cleaning ---
    # The read_csv might have created unintended blank columns if your data file had trailing commas/spaces.
    # Drop any fully unnamed/empty columns.
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    # Ensure the target columns exist
    if not all(col in df.columns for col in bucket_columns):
        print(f"Error: Missing expected bucket columns in the file: {bucket_columns}")
        return

    # --- Type Conversion ---
    # Convert all relevant columns to numeric first, handling blank/non-numeric cells as NaN
    for col in bucket_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    # Also convert 'Total' column if it exists and needs calculation
    if 'Total' in df.columns:
         df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)

    # --- The Multiplication Step (Corrected and implemented reliably) ---
    multiplier_array = np.array(bucket_values)
    
    # Select the columns by name, multiply by the 1D numpy array (broadcasting happens automatically)
    # df[bucket_columns] = df[bucket_columns] * multiplier_array


    # --- Further Processing ---
    # We redefine the numeric part of the DF now that it is clean and multiplied
    df_numeric = df[bucket_columns]

    # 3. Calculate the cumulative sum along the columns (axis=1)
    df_cumsum = df_numeric.cumsum(axis=1)
    
    # Assign the cumulative results back to the original DataFrame structure, overwriting bucket values
    df[bucket_columns] = df_cumsum


    # Calculate percentiles across rows (axis=1) for the numeric data columns
    df['50th_Percentile_Row'] = df_cumsum.quantile(0.5, axis=1)
    df['95th_Percentile_Row'] = df_cumsum.quantile(0.95, axis=1)
    df['99th_Percentile_Row'] = df_cumsum.quantile(0.99, axis=1)

    # Calculate total cumulative sum for each row
    df['Total_Cumulative_Sum_Row'] = df_cumsum.iloc[:, -1] # The last column of the cumulative sum is the total sum


    # Save the results to a new CSV file
    df.to_csv(output_file, index=False)
    
    print(f"\nSuccessfully processed data and saved to {output_file}")
    print("\nSample of the output (first 5 rows):")
    print(df.head())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_data.py <input_file_path>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = "./output_percentiles.csv"
    
    process_and_add_percentiles(input_file, output_file)
