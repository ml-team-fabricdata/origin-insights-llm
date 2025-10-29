import boto3
import json


class EmbeddingsGenerator:

    def __init__(self, model_id="amazon.titan-embed-text-v2:0", region_name: str="us-east-1"):
        self._model_id = model_id
        self._client = boto3.client("bedrock-runtime", region_name=region_name)

    def get_embedding(self, texto, dim=512):
        response = self._client.invoke_model(
            modelId=self._model_id,
            body=json.dumps({"inputText": texto, "dimensions": dim})
        )
        result = json.loads(response["body"].read())
        return result["embedding"]


embeddings_generator = EmbeddingsGenerator()
