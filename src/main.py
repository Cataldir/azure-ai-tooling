
import os
import asyncio
import logging
import time
import json
from os.path import abspath, dirname, join
from dotenv import load_dotenv

from tools.ai_queries.generate import QueryGenerator
from tools.indexing.index_manager import add_data_to_index
from tools.research.index_management import create_or_update_search_index
from tools.research.operate import SearchEngine, SourceEngineSchema
from tools.data_ingestion.ado_analytics.ado import AzureDevOpsExtractor


logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

CURRENT_DIR = os.path.dirname(__file__)
dotenv_path = join(dirname(abspath(__file__)), ".env")
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
        query_type = "CosmosDB for MongoDB"
        programming_language = "Python"
        db_params = {
            "database_name": "some_cosmos",
            "table_name": "products",
            "fields": ["product_name", "product_description"],
        }

        parameters = {
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 2000,
        }

        response = await query_generator.send_request(
            prompt,
            query_type,
            db_params,
            parameters,
            programming_language=programming_language,
        )

        assert isinstance(response, str)
        return response

    @staticmethod
    async def test_search_engine():
        schema = SourceEngineSchema(
            origin={
                "bing": {
                    "subscription-key": os.environ.get(
                        "BING_SUBSCRIPTION_KEY", ""
                    ),
                    "endpoint": os.environ.get("BING_SEARCH_URL", ""),
                },
                "topic": "Melhores planos de gerenciamento de dados em 2022",
            },
            destination={
                "blob-connection-string": os.environ.get(
                    "BLOB_STORAGE_CONNECTION_STRING", ""
                ),
                "blob-container": os.environ.get(
                    "BLOB_STORAGE_STORAGE_ACCOUNT", ""
                )
                + "/item-search",
            },
        )
        search_engine = SearchEngine(schema)
        endpoint = os.environ.get("ENDPOINT_AI_SEARCH", "")
        api_key = os.environ.get("API_KEY_AI_SEARCH", "")
        index_name = "some-search-index"
        index = await create_or_update_search_index(
            endpoint=endpoint,
            api_key=api_key,
            index_name=index_name
        )

        search_result = search_engine.retrieve_data()
        if index:
            await add_data_to_index(
                endpoint=endpoint,
                index_name=index_name,
                api_key=api_key,
                data=search_result,
            )
        response = search_engine.post_data()
        assert response is None

    @staticmethod
    def test_ado():
        ado_extractor = AzureDevOpsExtractor()
        days = 10
        start = time.time()
        items_list = asyncio.run(
            ado_extractor.format_work_items(
                process_date="2024-03-18", days_length=days
            )
        )
        end = time.time()
        for work_item in items_list:
            custom_items = work_item.custom
            if custom_items is None:
                continue
            if any([custom_items.gbb_specialist != '', custom_items.gbb_tai != '', custom_items.gbb_tapps != '']):
                print(work_item)
        logger.info("Items Retrieved")
        logger.info("Time for completion on %s days: %s", str(days), str(end - start))
        dict_items = [item.model_dump() for item in items_list]
        with open("sample.json", "w+", encoding='utf-8') as f:
            f.write(json.dumps(dict_items, indent=2))
        print("End of Program.")


if __name__ == "__main__":
    method = input("Select the Method: ")
    routine = TestRoutinesHook()
    asyncio.run(getattr(routine, method)())
