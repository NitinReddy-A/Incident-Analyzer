import pandas as pd

# Read the CSV file into a DataFrame
df = pd.read_csv('formatedData.csv', usecols=[0, 1])

# Define a function to format each row
def format_text(row):
    return f"###Human:\nCategorize the incident: {row['Incident Description']}\n\n###Assistant:\n{row['Category']}"

# Apply the formatting function to each row and create a new column 'text'
df['text'] = df.apply(format_text, axis=1)

# Write the updated DataFrame to a new CSV file
df.to_csv('train.csv', index=False)
