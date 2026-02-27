import os
import time
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage, ImageMessage

CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
USER_ID = os.getenv('LINE_USER_ID')
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
GITHUB_REPOSITORY = os.getenv('GITHUB_REPOSITORY')

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

timestamp = int(time.time())
base_url = f'https://{GITHUB_USERNAME}.github.io/{GITHUB_REPOSITORY}/plots/'

messages = [TextMessage(text="📊 利回りチェック結果")]

# plotsフォルダ内の画像を送信（最大4枚）
for filename in os.listdir('plots')[:4]:
    image_url = f'{base_url}{filename}?t={timestamp}'
    messages.append(
        ImageMessage(
            original_content_url=image_url,
            preview_image_url=image_url
        )
    )

with ApiClient(configuration) as api_client:
    MessagingApi(api_client).push_message(
        PushMessageRequest(
            to=USER_ID,
            messages=messages
        )
    )

print("✅ LINE sent")
