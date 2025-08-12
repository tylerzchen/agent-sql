from aws_cdk import (
    Duration,
    Stack,
    CfnOutput
)
from constructs import Construct
import aws_cdk.aws_rds as rds
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_apigateway as apigw

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

        # Security group for Aurora Serverless v2
        aurora_security_group = ec2.SecurityGroup(self, "AuroraSecurityGroup", vpc=vpc, allow_all_outbound=False)

        # Security group for RDS proxy
        rds_proxy_security_group = ec2.SecurityGroup(self, "RDSProxySecurityGroup", vpc=vpc, allow_all_outbound=False)

        # Security group for Lambda function
        lambda_security_group = ec2.SecurityGroup(self, "LambdaSecurityGroup", vpc=vpc, allow_all_outbound=True)

        # Security group rules: Lambda -> RDS proxy
        rds_proxy_security_group.add_ingress_rule(peer=lambda_security_group, connection=ec2.Port.tcp(5432))

        # Security group rules: RDS proxy -> Aurora Serverless v2
        aurora_security_group.add_ingress_rule(peer=rds_proxy_security_group, connection=ec2.Port.tcp(5432))
        
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
            writer=rds.ClusterInstance.serverless_v2("writer"),
            serverless_v2_min_capacity=0.5,
            serverless_v2_max_capacity=10,
            storage_encrypted=True,
            backup=rds.BackupProps(retention=Duration.days(7)),
            deletion_protection=False,
            security_groups=[aurora_security_group],
            enable_data_api=True
        )

        # RDS proxy initialization
        proxy = rds.DatabaseProxy(
            self,
            "AgentSQLProxy",
            proxy_target=rds.ProxyTarget.from_cluster(cluster),
            secrets=[cluster.secret],
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[rds_proxy_security_group],
            db_proxy_name="agent-sql-proxy",
            require_tls=True,
            idle_client_timeout=Duration.minutes(30),
            max_connections_percent=100,
            max_idle_connections_percent=50,
            debug_logging=False
        )