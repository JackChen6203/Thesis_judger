import pymysql
import re
from g4f.client import Client
import base64
import requests

def connect_to_database():
    pwString = "QVZOU18zQ0ZFcG9lRnlFRU4zX2VvUThL"
    pwBytes = base64.b64decode(pwString)
    pw = pwBytes.decode('utf-8')
    print("正在連接資料庫...")
    return pymysql.connect(
        host='mysql-1bddf0d4-davis1233798-2632.d.aivencloud.com', 
        port=20946, user='avnadmin',
         password=pw, database='defaultdb', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

def clean_text(input_text):
    cleaned_text = re.sub(r'[^\u0000-\uFFFF]', '', input_text)
    print(f"清理後的文字: {cleaned_text}")
    return cleaned_text

def check_for_error(response_text):
    error_message = "<!doctype html>\n<html lang=en>\n<title>500 Internal Server Error</title>\n<h1>Internal Server Error</h1>\n<p>The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.</p>"
    if error_message in response_text:
        print("偵測到內部伺服器錯誤訊息，不進行資料庫更新。")
        return True
    return False

def process_prompts():
    client = Client()
    connection = connect_to_database()
    try:
        while True:
            prompt_info = get_next_prompt(connection)
            if not prompt_info:
                print("檢查後仍無可用提示或空缺欄位，程式將結束。")
                break
            prompt_id = prompt_info['id']
            field_name = prompt_info['field_name']
            cursor = connection.cursor()
            cursor.execute("SELECT p.trained_result, d.value as description FROM prompts p JOIN descriptions d ON p.cve_id = d.cve_id WHERE p.id = %s", (prompt_id,))
            result = cursor.fetchone()
            content = f"請您實際的使用\n1.修補方法: {result['trained_result']} 來修補\n2.漏洞: {result['description']} 確認實作修補策略是否可修補這個漏洞\n3.只需要回答是或否即可。"
            response = requests.get(f"http://127.0.0.1:5500?text={content}")
            if check_for_error(response.text):
                continue
            decision = clean_text(response.text)
            print(decision)
            update_field(connection, prompt_id, field_name, decision)
    except Exception as e:
        print(f"發生錯誤：{str(e)}")
    finally:
        if connection and connection.open:
            connection.close()

process_prompts()
