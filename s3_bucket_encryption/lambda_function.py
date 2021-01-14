"""Ensures S3 Buckets have server side encryption enabled"""
# Forked from: https://github.com/awslabs/aws-config-rules/blob/master/python/s3_bucket_default_encryption_enabled.py
#
# Trigger Type: Change Triggered
# Scope of Changes: S3:Bucket
# Accepted Parameters: None
# Your Lambda function execution role will need to have a policy that provides
# the appropriate permissions. Here is a policy that you can consider.
# You should validate this for your own environment.
#
# Optional Parameters:
# 1. Key: SSE_OR_KMS
#    Values: SSE, KMS
# 2. Key: KMS_ARN
#    Value: ARN of the KMS key
#
# NOTE: If you specify KMS_ARN, you must choose KMS for SSE_OR_KMS.
#
# {
#    "Version": "2012-10-17",
#    "Statement": [
#        {
#            "Effect": "Allow",
#            "Action": [
#                "logs:CreateLogGroup",
#                "logs:CreateLogStream",
#                "logs:PutLogEvents"
#            ],
#            "Resource": "arn:aws:logs:*:*:*"
#        },
#        {
#            "Effect": "Allow",
#            "Action": [
#                "config:PutEvaluations"
#            ],
#            "Resource": "*"
#        },
#        {
#            "Effect": "Allow",
#            "Action": [
#                "s3:GetEncryptionConfiguration"
#            ],
#            "Resource": "arn:aws:s3:::*"
#        }
#    ]
# }


import json
import boto3



APPLICABLE_RESOURCES = ["AWS::S3::Bucket"]


def evaluate_compliance(configuration_item, rule_parameters, s3Client):
    """Evaluate complience for each item"""

    # Start as non-compliant
    compliance_type = 'NON_COMPLIANT'
    annotation = "S3 bucket either does NOT have default encryption enabled, " \
                 + "has the wrong TYPE of encryption enabled, or is encrypted " \
                 + "with the wrong KMS key."

    # Check if resource was deleted
    if configuration_item['configurationItemStatus'] == "ResourceDeleted":
        compliance_type = 'NOT_APPLICABLE'
        annotation = "The resource was deleted."

    # Check resource for applicability
    elif configuration_item["resourceType"] not in APPLICABLE_RESOURCES:
        compliance_type = 'NOT_APPLICABLE'
        annotation = "The rule doesn't apply to resources of type " \
                     + configuration_item["resourceType"] + "."

    # Check bucket for default encryption
    else:
        try:
            # TODO: check bucket tags and pass if contains audit:public_okay

            # Encryption isn't in configurationItem so an API call is necessary
            response = s3Client.get_bucket_encryption(
                Bucket=configuration_item["resourceName"]
            )

            if response['ServerSideEncryptionConfiguration']['Rules'][0][
                    'ApplyServerSideEncryptionByDefault']['SSEAlgorithm'] != 'AES256':
                compliance_type = 'NON_COMPLIANT'
                annotation = 'S3 bucket is NOT encrypted with SSE-S3.'
            else:
                compliance_type = 'COMPLIANT'
                annotation = 'S3 bucket is encrypted with SSE-S3.'

        except BaseException as e:
            print(e)
            # If we receive an error, the default encryption flag is not set
            compliance_type = 'NON_COMPLIANT'
            annotation = 'S3 bucket does NOT have default encryption enabled.'

    return {
        "compliance_type": compliance_type,
        "annotation": annotation
    }


def lambda_handler(event, context):
    """Entrypoint"""

    invoking_event = json.loads(event['invokingEvent'])

    # Check for oversized item
    if "configurationItem" in invoking_event:
        configuration_item = invoking_event["configurationItem"]
    elif "configurationItemSummary" in invoking_event:
        configuration_item = invoking_event["configurationItemSummary"]

    # Optional parameters
    rule_parameters = {}
    if 'ruleParameters' in event:
        rule_parameters = json.loads(event['ruleParameters'])


    sts = boto3.client('sts')
    response = sts.assume_role(
        RoleArn=rule_parameters['execution_role'],
        RoleSessionName="ops")

    session = boto3.session.Session(aws_access_key_id=response['Credentials']['AccessKeyId'],
                                    aws_secret_access_key=response['Credentials']['SecretAccessKey'],
                                    aws_session_token=response['Credentials']['SessionToken'])
    config = session.client('config')
    s3Client = session.client('s3')

    evaluation = evaluate_compliance(configuration_item, rule_parameters, s3Client)

    print('Compliance evaluation for %s: %s' %
          (configuration_item['resourceId'], evaluation["compliance_type"]))
    print('Annotation: %s' % (evaluation["annotation"]))

    response = config.put_evaluations(
        Evaluations=[
            {
                'ComplianceResourceType': invoking_event['configurationItem']['resourceType'],
                'ComplianceResourceId': invoking_event['configurationItem']['resourceId'],
                'ComplianceType': evaluation["compliance_type"],
                "Annotation": evaluation["annotation"],
                'OrderingTimestamp': invoking_event['configurationItem']['configurationItemCaptureTime']
            },
        ],
        ResultToken=event['resultToken'])
