import os, json
from openai import OpenAI

with open('json/setting.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

client = OpenAI(
    api_key=cfg['AIAPIKEY'],
    base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}}
)

print(response.choices[0].message.content)