from openai import AzureOpenAI

client = AzureOpenAI(
  azure_endpoint = "https://ai-xm-openai-msdn-cus.openai.azure.com/openai/deployments/elastic-nlp/chat/completions?api-version=2023-03-15-preview", 
  api_key="",  
  api_version="2023-03-15-preview"
)

from elasticsearch import Elasticsearch

# Elasticsearch user and password
ELASTIC_USER = "" 
ELASTIC_PASSWORD = "" 

# Found in the 'Manage Deployment' page
CLOUD_ID = "els-xm-exchange-elastic-nlp-cus:Y2VudHJhbHVzLmF6dXJlLmVsYXN0aWMtY2xvdWQuY29tJGY5MjU3ZTIwY2I1NzQwMGU5ZTVlMmZhNTBiNGE3NDBkJGNlODQwODI5M2ZiZjQ0MGE5NDUyNGJlODg3ZThmZGU1"


# Create the client instance
esclient = Elasticsearch(
    cloud_id=CLOUD_ID,
    basic_auth=(ELASTIC_USER, ELASTIC_PASSWORD)
)

def translateQuery(openAPI, esclient, index, query):
    SYSTEM_PROMPT = "You are a elasticsearch analyst. Pay close attention to data definition. Do not include filters not requested in the query"
    #BASE_PROMPT_CHATGPT = "Given the mapping delimited by triple backticks ```{}``` translate the text delimited by triple quotes in a valid Elasticsearch DSL query \"\"\"{}\"\"\". The following in the data definition. CustomField14 - FinancingAvailable, customField2 - OccupancyStatus (VACANT, OCCUPIED), customFieldChar255_21 - Reduced reserve. Give me only the json code part of the answer. Compress the json output removing spaces."
    BASE_PROMPT_CHATGPT = """Given the mapping delimited by triple backticks ```{}``` 
                        translate the text delimited by triple quotes in 
                        a valid Elasticsearch DSL query \"\"\"{}\"\"\". 
                        The following in the data definition: 
                        customField2 - Occupancy Status ('VACANT', 'OCCUPIED'). 
                        Include customeField in query only if Vacant or Occupied property is requested
                        customFieldChar255_21 - Reduced reserve ('true', 'false').
                        customField23 - Reserve price change date.
                        customField14 - Financing Available (true, false)
                        Recent means last 2 month.
                        Ignore auctionPropertyFlg.
                        Don't use .keyword of the field is not multi field.
                        Give me only the json code part of the answer. 
                        Compress the json output removing spaces."""
    
    # query = "Houses where I can make a pre-auction offer and vacant"
    # Get mapping of the index
    mapping = esclient.indices.get_mapping(index=index)

    prompt = BASE_PROMPT_CHATGPT.format(mapping,query)
    print("Prompt for the LLM:")
    print(prompt)

    response = client.chat.completions.create(
        model="gpt-4o", # replace with the model deployment name of your o1-preview, or o1-mini model
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )
    res = response.choices[0].message.content.strip()
    esquery = res.replace("```json", "").replace("```", "")
    print("Elastic Query:")
    print(esquery)
    return esquery 

def runESQuery (index, esquery):
    import elasticsearch
    import json
    json_query = json.loads(esquery)
    esquery = json_query.get("query")
    #print(esquery)
    try:
        results = esclient.search(index=index, query=esquery)
    except elasticsearch.ElasticsearchException as es1:
        print("Error in Elastic Query")
    return results


if __name__ == '__main__':
    userQuery = input("Enter your natural language search query: ")
    esquery = translateQuery(client, esclient, "listings_active2", userQuery)
    results = runESQuery("listings_active2", esquery)
    print("Below is the result of executing Elastic Query:")
    print(results.body)