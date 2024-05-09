# INCIDENT ANALYZER 
## Project Name: HPE GreenLake Private Cloud Enterprise Incident Analytics Platform

### Project Overview:
HPE GreenLake Private Cloud Enterprise comprises numerous microservices, all utilizing PagerDuty for incident management. It's imperative to analyze incident data to glean insights into service stability and event patterns. The objective of this project is to develop a comprehensive platform and dashboard that provides meaningful event analytics for all PCE services.

### Categories of Work:
1. **Curation of Data:**
   - Identifying and **filtering out noise** from the dataset to enhance the relevance of subsequent analysis.
     
2. **Visualization of Incidents:**
   - **Heatmap** of Incidents Count per Service.
   - **Line graph** of No. of incidents triggered v/s Time.

3. **Statistical Analysis:**
   - Initial **Categorization** of incidents **using LLM**.
   - **Visualization of most likely incidents occurred** as well as the overall split of incidents using Pie Charts.
   
4. **Correlations and Connections between the occurance of incidents:**
   - **Transition Probability** : Analyzing probabilities of incident occurrences being followed by incidents of different types (P(i|j)).
   - Implementing a **Sankey Diagram** for showcasing these relationships effectively.

5. **Live Dashboards:**
   - Developing dynamic dashboards showcasing incident data in real-time using DASH.

### Getting Started:
To set up the project locally, follow these steps:
1. Clone the repository to your local machine.
2. Install the required dependencies listed in `requirements.txt`.
3. Obtain necessary access credentials/API keys from PagerDuty and OpenAI.
4. Configure the project settings and API connections.
5. Run the relevant scripts for data processing, analysis, and visualization.

### Contributors:
- Nitin : https://github.com/NitinReddy-dev/
- Chetana : https://github.com/Chetana2403/
- Ayush : https://github.com/BeerLambert
- Deeksha : https://github.com/Deeksha-Dattaraj-Ganapumane
- Anoushka : https://github.com/s-anoushka
