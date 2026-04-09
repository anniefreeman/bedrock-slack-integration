import boto3, json, urllib.request
import os

SLACK_TOKEN = os.environ["SLACK_TOKEN"]

def lambda_handler(event, context):
    body = json.loads(event["body"])
    
    # Slack sends a URL verification challenge on first setup
    if "challenge" in body:
        return {"statusCode": 200, "body": body["challenge"]}

    slack_event = body["event"]
    text = slack_event["text"]
    channel = slack_event["channel"]

    # Call Bedrock
    bedrock = boto3.client("bedrock-runtime", region_name="eu-north-1")
    response = bedrock.invoke_model(
        modelId="eu.anthropic.claude-haiku-4-5-20251001-v1:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": f"Summarize this in 2-3 sentences: {text}"}]
        })
    )
    summary = json.loads(response["body"].read())["content"][0]["text"]

    # Post back to Slack
    msg = json.dumps({"channel": channel, "text": summary}).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=msg,
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"}
    )
    urllib.request.urlopen(req)

    return {"statusCode": 200}
