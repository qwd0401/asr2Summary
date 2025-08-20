import requests

url = "https://api.siliconflow.cn/v1/audio/transcriptions"

files = { "file": open('asr.mp3', 'rb') }
payload = { "model": "FunAudioLLM/SenseVoiceSmall" }
headers = {"Authorization": "Bearer sk-breyqcjehyljoocgimftfmhndccaxntudloarkfpdqlwjqxs"}

response = requests.post(url, data=payload, files=files, headers=headers)

# 将结果写入文件
with open('transcription_result.txt', 'w', encoding='utf-8') as f:
    result = response.json()
    if 'text' in result:
        f.write(result['text'])
    else:
        f.write(str(result))