import os
from os.path import abspath, dirname, join

import asyncio
from typing import Dict, List

from ai_queries.generate import QueryGenerator
from research.operate import SearchEngine, SourceEngineSchema
from research.index_management import create_or_update_search_index, add_data_to_index

from dotenv import load_dotenv


CURRENT_DIR = os.path.dirname(__file__)
dotenv_path = join(dirname(abspath(__file__)), '.env')
load_dotenv(dotenv_path)


class TestRoutinesHook:

    @staticmethod
    async def test_query_generator():
        url: str = os.environ.get("GPT4V_URL", "")
        key: str = os.environ.get("GPT4V_KEY", "")
        az_monitor: str = os.environ.get("AZ_CONNECTION_LOG", "")

        query_generator = QueryGenerator(aoai_url=url, aoai_key=key)
        # query_generator = QueryGenerator(aoai_url=url, aoai_key=key, az_monitor=az_monitor) // If want to enable azure monitor logs

        prompt = "Retrieve the information from all products that contains the name 'student' but are not 'student loans'."
        query_type = "CosmosDB NoSQL"
        programming_language = "Python"
        db_params = {"database_name": "some_cosmos", "table_name": "products", "fields": ["product_name", "product_description"]}
        parameters = {"temperature": 0.7, "top_p": 0.95, "max_tokens": 2000}

        response = await query_generator.send_query(prompt, query_type, db_params, parameters, programming_language=programming_language)
        assert type(response) == str
        return response

    @staticmethod
    async def test_search_engine():
        schema = SourceEngineSchema(
            origin = {
                "bing": {
                    "subscription-key": os.environ.get("BING_SUBSCRIPTION_KEY", ""),
                    "endpoint": os.environ.get("BING_SEARCH_URL", "")
                },
                "topic": "Melhores planos de telefonia móvel"
            },
            destination = {
                "blob-connection-string": os.environ.get("BLOB_STORAGE_CONNECTION_STRING", ""),
                "blob-container": os.environ.get("BLOB_STORAGE_STORAGE_ACCOUNT", "")+"/claro-search"
            }
        )
        search_engine = SearchEngine(schema)
        endpoint = os.environ.get("ENDPOINT_AI_SEARCH", "")
        api_key = os.environ.get("API_KEY_AI_SEARCH", "")
        index_name = "claro-bing-search-index"
        index = await create_or_update_search_index(endpoint=endpoint, api_key=api_key, index_name=index_name)

        search_result = search_engine.retrieve_data()
        if index:
            await add_data_to_index(
                endpoint=endpoint,
                index_name=index_name,
                api_key=api_key,
                data=search_result
            )
        response = search_engine.post_data()
        assert response is None


if __name__ == "__main__":
    method = input('Select the Method: ')
    routine = TestRoutinesHook()
    asyncio.run(getattr(routine, method)())
