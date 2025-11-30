from fastapi import FastAPI
from pydantic import BaseModel
from service import extract_tasks_from_message, write_row_to_zoho, extract_data_from_sheets, summarize_with_groq
import uvicorn


app = FastAPI()


class LogRequest(BaseModel):
    user: str
    message: str
    timestamp: str
    
class SummaryRequest(BaseModel):
    user: str
    type: str


@app.get("/")
def home():
    return {"status": "Backend is running"}



@app.post("/extract-log")
def extract_log(data: LogRequest):
    tasks = extract_tasks_from_message(data.message)
    return {"user": data.user, "tasks": tasks}



@app.post("/save-log")
def save_log(data: LogRequest):
    # Here you can integrate any LLM extraction if needed
    tasks_json = '{"tasks":[{"task":"' + data.message + '","type":"general"}]}'

    res = write_row_to_zoho(user=data.user, message=data.message, tasks=tasks_json, date=data.timestamp)
    return {"status": "saved", "zoho_response": res}

@app.post("/datatosheet")
def data_to_sheet(data: LogRequest):
    print("Received data:", data)
    tasks = extract_tasks_from_message(data.message)
    res = write_row_to_zoho(user=data.user, message=data.message, tasks=tasks, date=data.timestamp)
    return {"status": "saved", "zoho_response": res}

@app.post("/summary")
def summary(data: SummaryRequest):
    print("Received summary request:", data)
    tasks = extract_data_from_sheets(data.type, data.user)
    if not tasks:
        return {"user": data.user, "summary": "No tasks found."}
    summarized_tasks = summarize_with_groq(tasks)
    
    print("Summarized tasks:", summarized_tasks)
    return {"user": data.user, "summary": summarized_tasks}
    
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
