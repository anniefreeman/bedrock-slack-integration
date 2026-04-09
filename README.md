# bedrock-slack-integration

# Slack Bedrock Summariser — Setup & Operations Guide

A Slack bot that summarises text using Amazon Bedrock. Mention the bot in a Slack channel with some text and it will reply with a 2-3 sentence summary.

---

## Architecture

```
Slack → API Gateway → Lambda → Amazon Bedrock (Claude Haiku)
                    ↑
              (response posted back to Slack)
```

---

## Components

| Component | Name/ID |
|---|---|
| AWS Region | eu-north-1 |
| API Gateway | https://9eiklj7xzh.execute-api.eu-north-1.amazonaws.com |
| API Route | POST /slack/events |
| Lambda Function | bedrock-slack-integration |
| Lambda Role | bedrock-slack-integration-role-tdjysqf8 |
| Bedrock Model | eu.anthropic.claude-haiku-4-5-20251001-v1:0 |

---

## Lambda Code

```python
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

```

---

## Environment Variables

Set in Lambda console under **Configuration → Environment variables**.

| Key | Value |
|---|---|
| `SLACK_TOKEN` | The bot user OAuth token from the Slack app settings. Starts with `xoxb-`. |

---

## Testing

### 1. Test Lambda directly (AWS Console)

Go to your Lambda function → **Test tab**, paste the following and click **Test**:

```json
{
  "body": "{\"event\": {\"type\": \"app_mention\", \"text\": \"<@U12345678> Can you summarise this? Artificial intelligence is transforming industries across the globe. From healthcare to finance, AI systems are being used to automate complex tasks and analyse large datasets.\", \"channel\": \"C12345678\", \"user\": \"U87654321\"}}"
}
```

A successful response looks like:

```json
{
  "statusCode": 200
}
```

### 2. Test API Gateway via curl

Run this from your terminal to confirm API Gateway is routing correctly to Lambda:

```bash
curl -X POST https://9eiklj7xzh.execute-api.eu-north-1.amazonaws.com/slack/events \
  -H "Content-Type: application/json" \
  -d '{"challenge": "test123"}'
```

Expected response: `test123`

### 3. Test the full integration via Slack

In any Slack channel where the bot has been invited, type:

```
@YourBotName Can you summarise this? [paste your text here]
```

The bot should reply with a summary within a few seconds.

---

## Turning the Integration On and Off

You can disable and re-enable the bot by setting the Lambda concurrency to 0. This prevents any invocations without deleting anything.

### Turn off

1. Go to **AWS Console → Lambda → bedrock-slack-integration**
2. Click **Configuration → Concurrency**
3. Click **Edit**
4. Select **Reserve concurrency** and set the value to **0**
5. Click **Save**

API Gateway will now return a 429 to all requests.

### Turn on

1. Go to **AWS Console → Lambda → bedrock-slack-integration**
2. Click **Configuration → Concurrency**
3. Click **Edit**
4. Select **Use unreserved concurrency**
5. Click **Save**

The bot will be live again within a few seconds.

---

## Slack App Settings

All Slack configuration lives at [api.slack.com/apps](https://api.slack.com/apps).

| Setting | Location |
|---|---|
| Bot token | Install App → Bot User OAuth Token |
| Signing secret | Basic Information → App Credentials |
| Event subscriptions | Features → Event Subscriptions |
| Webhook URL | Features → Event Subscriptions → Request URL |
| Bot scopes | OAuth & Permissions → Scopes |

### Required bot scopes

- `app_mentions:read` — receive @mention events
- `chat:write` — post messages to channels
- `channels:history` — read channel messages

---

## IAM Permissions

The Lambda execution role `bedrock-slack-integration-role-tdjysqf8` requires the following policy to call Bedrock:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:eu-north-1::foundation-model/eu.anthropic.claude-haiku-4-5-20251001-v1:0"
    }
  ]
}
```

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Handler missing` | Function name mismatch | Ensure the function is named `lambda_handler` |
| `Task timed out` | Lambda timeout too short | Set timeout to 30s under Configuration → General |
| `EndpointConnectionError` | Wrong AWS region | Ensure region in code matches where Lambda is deployed |
| `ValidationException: invalid model` | Wrong model ID | Copy the exact model ID from Bedrock → Model catalog |
| `AccessDeniedException` | Missing IAM permissions | Attach Bedrock policy to the Lambda execution role |
| `ValidationException: on-demand not supported` | Missing region prefix on model ID | Add `eu.` prefix to the model ID |
| Slack URL not verifying | Lambda not deployed or challenge handler missing | Ensure Lambda is live and the challenge check is at the top of the handler |
| Duplicate responses | Slack retrying due to slow response | Respond to Slack immediately and process Bedrock call asynchronously |
