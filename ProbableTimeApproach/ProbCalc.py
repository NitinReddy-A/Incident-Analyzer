import pandas as pd

# Load categorized incidents data
categorized_incidents_df = pd.read_csv('data/categorized_incidents.csv')

# Convert 'created_at' column to datetime
categorized_incidents_df['created_at'] = pd.to_datetime(categorized_incidents_df['created_at'])

# Initialize dictionaries to store time differences, counts, and probabilities
time_differences = {}
time_counts = {}
transition_counts = {}
transition_probabilities = {}

# Iterate over rows to calculate time differences and count transitions
for i in range(len(categorized_incidents_df) - 1):
    current_category = categorized_incidents_df.at[i, 'category']
    next_category = categorized_incidents_df.at[i+1, 'category']
    current_service = categorized_incidents_df.at[i, 'service']
    next_service = categorized_incidents_df.at[i+1, 'service']
    
    # Check if the incidents occur within the same service
    if current_service == next_service:
        # Calculate time difference between consecutive incidents
        time_diff = (categorized_incidents_df.at[i+1, 'created_at'] - categorized_incidents_df.at[i, 'created_at']).total_seconds()
        
        # Increment time difference and count for the current category to next category and service
        time_differences[(current_category, current_service, next_category)] = time_differences.get((current_category, current_service, next_category), 0) + time_diff
        time_counts[(current_category, current_service, next_category)] = time_counts.get((current_category, current_service, next_category), 0) + 1
        
        # Increment transition count for the current category to next category and service
        transition_counts[(current_category, current_service, next_category)] = transition_counts.get((current_category, current_service, next_category), 0) + 1

# Calculate transition probabilities
total_transitions = sum(transition_counts.values())
for transition, count in transition_counts.items():
    transition_probabilities[transition] = count / total_transitions

# Calculate average time differences (probable times)
probable_times = {transition: time_differences[transition] / time_counts[transition] for transition in time_differences}

# Convert probable times and transition probabilities to DataFrame
probable_times_df = pd.DataFrame.from_dict(probable_times, orient='index', columns=['Average Time (seconds)'])
transition_probabilities_df = pd.DataFrame.from_dict(transition_probabilities, orient='index', columns=['Probability'])

# Merge the two DataFrames
result_df = probable_times_df.join(transition_probabilities_df)

# Reset index and rename columns for clarity
result_df = result_df.reset_index().rename(columns={'index': 'Transition'})

# Separate incident name and service name into separate columns
result_df[['Incident Name (From)', 'Service Name', 'Incident Name (To)']] = pd.DataFrame(result_df['Transition'].tolist(), index=result_df.index)

# Drop the original 'Transition' column
result_df.drop(columns=['Transition'], inplace=True)

# Save the result to CSV file
result_df.to_csv('data/probable_times_and_probabilities_within_service.csv', index=False)

print("Probable times and transition probabilities within the same service saved to probable_times_and_probabilities_within_service.csv")
