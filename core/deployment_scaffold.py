"""DeploymentScaffold: generates GitHub Actions workflow and CloudFormation stubs."""

from pathlib import Path


DEPLOY_YML = """\
name: Deploy

on:
  push:
    branches:
      - main

env:
  AWS_DEFAULT_REGION: us-east-1

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{{{ secrets.AWS_ACCESS_KEY_ID }}}}
          aws-secret-access-key: ${{{{ secrets.AWS_SECRET_ACCESS_KEY }}}}
          aws-region: ${{{{ secrets.AWS_DEFAULT_REGION }}}}

      - name: Deploy ECS stack
        run: |
          aws cloudformation deploy \\
            --template-file infra/cloudformation/ecs.yml \\
            --stack-name {crew_name}-ecs \\
            --capabilities CAPABILITY_NAMED_IAM

      - name: Deploy ALB/WAF stack
        run: |
          aws cloudformation deploy \\
            --template-file infra/cloudformation/alb-waf.yml \\
            --stack-name {crew_name}-alb-waf \\
            --capabilities CAPABILITY_NAMED_IAM

      - name: Deploy S3 stack
        run: |
          aws cloudformation deploy \\
            --template-file infra/cloudformation/s3.yml \\
            --stack-name {crew_name}-s3

      - name: Deploy DynamoDB stack
        run: |
          aws cloudformation deploy \\
            --template-file infra/cloudformation/dynamodb.yml \\
            --stack-name {crew_name}-dynamodb

      - name: Deploy RDS stack
        run: |
          aws cloudformation deploy \\
            --template-file infra/cloudformation/rds.yml \\
            --stack-name {crew_name}-rds \\
            --capabilities CAPABILITY_NAMED_IAM
"""

ECS_YML = """\
AWSTemplateFormatVersion: "2010-09-09"
Description: ECS cluster and service for {crew_name}

Resources:
  ECSCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: {crew_name}-cluster
"""

ALB_WAF_YML = """\
AWSTemplateFormatVersion: "2010-09-09"
Description: Application Load Balancer and WAF for {crew_name}

Resources:
  LoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Name: {crew_name}-alb
      Scheme: internet-facing
      Type: application

  WebACL:
    Type: AWS::WAFv2::WebACL
    Properties:
      Name: {crew_name}-waf
      Scope: REGIONAL
      DefaultAction:
        Allow: {{}}
      VisibilityConfig:
        SampledRequestsEnabled: true
        CloudWatchMetricsEnabled: true
        MetricName: {crew_name}-waf-metric
      Rules: []
"""

S3_YML = """\
AWSTemplateFormatVersion: "2010-09-09"
Description: S3 buckets for {crew_name}

Resources:
  AssetsBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: {crew_name}-assets
"""

DYNAMODB_YML = """\
AWSTemplateFormatVersion: "2010-09-09"
Description: DynamoDB tables for {crew_name}

Resources:
  MainTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: {crew_name}-main
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: pk
          AttributeType: S
        - AttributeName: sk
          AttributeType: S
      KeySchema:
        - AttributeName: pk
          KeyType: HASH
        - AttributeName: sk
          KeyType: RANGE
"""

RDS_YML = """\
AWSTemplateFormatVersion: "2010-09-09"
Description: RDS instance for {crew_name}

Resources:
  DBInstance:
    Type: AWS::RDS::DBInstance
    Properties:
      DBInstanceIdentifier: {crew_name}-db
      DBInstanceClass: db.t3.micro
      Engine: postgres
      MasterUsername: admin
      MasterUserPassword: "{{{{resolve:secretsmanager:{crew_name}-db-secret:SecretString:password}}}}"
      AllocatedStorage: "20"
"""


class DeploymentScaffold:
    def generate(self, project_path: Path, crew_name: str) -> None:
        """Write all six scaffold files into the project directory."""
        files = {
            ".github/workflows/deploy.yml": DEPLOY_YML.format(crew_name=crew_name),
            "infra/cloudformation/ecs.yml": ECS_YML.format(crew_name=crew_name),
            "infra/cloudformation/alb-waf.yml": ALB_WAF_YML.format(crew_name=crew_name),
            "infra/cloudformation/s3.yml": S3_YML.format(crew_name=crew_name),
            "infra/cloudformation/dynamodb.yml": DYNAMODB_YML.format(crew_name=crew_name),
            "infra/cloudformation/rds.yml": RDS_YML.format(crew_name=crew_name),
        }

        for relative_path, content in files.items():
            target = project_path / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
