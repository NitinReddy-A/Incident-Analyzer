# Read the CSV file
input_file = 'InitaialData.csv'
output_file = 'formatedData.csv'

with open(input_file, 'r', encoding='utf-8') as infile:
    lines = infile.readlines()

# Process lines to add quotes and handle periods
processed_lines = []
for line in lines:
    if line.strip().startswith('"'):  # Check if the line already starts with double quotes
        line = line.strip()  # Strip extra whitespace
        line = line.replace('.,', '.",')  # Add quotes before periods
    else:
        line = '"' + line.strip()  # Add double quotes at the beginning
        line = line.replace('.,', '.",')  # Add quotes before periods
    processed_lines.append(line)

# Write processed lines to output file
with open(output_file, 'w', encoding='utf-8') as outfile:
    for line in processed_lines:
        outfile.write(line + '\n')
