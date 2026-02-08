import os
from openai import OpenAI

client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=os.environ.get("ARK_API_KEY"),
)

prompt = '只输出JSON：{"translation":"测试","part_of_speech":"noun","ipa":"","phonetic_us":"","phonetic_uk":"","word_roots":[],"tense_form":"","common_meanings":[],"related_terms":[],"definition":""}'

resp = client.chat.completions.create(
    model=os.environ.get("LLM_MODEL"),
    messages=[{"role":"user","content":prompt}],
    temperature=0.2,
)

print(resp.choices[0].message.content)
