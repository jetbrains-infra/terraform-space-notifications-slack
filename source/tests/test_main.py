""" Unit tests file """

import json
import logging
from unittest import TestCase, mock

from lambda_function import main

logging.basicConfig(level=logging.DEBUG)


class TestLambdaFunction(TestCase):
    """Unit tests for lambda_function.main"""

    @mock.patch("lambda_function.main.requests")
    def test_python_function(self, mock_requests):
        """Simple Unit test for lambda_function.main"""
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response

        message = json.dumps(
            {
                "AutoScalingGroupName": "Name",
                "AutoScalingGroupARN": "arn:aws:autoscaling:::autoScalingGroup/Name",
                "Event": "Event",
                "Description": "Description",
                "Cause": "Cause",
            }
        )
        result = main.lambda_handler(
            {"Records": [{"Sns": {"Message": message}}]},
            type("obj", (object,), {"invoked_function_arn": "arn:aws:::Lambda"}),
        )
        self.assertEqual(result, True)
