import pymysql
import re
from g4f.client import Client

def connect_to_database():
    connection = pymysql.connect(
        host='mysql-1bddf0d4-davis1233798-2632.d.aivencloud.com',
        port=20946,
        user='avnadmin',
        password='AVNS_3CFEpoeFyEEN3_eoQ8K',
        database='defaultdb',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    print("Connected to MySQL")
    return connection

def clean_text(input_text):
    return re.sub(r'[^\u0000-\uFFFF]', '', input_text)

def find_next_available_id(cursor, initial_id):
    max_attempts = 10
    current_id = initial_id
    for attempt in range(max_attempts):
        cursor.execute("SELECT is_taken FROM prompts WHERE id = %s", (current_id,))
        result = cursor.fetchone()
        if result and result['is_taken'] == 0:
            return current_id
        current_id += 1
    return None  # 如果嘗試了最大次數還未找到，返回 None

def process_prompts():
    connection = connect_to_database()
    client = Client()  # 假設已建立Client類別用於模型互動
    try:
        with connection.cursor() as cursor:
            while True:
                connection.begin()

                cursor.execute("SELECT MIN(prompts_id) as last_id FROM final WHERE result2 IS NULL")
                last_id_result = cursor.fetchone()
                
                if not last_id_result or not last_id_result['last_id']:
                    connection.rollback()
                    break

                next_id = find_next_available_id(cursor, last_id_result['last_id'])
                
                if not next_id:
                    connection.rollback()
                    break

                updated_rows = cursor.execute("UPDATE prompts SET is_taken = 1 WHERE id = %s AND is_taken = 0", (next_id,))
                if updated_rows == 0:
                    connection.rollback()
                    continue
                
                connection.commit()

                cursor.execute("""
                    SELECT p.id, p.cve_id, p.method, p.trained_result, p.final_count, d.value as description
                    FROM prompts p
                    JOIN descriptions d ON p.cve_id = d.cve_id
                    WHERE p.id = %s
                    LIMIT 1
                """, (next_id,))
                result = cursor.fetchone()
                
                if not result:
                    continue

                content = f"請你詳細的閱讀修補方法後,使用你的專業判斷修補方法是否能正確的修補漏洞 1.修補方法: {result['trained_result']} 2.漏洞: {result['description']}  3.只需要回答是或否即可。"
                message = [{"role": "資訊安全專家", "content": content}]
                response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=message,
                )
                clean_content = clean_text(response.choices[0].message.content)

                connection.begin()
                cursor.execute("UPDATE final SET result2 = %s WHERE prompts_id = %s", (clean_content, next_id))
                cursor.execute("UPDATE prompts SET is_taken = 0 WHERE id = %s", (next_id,))
                connection.commit()
    finally:
        connection.close()

process_prompts()
