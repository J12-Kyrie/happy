from openai import OpenAI


client = OpenAI(
    api_key="sk-pSgixPnLcUr23Kubw8TU2AoDjpks0kNBb4U5nPsKquIwyUFV",  
    base_url="https://api.chatfire.cn/v1"  
)


response = client.chat.completions.create(
    model="gpt-4o", 
    messages=[
        {"role": "system", "content": "你是一个有用的助手。"},
        {"role": "user", "content": "你好，请介绍一下你自己。"}
    ]
)

print(response.choices[0].message.content)