import os
import json
from fastapi import params
import requests
from dotenv import load_dotenv
from datetime import datetime


load_dotenv()


GROQ_API_KEY = os.getenv("GROQ_API_KEY")

ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
ZOHO_SHEET_ID = os.getenv("ZOHO_SHEET_ID")
ZOHO_WORKSHEET_NAME = os.getenv("ZOHO_WORKSHEET_NAME", "Sheet1")


def get_zoho_access_token():
    token_url = "https://accounts.zoho.in/oauth/v2/token" 
    payload = {
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    res = requests.post(token_url, data=payload)
    data = res.json()
    if "access_token" not in data:
        raise Exception(f"ZOHO TOKEN ERROR: {data}")
    return data["access_token"]

def summarize_with_groq(tasks: list):
    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": "llama-3.1-8b-instant",
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "Summarize the following tasks like what tasks done and status in a sentence"},
            {"role": "user", "content": f"""
        Summarize these tasks:

        {tasks}

        """}
                ]
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    res = requests.post(url, json=payload, headers=headers)
    # print("Groq summary response status:", res.content)
    try:
        content = res.json()["choices"][0]["message"]["content"]
        return content # return Python dict
    except Exception as e:
        print("Error parsing Groq summary response:", e)
        return {"tasks": []}

def extract_tasks_from_message(message: str):
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "llama-3.1-8b-instant",
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "Extract work tasks from text. Return STRICT JSON only."},
            {"role": "user", "content": f"""
        Extract tasks from this text and return JSON only:

        Text: "{message}"

        Format:
        {{
        "tasks": [
            {{"task": "...", "type": "..."}}
        ]
        }}
        """}
                ]
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    res = requests.post(url, json=payload, headers=headers)
    # print("Groq response status:", res)   
    try:
        content = res.json()["choices"][0]["message"]["content"]
        return json.loads(content)  # return Python dict
    except Exception as e:
        print("Error parsing Groq response:", e)
        return {"tasks": []}


def write_row_to_zoho(user: str, message: str, tasks: dict, date: str = None):
    access_token = get_zoho_access_token()
    
    url = f"https://sheet.zoho.in/api/v2/{ZOHO_SHEET_ID}" 
    
    paramMap = {}
    paramMap['method'] = 'worksheet.jsondata.append'             
    paramMap['worksheet_name'] = ZOHO_WORKSHEET_NAME
   
    
    row_data = [
        {
            "User": user,
            "Message": message,
            "Tasks": json.dumps(tasks),
            "Date" : date if date else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    ]
    
    paramMap['json_data'] = json.dumps(row_data)  
    
    headers = {
        'Content-type': 'application/x-www-form-urlencoded',
        'Authorization': f'Zoho-oauthtoken {access_token}'
    }
    
    # Send request
    response = requests.post(url=url, headers=headers, data=paramMap)
    
    # Parse response
    try:
        return response.json()
    except Exception:
        return {"status": "error", "raw_response": response.text}
    
def extract_data_from_sheets(data_type: str, user: str):
    access_token = get_zoho_access_token()

    url = f"https://sheet.zoho.in/api/v2/{ZOHO_SHEET_ID}"

    paramMap = {
        "method": "worksheet.content.get",
        "worksheet_name": ZOHO_WORKSHEET_NAME
    }

    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }

    res = requests.post(url, headers=headers, data=paramMap).json()
    # print("Zoho sheet data fetch response:", res)

    rows = res.get("range_details", [])

    # --------- Extract header row ---------
    header_row = rows[0]["row_details"]
    headers_list = [col["content"] for col in header_row]

    # --------- Extract data row-by-row ---------
    parsed_rows = []
    for row in rows[1:]:
        row_data = row["row_details"]
        row_dict = {}

        for col in row_data:
            col_index = col["column_index"] - 1  # 1-based index
            if col_index < len(headers_list):
                row_dict[headers_list[col_index]] = col["content"]

        parsed_rows.append(row_dict)
    print("Parsed rows from Zoho sheet:", parsed_rows)
    # Filter by user
    user_rows = [r for r in parsed_rows if r.get("User") == user]
    print("Filtered rows by user:", user_rows)
    # Filter by today (if timestamp column exists)
    if data_type == "today":
        today = datetime.now().date()

        user_rows = [
            r for r in user_rows
            if "Date" in r and
            datetime.strptime(r["Date"], "%d/%m/%Y %I:%M:%S %p").date() == today
        ]
    print("Rows after date filtering:", user_rows)

    return user_rows


def log_user_message(user: str, message: str):
    tasks = extract_tasks_from_message(message)
    print("Extracted tasks:", tasks)
    result = write_row_to_zoho(user, message, tasks)
    return result

# Example usage:
if __name__ == "__main__":
    user_name = "Alice"
    message_text = "Fixed API latency issue, reviewed PR #112, started DB schema changes."
    res = log_user_message(user_name, message_text)
    print(res)
