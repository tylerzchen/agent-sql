#!/usr/bin/env python3
import os

import aws_cdk as cdk

from agent_sql.agent_sql_stack import AgentSqlStack


app = cdk.App()
AgentSqlStack(app, "AgentSqlStack")

app.synth()
