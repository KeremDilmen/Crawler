import json
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import pairwise_distances
import numpy as np
from sklearn.cluster import KMeans
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import time

# Load the data
with open('all_company_details.json', 'r') as f:
    companies = json.load(f)

# Extract descriptions and themes with scores
descriptions, themes = [], []
for company in companies:
    descriptions.append(company['description'])
    theme_scores = {theme[0]: int(theme[1]) for theme in company['startup_themes']}
    themes.append(theme_scores)

model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

# Embed the company descriptions
description_embeddings = model.encode(descriptions)

# Calculate the cosine similarity matrix for text
text_similarity_matrix = cosine_similarity(description_embeddings)

# Prepare the theme data for similarity calculation
unique_themes = list(set(theme for company in themes for theme in company))
theme_vectors = np.zeros((len(companies), len(unique_themes)))

for i, company in enumerate(themes):
    for theme, score in company.items():
        theme_vectors[i][unique_themes.index(theme)] = score

# Calculate weighted Jaccard similarity matrix for themes
def weighted_jaccard(v1, v2):
    min_sum = np.sum(np.minimum(v1, v2))
    max_sum = np.sum(np.maximum(v1, v2))
    return min_sum / max_sum if max_sum != 0 else 0

theme_similarity_matrix = pairwise_distances(theme_vectors, metric=weighted_jaccard)

# Define weights for the combined metric
alpha = 0.3  # weight for text similarity
beta = 0.7   # weight for theme similarity

# Calculate the combined closeness matrix
combined_similarity_matrix = alpha * (1 - text_similarity_matrix) + beta * (1 - theme_similarity_matrix)

# Perform K-Means clustering
num_clusters = 10  # You can choose an appropriate number of clusters
kmeans = KMeans(n_clusters=num_clusters, random_state=0)
labels = kmeans.fit_predict(combined_similarity_matrix)

# Group companies by cluster labels
clusters = {i: [] for i in range(num_clusters)}
for i, label in enumerate(labels):
    clusters[label].append(companies[i])

with open('clusters.json', 'w') as f:
    json.dump(clusters, f, indent=4)

print("Clusters have been saved to clusters.json")

gemini_key = "AIzaSyCRFzQ9xhzII7QMEVqeQcfIp_Upx6hHYEo"
genai.configure(api_key=gemini_key)

# Function to generate title and description for the cluster using the Google Gemini API
def generate_title_and_description(cluster):
    company_names = [company['name'] for company in cluster]
    descriptions = [company['description'] for company in cluster]
    themes = [theme for company in cluster for theme in company['startup_themes']]
    
    # Create the prompt for the LLM to generate a specific title
    title_prompt = (
        f"Based on the following companies and their descriptions, generate a specific and descriptive title "
        f"that captures the unique theme and focus of this cluster.\n"
        f"Companies: {', '.join(company_names)}\n"
        f"Descriptions: {', '.join(descriptions)}\n"
        f"Themes: {themes}\nTitle:"
    )
    
    # Initialize the Gemini model
    model = genai.GenerativeModel('gemini-pro')
    
    # Retry logic with exponential backoff
    def generate_with_retry(prompt):
        retries = 0
        max_retries = 5
        while retries < max_retries:
            try:
                response = model.generate_content(prompt)
                return response.text.strip() if hasattr(response, 'text') else None
            except ResourceExhausted:
                retries += 1
                wait_time = 2 ** retries 
                print(f"Rate limit exceeded, retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        return None
    
    # Generate title using the model
    title = generate_with_retry(title_prompt)
    
    # Create the prompt for the LLM to generate an overall description
    description_prompt = (
        f"Based on the following companies and their descriptions, generate a concise and informative "
        f"1-2 sentence description that summarizes the common themes, focus areas, and unique aspects of this cluster as a whole.\n"
        f"Companies: {', '.join(company_names)}\n"
        f"Descriptions: {', '.join(descriptions)}\n"
        f"Themes: {themes}\nDescription:"
    )
    
    # Generate description using the model
    description = generate_with_retry(description_prompt)
    
    return title, description


# Summarize each cluster
cluster_summaries = {}
request_count = 0
start_time = time.time()
    
for label, cluster in clusters.items():
    if request_count >= 60:
        elapsed_time = time.time() - start_time
        if elapsed_time < 60:
            time.sleep(60 - elapsed_time)
        start_time = time.time()
        request_count = 0
        
    title, description = generate_title_and_description(cluster)
    cluster_summaries[label] = {'title': title, 'description': description, 'companies': cluster}
        
    request_count += 2
    
# Save the cluster summaries to a JSON file
with open('cluster_summaries.json', 'w') as f:
    json.dump(cluster_summaries, f, indent=4)
    
print("Cluster summaries have been saved to cluster_summaries.json")
