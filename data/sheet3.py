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


	potm			vikram			perfect			baseline			victima			tempo		
	mix_ipc	alone_ipc	ratio	mix_ipc	alone_ipc	ratio	mix_ipc	alone_ipc	ratio	mix_ipc	alone_ipc	ratio	mix_ipc	alone_ipc	ratio	mix_ipc	alone_ipc	ratio
cc	0.04267659998			0.05567156079			0.06917185717			0.04818511835			0.03493881291			0.04798766611		
dlrm	0.05706951845			0.08028512951			0.1017719521			0.06600814366			0.04819675055			0.06599702119		
gc	0.0414365525			0.05421858667			0.07656722329			0.04672805181			0.03431415705			0.04694210397		
rnd	0.09204780423			0.1987507841			0.2885401016			0.1160313273			0.07586144499			0.1159126487		
bfs	0.05706951845			0.08028507175			0.1017719418			0.06600826603			0.04819675757			0.06599710931		
sssp	0.050790388			0.06425911759			0.09196795781			0.05709126676			0.04149408941			0.05704863196		
gen	0.04143648982			0.05421858667			0.07656690743			0.04672805181			0.03431413686			0.04694227286		
pr	0.1578616529			0.1724076588			0.2192500429			0.1651183271			0.1215113452			0.1651510138		

	baseline	perfect_tlb	perfect_pwc	potm	victima	vikram	utopia	victima	tempo
dlrm	0.05540131853	0.06465429802	0.06159520994	0.05638350401	0.0585881629	0.0594111507	0.06100591601	0.05657684219	0.05548375354
pr	0.07447661338	0.08372184242	0.08025098087	0.07430508661	0.07785988575	0.07816124883	0.07903873985	0.07016209438	0.07456501295
cc	0.06030228016	0.07054034644	0.06767682253	0.06136113287	0.06337596125	0.06538383483	0.0664653679	0.0604219926	0.06022604629
sssp	0.08151727666	0.1077083319	0.1014619763	0.08557897051	0.08564864014	0.08411821363	0.09727449525	0.07472478767	0.08147648838
gc	0.06329447278	0.08242313418	0.07793240425	0.06493313271	0.06474144365	0.06726341743	0.07673581233	0.0612941556	0.06331380262
tc	0.2585055533	0.3000208334	0.2882089107	0.2658778726	0.2657677504	0.2824012099	0.2852527179	0.2501854314	0.2585114955
xs	0.4394526117	0.6497678782	0.5828767189	0.4805682148	0.528327132	0.4835881444	0.5976790026	0.498436821	0.4387908493
rnd	0.3018224942	0.9368123472	0.8445816973	0.5085996274	0.6084667572	0.7138735843	0.8698069574	0.3616419382	0.3020473392
bfs	0.05563520539	0.06465429585	0.06159542301	0.05640083912	0.05865671593	0.05942067631	0.06100640177	0.05659335707	0.05548295955
bc	0.2906138153	0.4773771621	0.4374318026	0.3043051033	0.3014259067	0.3156569466	0.4043802093	0.2419152418	0.2905560316
gen	0.06332924831	0.08242272793	0.07793212949	0.06492793694	0.06473890457	0.06731872949	0.07673964609	0.06130054072	0.06335732128