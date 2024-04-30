import pandas as pd

# Load categorized incidents data
categorized_incidents_df = pd.read_csv('data/categorized_incidents.csv')

# Initialize dictionaries to store transition counts and probabilities
transition_counts = {}
transition_probabilities = {}

# Iterate over rows to count transitions
for i in range(len(categorized_incidents_df) - 1):
    current_category = categorized_incidents_df.at[i, 'category']
    next_category = categorized_incidents_df.at[i+1, 'category']
    current_service = categorized_incidents_df.at[i, 'service']
    next_service = categorized_incidents_df.at[i+1, 'service']
    
    # Check if the incidents occur within the same service
    if current_service == next_service:
        # Increment transition count for the current category to next category and service
        transition_counts[(current_category, current_service, next_category)] = transition_counts.get((current_category, current_service, next_category), 0) + 1

# Calculate transition probabilities
total_transitions = sum(transition_counts.values())
for transition, count in transition_counts.items():
    transition_probabilities[transition] = count / total_transitions

# Convert transition probabilities to DataFrame
transition_df = pd.DataFrame.from_dict(transition_probabilities, orient='index', columns=['Probability'])

# Reset index and rename columns for clarity
transition_df = transition_df.reset_index().rename(columns={'index': 'Transition'})

# Separate incident name and service name into separate columns
transition_df[['Incident Name (From)', 'Service Name', 'Incident Name (To)']] = pd.DataFrame(transition_df['Transition'].tolist(), index=transition_df.index)

# Drop the original 'Transition' column
transition_df.drop(columns=['Transition'], inplace=True)

# Save transition probabilities to CSV file
transition_df.to_csv('data/transition_probabilities_within_service.csv', index=False)

print("Transition probabilities within the same service saved to transition_probabilities_within_service.csv")
