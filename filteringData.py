import csv

# Specify the input and output file paths
input_file = 'data/incidents_data.csv'
output_file = 'data/filtered_incidents.csv'

# Open the input CSV file
with open(input_file, 'r', newline='') as f_input:
    # Create CSV reader object
    csv_reader = csv.reader(f_input)
    
    # Read the header
    header = next(csv_reader)
    
    # Find the index of the column containing the set
    set_column_index = header.index("details") 
    
    # Filter out rows with an empty set in the specified column
    filtered_rows = [row for row in csv_reader if row[set_column_index] != "{}"]

# Write the filtered rows to the output CSV file
with open(output_file, 'w', newline='') as f_output:
    # Create CSV writer object
    csv_writer = csv.writer(f_output)
    
    # Write the header to the output file
    csv_writer.writerow(header)
    
    # Write the filtered rows to the output file
    csv_writer.writerows(filtered_rows)
