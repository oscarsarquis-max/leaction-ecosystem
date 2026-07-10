from app import create_app
from app.infrastructure.ai_client import invoke_claude

app = create_app()
with app.app_context():
    text = invoke_claude("Responda apenas: OK", max_tokens=20)
    print("bedrock_ok:", text[:80])
