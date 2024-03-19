import os
from os.path import abspath, dirname, join

import asyncio
from ai_queries.generate import QueryGenerator
from dotenv import load_dotenv


CURRENT_DIR = os.path.dirname(__file__)
dotenv_path = join(dirname(abspath(__file__)), '.env')
load_dotenv(dotenv_path)


url: str = os.environ.get("GPT4V_URL", "")
key: str = os.environ.get("GPT4V_KEY", "")
az_monitor: str = os.environ.get("AZ_CONNECTION_LOG", "")

query_generator = QueryGenerator(aoai_url=url, aoai_key=key)

prompt = "Retrieve the information from all products that contains the name 'student' but are not 'student loans'."
query_type = "CosmosDB NoSQL"
programming_language = "Python"
db_params = {"database_name": "some_cosmos", "table_name": "products", "fields": ["product_name", "product_description"]}
parameters = {"temperature": 0.7, "top_p": 0.95, "max_tokens": 2000}


async def main():
    response = await query_generator.send_query(prompt, query_type, db_params, parameters, programming_language=programming_language)
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
