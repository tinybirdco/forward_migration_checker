# Project Scope
This project provides scripts and checks to automate and validate the migration of Tinybird workspaces from Classic to Forward. It ensures that all workspace resources (pipes, datasources, and workflows) are compatible with Forward by:
- Detecting unsupported features such as DynamoDB connections, sink pipes, and version tags.
- Identifying shared datasources and vendor-specific resources.
- Providing actionable recommendations to resolve migration blockers.

# Scripts to Migrate Workspaces from Tinybird Classic to Forward

## Objective
The objective of those scripts is to be able to make the migration from Tinybird Classic to Forward easily. The limitations to migrate to forward are in [this doc](https://www.tinybird.co/docs/forward/get-started/migrate#considerations-before-migrating) so the scripts were created to cover the cases described on that document.

## Check DynamoDB Connection
Done in the script tb_checks_to_forward.sh and it uses the forward_check_if_possible_migration.sh that basically looks for a pattern in a file indicated by the user. So this last script is used for Dynamo connection as well as for the sinks.

- Folder: datasources/
- Pattern: 'IMPORT_SERVICE "dynamodb"'

## Check Sinks
Same as is explained before:

- Folder: pipes/
- Pattern: "TYPE sinks"

## Check Shared Datasources

Since the project structure is that the shared data sources are saved in the vendors/ folder, what the code does in the tb_checks_to_forward.sh script is to look fot he vendor folder. If it doesn't exit, that means there are no shared data source.