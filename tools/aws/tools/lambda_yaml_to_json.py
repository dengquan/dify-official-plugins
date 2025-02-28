import json
import logging
from typing import Any, Generator

import boto3  # type: ignore
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

console_handler = logging.StreamHandler()
logger.addHandler(console_handler)


class LambdaYamlToJsonTool(Tool):
    lambda_client: Any = None

    def _invoke_lambda(self, lambda_name: str, yaml_content: str) -> str:
        msg = {"body": yaml_content}
        logger.info(json.dumps(msg))

        invoke_response = self.lambda_client.invoke(
            FunctionName=lambda_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(msg),
        )
        response_body = invoke_response["Payload"]

        response_str = response_body.read().decode("utf-8")
        resp_json = json.loads(response_str)

        logger.info(resp_json)
        if resp_json["statusCode"] != 200:
            raise Exception(f"Invalid status code: {response_str}")

        return resp_json["body"]

    def _invoke(
        self,
        tool_parameters: dict[str, Any],
    ) -> Generator[ToolInvokeMessage, None, None]:
        """
        invoke tools
        """
        try:
            if not self.lambda_client:
                aws_region = tool_parameters.get(
                    "aws_region"
                )  # todo: move aws_region out, and update client region
                if aws_region:
                    self.lambda_client = boto3.client("lambda", region_name=aws_region)
                else:
                    self.lambda_client = boto3.client("lambda")

            yaml_content = tool_parameters.get("yaml_content", "")
            if not yaml_content:
                yield self.create_text_message("Please input yaml_content")
                return
            lambda_name = tool_parameters.get("lambda_name", "")
            if not lambda_name:
                yield self.create_text_message("Please input lambda_name")
                return
            logger.debug(f"{json.dumps(tool_parameters, indent=2, ensure_ascii=False)}")

            result = self._invoke_lambda(lambda_name, yaml_content)
            logger.debug(result)

            yield self.create_text_message(result)
        except Exception as e:
            yield self.create_text_message(f"Exception: {str(e)}")
            return
        console_handler.flush()
