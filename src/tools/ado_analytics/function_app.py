import json
import logging
import os
import time
from datetime import datetime, timedelta

import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv

from .ado import query_work_items

load_dotenv()

connection_string = os.getenv("BLOB_STORAGE_CONNECTION_STRING")
container_name = os.getenv("BLOB_STORAGE_CONTAINER_NAME")

search_client = SearchClient(
    endpoint=os.getenv("AZURE_AI_SEARCH_ENDPOINT"),
    index_name=os.getenv("AZURE_AI_INDEX_NAME"),
    credential=AzureKeyCredential(os.getenv("AZURE_AI_SEARCH_KEY")),
)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="adopoller", methods=["GET"])
def ado_function_poller(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    # json response
    json_response = {"values": []}

    # define date range
    start_date = datetime.now() - timedelta(days=10)
    end_date = datetime.now()

    logging.info(f"Start_date:{start_date}")
    logging.info(f"End_date:{start_date}")

    logging.info("getting work items...")

    # Loop between the days from start_date to end_date
    while start_date <= end_date:
        try:
            work_items_as_dict = query_work_items(start_date.strftime("%Y-%m-%d"))

            if work_items_as_dict:
                # add json to json_response values
                for work_item in work_items_as_dict:
                    try:
                        result = search_client.upload_documents(work_item)
                        logging.info(f"Uploaded work item to Azure Search Index: {result}")

                        json_response["values"].append(
                            {f"The recordId {work_item['id']} has been added"}
                        )
                    except Exception as e:
                        logging.error(f"Error dumping work item to blob storage: {e}")
                        json_response["values"].append(
                            {
                                "errors": [
                                    {
                                        "message": f"Error dumping work item {work_item['id']} to blob storage: {e}"
                                    }
                                ]
                            }
                        )
            else:
                logging.info("vector is empty")

                # add json with error to json_response values
                json_response["values"] = [
                    {"errors": [{"message": "No work items found in the date range."}]}
                ]
        except Exception as e:
            print(e)

        start_date += timedelta(days=1)
        time.sleep(2)

    return func.HttpResponse(f"The process has been concluded: {json.dumps(json_response)}")
