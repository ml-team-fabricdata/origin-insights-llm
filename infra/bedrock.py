import boto3
import os

def get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))

def call_bedrock(prompt, model="haiku"):  # "haiku" o "sonnet"
    model_map = {
        "haiku":  "anthropic.claude-3-haiku-20240307-v1:0",
        "sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
        # por ahora se usaran estos. no se descarta Nova
    }

    client = get_bedrock_client()
    body = {
        "prompt": prompt,
        "max_tokens": 400,
        "temperature": 0.7,
        # según el modelo, el formato puede cambiar (se revisara luego)
    }

    response = client.invoke_model(
        modelId=model_map[model],
        body=json.dumps(body),
        contentType="application/json",
    )

    return json.loads(response["body"].read())