import os
import sqlite3
import openai
import numpy as np
import json
import faiss
import re
from configparser import ConfigParser

# load config
file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.ini")
cf = ConfigParser()
cf.read(file_path, encoding='utf-8')
openai.api_base = cf.get('openai', 'api_base')
openai.api_key = cf.get('openai', 'api_key')

def cosine_similarity(vec_a, vec_b):
    return np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))

def retrieve(query_embedding, embeddings, docs, threshold=0.8):
    embeddings_np = np.array(embeddings).astype('float32')

    index = faiss.IndexFlatL2(embeddings_np.shape[1])
    index.add(embeddings_np)

    D, I = index.search(np.array([query_embedding]).astype('float32'), 1)
    best_match_index = I[0][0]
    best_match_score = D[0][0]

    cos_sim = cosine_similarity(query_embedding, embeddings[best_match_index])

    print(cos_sim)
    if cos_sim < threshold:
        return None

    return docs[best_match_index]


def processJSON(result):
    pattern = re.compile(r'([^,]*?): ([^\n]*?)(, |\n|$)')
    matches = re.findall(pattern, result)
    result_dict = {}
    for match in matches:
        key, value, _ = match
        key = key.strip()
        if key == "Interface Parameters":
            value = value.strip("[]").split(", ")
        elif value == "true":
            value = True
        elif value == "false":
            value = False
        result_dict[key] = value
    return result_dict

DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools.db')

def find_best_match(description):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM tool')
    rows = cursor.fetchall()
    docs = ["Interface ID: " + str(row[0]) + ", Interface Name: " + str(row[1]) + ", Interface Address: " + str(row[2]) + ", Interface Description: " + str(row[3]) + ", Interface Parameters: " + str(row[4]) + ", Status: " + str(row[5]) for row in rows if row[5] == 'true']

    embeddings = []
    for doc in docs:
        response = openai.Embedding.create(input=doc, engine="text-embedding-ada-002")
        embeddings.append(response['data'][0]['embedding'])

    query = "Question: "+description + \
            "Based on the known issues and API details, can you choose the right API to solve the given problem?"+\
            ""
    query_response = openai.Embedding.create(input=query, engine="text-embedding-ada-002")
    query_embedding = query_response['data'][0]['embedding']

    result = retrieve(query_embedding, embeddings, docs)

    if result:
        result_dict = processJSON(result)
        result_dict["Matched"] = True
    else:
        result_dict={"Matched": False}

    json_result = json.dumps(result_dict, indent=4)

    return json_result

def fill_parameters(description, result, params):
    prompt ="Problem description: "+ description + \
            "About the selected API information:" + str(result)+ \
            "Parameters:"+ str(params) +\
            "Parameter structure: [{type, name, description, value}]"+\
            "This structure is a list containing multiple dictionaries, each representing a parameter. Each parameter dictionary has four key-value pairs: type, name, description, and value."+\
            "Wherein, type represents the parameter type, possible values include 'profile', 'tool' (indicating that this is a provided parameter), and 'fix' (indicating that this is a fixed parameter extracted from the problem description); name represents the parameter name, used to identify the parameter; description represents the parameter description, used to explain the meaning or use of the parameter; value represents the parameter value, that is, the actual content of the parameter."+\
            "Please fill in the parameters of the selected API according to the given parameters and problem description, that is, fill in the values of each parameter in the Interface Parameters of the selected API. If the parameter can be found in the given parameter list, its type remains unchanged, the name needs to be changed to the corresponding name in the API interface parameters, and the description and value remain unchanged. If the parameter cannot be found in the parameter list but can be extracted from the problem description, the type of this parameter is 'fix', the name is the corresponding name in the API interface parameters, the description can be filled in according to your understanding, and the value is the information extracted from the problem description."+\
            "Here is an example:"+\
            "Assume the problem description is: Find restaurants with a rating above 4.5 in New York and sort them by price. The selected API information is:"+\
            "{'Interface ID': '2', 'Interface Name': 'RestaurantFinder', 'Interface Address': 'http://127.0.0.1:5008', "+\
            " 'Interface Description': 'RestaurantFinder is a tool for querying and analysing restaurant information. Users can enter their target city, a minimum rating, and a sorting method"+\
            " 'Interface Parameters': ['target_city,minimum_rating,sort_method'],'Status': true, 'Matched': true},"+\
            " The provided parameters are: [{'type': 'profile', 'name': 'city', 'description': 'target city', 'value': 'New York'}, {'type': 'tool', 'name': 'sort', 'description': 'sort method', 'value': 'price'}]."+\
            "In this example, we need to fill in three API parameters, 'target_city', 'minimum_rating', and 'sort_method'. First, we can find the parameter corresponding to 'target_city' in the provided parameter list, so we keep its type as 'profile', change the name to 'target_city', and keep the description and value unchanged, resulting in the parameter {'type': 'profile', 'name': 'target_city', 'description': 'target city', 'value': 'New York'}; then, we extract the value of 'minimum_rating' from the problem description as 4.5, so we set its type to 'fix', name to 'minimum_rating', description can be filled in according to your understanding, and the value is 4.5 extracted from the problem description, resulting in the parameter {'type': 'fix', 'name': 'minimum_rating', 'description': 'minimum rating', 'value': '4.5'}; finally, we find the parameter corresponding to 'sort_method' in the provided parameter list, so we keep its type as 'tool', change the name to 'sort_method', and keep the description and value unchanged, resulting in the parameter {'type': 'tool', 'name': 'sort_method', 'description': 'sort method', 'value': 'price'}."+\
            "we combine all the parameters into a list, resulting in:"+\
            "[{'type': 'profile','name': 'target_city','description': 'target city', 'value': 'New York'},{'type': 'fix','name': 'minimum_rating','description': 'minimum rating',"+\
            "'value': '4.5'},{'type': 'tool', 'name': 'sort_method','description': 'sort method','value': 'price'}]" +\
            "Finally, replace the list composed of interface parameters with the Interface Parameters of the selected API, and the final result will be" +\
            "{'Interface ID': '2','Interface Name': 'RestaurantFinder','Interface Address': 'http://127.0.0.1:5008',"+\
            "'Interface Description': 'RestaurantFinder is a tool for querying and analysing restaurant information. Users can enter their target city, a minimum rating, and a sorting method',"+\
            "'Interface Parameters':[{'type': 'profile','name': 'target_city','description': 'target city','value': 'New York'},"+\
            "{'type': 'fix','name': 'minimum_rating','description': 'minimum rating', 'value': '4.5' }, {'type': 'tool','name': 'sort_method','description': 'sort method','value': 'price'}],'Status': true,'Matched': true}"+\
            "Please return the interface in accordance with this format."


    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    fill_parameters = str(completion.choices[0].message.content)
    print(fill_parameters)

    # if isinstance(fill_parameters, dict):
    #     fill_parameters = json.dumps(fill_parameters)
    #
    # try:
    #     json_fill_parameters = json.loads(fill_parameters)
    # except json.decoder.JSONDecodeError:
    #     print(f"Unable to parse JSON: {fill_parameters}")
    #
    #
    # result_dict = json.loads(result)
    # result_dict["Interface Parameters"] = json_fill_parameters

    return fill_parameters

def ask_question(data: dict):
    description = data["description"]
    params = data["params"]

    API_result = find_best_match(description)

    result = fill_parameters(description, API_result, params)
    return result