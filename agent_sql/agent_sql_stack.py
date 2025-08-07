from aws_cdk import (
    Duration,
    Stack,
    CfnOutput
)
from constructs import Construct
import aws_cdk.aws_rds as rds
import aws_cdk.aws_ec2 as ec2

class AgentSqlStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC initialization
        vpc = ec2.Vpc(
            self, 
            "AgentSQLVpc", 
            max_azs=2, 
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ]
        )
        
        # Aurora Serverless v2 initialization
        cluster = rds.DatabaseCluster(
            self,
            "AgentSQLDatabase",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_15_4
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            writer=rds.ClusterInstance.provisioned("writer"),
            serverless_v2_min_capacity=0.5,
            serverless_v2_max_capacity=10,
            storage_encrypted=True,
            backup=rds.BackupProps(retention=Duration.days(7)),
            deletion_protection=True,
        )

        # TODO: Add security groups and RDS proxy to instance/vpc
