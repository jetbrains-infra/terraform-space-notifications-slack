""" Send ECS events to Slack """

import json
import os

import boto3
import requests

webhook_url = os.getenv("SLACK_WEBHOOK")
channel = os.getenv("SLACK_CHANNEL")
slack_username = os.getenv("SLACK_USERNAME")
stack_name = os.getenv("STACK_NAME")
client_service = boto3.client("ecs")


def describe_containers(msg):
    """Generate containers message"""
    list_of_containers = ["\n"]
    for container in msg["detail"]["containers"]:
        tmp = (
            f'• <https://{msg["region"]}.console.aws.amazon.com/cloudwatch/home?'
            + f'region={msg["region"]}#logsV2:log-groups/log-group/{stack_name}-logs/'
            + f'log-events/{container["name"]}$252F{container["name"]}'
            + f'$252F{container["taskArn"].split("/").pop()}|{container["name"]}>'
            + " ("
            + (str(container["exitCode"]) if "exitCode" in container else "")
            + ")"
        )
        list_of_containers.append(tmp)
    return "\n".join(list_of_containers)


def describe_event(cluster, service):
    """AWS ECS API request for collecting event message"""
    resp = client_service.describe_services(
        cluster=cluster,
        services=[
            service,
        ],
    )
    for event in resp["services"][0]["events"][:5]:
        if "unhealthy" in str(event["message"]):
            msg = event["message"].split("reason").pop()[:-1]
            return msg
    return ""


def test_message(event):
    """Message generator"""
    msg_dict = {}
    if "AlarmName" in event:
        msg_dict["alarmName"] = event["AlarmName"]
        msg_dict["event"] = event["AlarmDescription"]
        msg_dict["description"] = event["NewStateValue"]
    elif "source" in event:
        if event["source"] == "aws.ecs":
            msg_dict["alarmName"] = event["detail"]["group"]
            msg_dict["serviceUrl"] = (
                f'<https://{event["region"]}.console.aws.amazon.com/ecs/home'
                + f'?region={event["region"]}#/clusters/'
                + f'{event["detail"]["group"].split(":").pop().split("-")[0]}'
                + f'/services/{event["detail"]["group"].split(":").pop()}'
                + f'/details|{event["detail"]["group"]}>'
            )
            msg_dict["event"] = (
                event["detail-type"] + " to " + event["detail"]["desiredStatus"]
            )
            msg_dict["currentStatus"] = event["detail"]["lastStatus"]
            if event["detail"]["desiredStatus"] == "STOPPED":
                msg_dict["description"] = event["detail"]["stoppedReason"]
                if "Task failed ELB health checks" in event["detail"]["stoppedReason"]:
                    msg_dict["TargetGroupURL"] = (
                        f'<https://{event["region"]}.console.aws.amazon.com/ec2/v2/home?'
                        + f'region={event["region"]}#TargetGroup:targetGroupArn='
                        + f'{event["detail"]["stoppedReason"].split("target-group ")[1][:-1]}'
                        + "|TargetGroupUrl>"
                    )
            if "containerInstanceArn" in event["detail"]:
                msg_dict["instance"] = (
                    f'<https://{event["region"]}.console.aws.amazon.com/ecs/home?'
                    + f'region={event["region"]}#/clusters/'
                    + f'{event["detail"]["group"].split(":").pop().split("-")[0]}'
                    + f'/containerInstances/{event["resources"][0].split("/").pop()}|'
                    + f'{event["detail"]["containerInstanceArn"].split("/").pop()}>'
                )
            msg_dict["taskId"] = (
                f'<https://{event["region"]}.console.aws.amazon.com/ecs/home'
                + f'?region={event["region"]}#/clusters/'
                + f'{event["detail"]["group"].split(":").pop().split("-")[0]}/tasks/'
                + f'{event["resources"][0].split("/").pop()}/details|'
                + f'{event["resources"][0].split("/").pop()}>'
            )
            if event["detail"]["desiredStatus"] == "STOPPED":
                msg_dict["healthcheck"] = describe_event(
                    event["detail"]["clusterArn"].split("/").pop(),
                    event["detail"]["group"].split(":").pop(),
                )
            if "containers" in event["detail"]:
                msg_dict["containers"] = describe_containers(event)
            if (
                event["detail"]["desiredStatus"] == "RUNNING"
                and event["detail"]["lastStatus"] == "RUNNING"
            ):
                msg_dict["attachmentsColor"] = "#0BF712"
            elif (
                event["detail"]["desiredStatus"] == "RUNNING"
                and event["detail"]["lastStatus"] != "RUNNING"
            ):
                msg_dict["attachmentsColor"] = "#FDF605"
            else:
                msg_dict["attachmentsColor"] = "#FF2D00"
    else:
        msg_dict["alarmName"] = event["AutoScalingGroupName"]
        msg_dict["serviceUrl"] = (
            f'<https://{event["AutoScalingGroupARN"].split(":")[3]}.console.aws.amazon.com'
            + f'/ec2autoscaling/home?region={event["AutoScalingGroupARN"].split(":")[3]}#/details/'
            + f'{event["AutoScalingGroupName"]}?view=details|{event["AutoScalingGroupName"]}>'
        )
        msg_dict["event"] = event["Event"]
        msg_dict["description"] = event["Description"]
        msg_dict["cause"] = event["Cause"]
    return msg_dict


def send_message(msg_dict):
    """Send slack message"""
    text_list = list(
        filter(
            None,
            [
                "*Event*: " + msg_dict["event"],
                "*Current status*: " + msg_dict["currentStatus"]
                if "currentStatus" in msg_dict
                else None,
                "*Description*: "
                + msg_dict["description"]
                + " "
                + (msg_dict["TargetGroupURL"] if "TargetGroupURL" in msg_dict else "")
                if "description" in msg_dict
                else None,
                "*Cause*: " + msg_dict["cause"] if "cause" in msg_dict else None,
                ("*Healthcheck*: " + msg_dict["healthcheck"])
                if "healthcheck" in msg_dict and msg_dict["healthcheck"] != ""
                else None,
                "*Container(ExitCode)*: " + msg_dict["containers"]
                if "containers" in msg_dict
                else None,
                "*TaskId*: " + msg_dict["taskId"] if "taskId" in msg_dict else None,
                "*Instance*: " + msg_dict["instance"]
                if "instance" in msg_dict
                else None,
            ],
        )
    )
    text = "\n".join(text_list)

    message = {
        "channel": channel,
        "username": slack_username,
        "text": ("*" + msg_dict["alarmName"] + "*")
        if "serviceUrl" not in msg_dict
        else msg_dict["serviceUrl"],
        "attachments": [
            {
                "text": text,
                "color": msg_dict["attachmentsColor"]
                if "attachmentsColor" in msg_dict
                else "#9B9B9B",
            }
        ],
    }
    response = requests.post(
        webhook_url,
        data=json.dumps(message),
        headers={"Content-Type": "application/json"},
    )
    if response.status_code != 200:
        raise ValueError(
            f"Request to slack returned an error {response.status_code},"
            + f" the response is:\n{response.text}"
        )


def lambda_handler(event, context):
    """Main entrypoint function"""
    print("Lambda function ARN:", context.invoked_function_arn)
    event_message = json.loads(event["Records"][0]["Sns"]["Message"])
    send_message(test_message(event_message))
    return True


if __name__ == "__main__":
    lambda_handler({}, "")
