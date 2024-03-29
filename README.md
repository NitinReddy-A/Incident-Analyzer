# INCIDENT ANALYZER 
## Project Name: HPE GreenLake Private Cloud Enterprise Incident Analytics Platform

### Project Overview:
HPE GreenLake Private Cloud Enterprise comprises numerous microservices, all utilizing PagerDuty for incident management. It's imperative to analyze incident data to glean insights into service stability and event patterns. The objective of this project is to develop a comprehensive platform and dashboard that provides meaningful event analytics for all PCE services.

### Categories of Work:
1. **Visualization of Incidents:**
   - Graphs over time on a per-system, per-topic, per-team, per-* basis.
   - Heat map visualization of topics, systems, nodes, VMs, services, etc.

2. **Statistical Analysis:**
   - Determining the most likely events to occur, categorized by system, customer, team, service, etc.
   
3. **Correlations and Connections:**
   - Analyzing probabilities of incident occurrences being followed by incidents of different types (P(i|j)).
   - Exploring visualization techniques for showcasing these relationships effectively.

4. **Replay of Events:**
   - Visualization of a day or specific event illustrating how incidents unfold.
   - Utilizing service map data to depict the sequence of failures across PCE systems.

5. **Curated Data:**
   - Identifying and filtering out noise from the dataset to enhance the relevance of subsequent analysis.

6. **Live Dashboards:**
   - Developing dynamic dashboards showcasing incident data in real-time as it arrives.

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
- Anoushka : 
- Deeksha :


### Project Progress:
1. **Visualization of Incidents:**
  - Heatmap of Incidents Count per Service.
  - Line graph of No. of incidents triggered v/s Time.
2. **Statistical Analysis:**
  - Initial Categorization of incidents using LLM.
