import aws_cdk as core
import aws_cdk.assertions as assertions

from agent_sql.agent_sql_stack import AgentSqlStack

# example tests. To run these tests, uncomment this file along with the example
# resource in agent_sql/agent_sql_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AgentSqlStack(app, "agent-sql")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
