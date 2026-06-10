import subprocess
import sys

SCRIPT_PATH = "../scripts/plot_koppen_map.py"

for step in [1,2,3,4,5,10,20,30]:
    for year in range(1983, 2024):
        year_str = str(year)
        output_file = f"y{step}_{year_str}.png"
        csv = f"data{step}.csv"
        # Construct the command as a list of strings (preferred for security and robustness)
        command = [
            sys.executable,  # Use the current Python interpreter
            SCRIPT_PATH,
            "--csv", csv,
            "--year", year_str,
            "--out", output_file
        ]

        # Log the command being executed
        print(f"\n[INFO] Running command for year {year} step {step}:")
        print(f"[CMD] {' '.join(command)}")

        try:
            # Execute the command.
            # check=True raises an exception if the called script returns a non-zero exit code.
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print(f"[SUCCESS] Successfully generated {output_file}")

        except subprocess.CalledProcessError as e:
            # Handle errors from the external script
            print(f"[ERROR] Script failed for year {year}.")
            print(f"--- STDOUT ---\n{e.stdout}")
            print(f"--- STDERR ---\n{e.stderr}")

        except FileNotFoundError:
            # Handle case where the 'python' executable or the script file is not found
            print(f"[CRITICAL ERROR] The external script '{SCRIPT_PATH}' or 'python' executable could not be found.")
            print("Please ensure the script path is correct and Python is in your system PATH.")
            break # Stop the process if a critical error occurs

    print("\n--- Plot Generation Complete ---")

