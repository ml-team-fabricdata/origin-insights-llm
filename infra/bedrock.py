import boto3
import os
import json

def get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))

def call_bedrock_llm1(prompt):
    """
    LLM1 (Default rápido): Claude 3.5 Haiku — 2024-10-22
    """
    return _invoke_bedrock(prompt, model="haiku")

def call_bedrock_llm2(prompt):
    """
    LLM2 (Smart): Claude 3.7 Sonnet — 2025-02-19
    """
    return _invoke_bedrock(prompt, model="sonnet")

def _invoke_bedrock(prompt, model="haiku"):
    model_map = {
        "haiku":  "anthropic.claude-3-5-haiku-20241022-v1:0",
        "sonnet": "anthropic.claude-3-7-sonnet-20250219-v1:0"
    }

    client = get_bedrock_client()
    body = {
        "prompt": prompt,
        "max_tokens": 400,
        "temperature": 0.7,
    }

    response = client.invoke_model(
        modelId=model_map[model],
        body=json.dumps(body),
        contentType="application/json",
    )

    return json.loads(response["body"].read())