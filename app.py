import os
import pandas as pd
import time 

from apikey import apikey

from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

os.environ['OPENAI_API_KEY'] = apikey

# Load incidents data from CSV
incidents_df = pd.read_csv('data/filtered_incidents.csv')

# Prompt templates
prompt = PromptTemplate(
    input_variables=['incident_desc'],
    template=''' As a seasoned data analyst, you play a crucial role within an incident response team operating within a private cloud enterprise. Your primary responsibility revolves around meticulously categorizing and classifying incoming incidents based on their descriptions. These incidents may pertain to various aspects of the system, such as security vulnerabilities, server capacity issues, or performance bottlenecks.
        A few examples of categories are Security Breach,Disk Capacity Issue, Performance Degradation, Network Connectivity Problem, Software Bug, Hardware Failure, Authentication/Access Issue, Data Corruption, Configuration Error, Service Outage, etc.
        Try to categorize the incidents accordingly if it matches the above categories, if not feel free to create a new category appropriately.
        To streamline the process, you categorize incidents according to the specific service, system component, or architectural element they impact. For instance, a security-related incident might involve unauthorized access attempts or data breaches, while a server capacity issue could manifest as resource exhaustion or hardware failures. Similarly, performance-related incidents may relate to slow load times or service disruptions.

        This is an example scenario:

        This will be the format of the input:
        Incident Description: "Users are experiencing intermittent login failures, resulting in denied access to the application."

        Your Output should be:
        Authentication/Access Issue

        Remember, precision and accuracy are paramount in your role. Make sure you only respond with the category name nothing more or less. 

        Hence I am providing you with the incident description, kindly categorize it accordingly: {incident_desc}'''
)

# Llms
llm = OpenAI(temperature=0.9)
chain = LLMChain(llm=llm, prompt=prompt, verbose=True)

# Function to categorize incidents
def categorize_incident(incident_desc):
    response = chain.run(incident_desc=incident_desc)
    return response.strip()

# Apply categorization to each incident
batch_size = 3  # Number of incidents to categorize in each batch
total_incidents = len(incidents_df)
for i in range(0, total_incidents, batch_size):
    batch = incidents_df.iloc[i:i + batch_size]
    for index, row in batch.iterrows():
        category = categorize_incident(row['details'])
        incidents_df.at[index, 'category'] = category
    incidents_df.to_csv('data/categorized_incidents.csv', index=False)  # Save categorized incidents to a new CSV file
    print(f"Categorized {min(i + batch_size, total_incidents)} incidents. Waiting for 20 seconds before next batch...")
    time.sleep(20)  # Introduce a 20-second delay before processing the next batch

print("All incidents categorized and saved successfully.") # Was able to only categorize 100 incidents.
