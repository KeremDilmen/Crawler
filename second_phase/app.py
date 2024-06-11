from fastapi import FastAPI, BackgroundTasks, HTTPException
from celery import group
from celery.result import AsyncResult
from celery_config import app as celery_app
from tasks import fetch_all_companies, fetch_enterprise_details, save_to_json, run_analysis
import celery.states as states
import json
import logging

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/start_crawling")
def start_crawling(background_tasks: BackgroundTasks):
    try:
        task = fetch_all_companies.apply_async()
        background_tasks.add_task(check_and_continue, task.id)
        return {"message": "Crawling started", "task_id": task.id}
    except Exception as e:
        logger.error(f"Failed to start crawling: {e}")
        raise HTTPException(status_code=500, detail="Failed to start crawling")

def check_and_continue(task_id):
    try:
        result = AsyncResult(task_id, app=celery_app)
        if result.state == states.SUCCESS:
            enterprise_ids = result.result
            tasks = group(fetch_enterprise_details.s(enterprise_id) for enterprise_id in enterprise_ids)
            details_result = tasks.apply_async()
            details_result.get()
            save_to_json.delay(details_result.result)
            run_analysis.delay()
        elif result.state in [states.FAILURE, states.REVOKED]:
            logger.error(f"Crawling task {task_id} failed or was revoked")
    except Exception as e:
        logger.error(f"Error in check_and_continue: {e}")

@app.get("/status/{task_id}")
def get_status(task_id):
    try:
        result = AsyncResult(task_id, app=celery_app)
        if result.state == states.PENDING:
            return {"status": "Pending"}
        elif result.state == states.STARTED:
            return {"status": "In progress"}
        elif result.state == states.SUCCESS:
            return {"status": "Completed", "result": result.result}
        else:
            return {"status": "Failed", "reason": str(result.info)}
    except Exception as e:
        logger.error(f"Failed to get status for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task status")

@app.get("/result")
def get_result():
    try:
        with open('cluster_summaries.json', 'r') as f:
            result = json.load(f)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Result not available yet")
    except Exception as e:
        logger.error(f"Failed to retrieve result: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve result")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
