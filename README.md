# Tinybird Migration Agent

A powerful AI-powered tool to analyze Tinybird Classic projects and assess their compatibility for migration to Tinybird Forward.

## Features

- **Comprehensive Analysis**: Checks version tags, sinks, shared datasources, DynamoDB connections, endpoint types, and include files
- **AI-Powered Insights**: Uses Google's Vertex AI to generate detailed migration recommendations
- **🔧 Automatic Fixes**: Can automatically fix compatible issues with user confirmation
- **Detailed Reporting**: Generates a comprehensive `migration.md` report with step-by-step migration plans
- **Safe Operations**: Creates backup files before making any changes
- **Easy to Use**: Simple command-line interface with progress indicators

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Google Cloud Authentication**:
   
   You need to authenticate with Google Cloud to use Vertex AI:
   
   ```bash
   # Option 1: Service Account Key
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
   
   # Option 2: gcloud CLI
   gcloud auth application-default login
   
   # Set your project ID
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   ```

## Usage

### Basic Usage

Run the migration check on a Tinybird project:

```bash
python main.py
```

This will analyze the `./tinybird` directory by default.

### Custom Project Path

Specify a custom path to your Tinybird project:

```bash
python main.py /path/to/your/tinybird/project
```

### What the Agent Checks

The migration agent performs these checks:

1. **🏷️ Version Tags**: Looks for version management files (*.mdc, *version*)
2. **🚰 Sinks**: Checks for `TYPE sink` declarations in .pipe files (**Auto-fixable** ✅)
3. **🤝 Shared Datasources**: Looks for `SHARED_WITH` declarations and vendor/ directories (**Auto-fixable** ✅)
4. **🗄️ DynamoDB Connections**: Finds `IMPORT_SERVICE "dynamodb"` declarations
5. **🔗 Endpoint Types**: Validates endpoint file structures (**Auto-fixable** ✅)
6. **📁 Include Files**: Checks for `INCLUDE` statements and .incl files (**Auto-fixable** ✅)

### Auto-Fix Capabilities

The agent can automatically fix the following issues with your confirmation:

#### ✅ **Auto-Fixable Issues**
- **Sinks**: Comments out sink declarations and related export configurations
- **Shared Datasources**: Removes `SHARED_WITH` declarations and offers to remove vendor directories
- **Endpoint Types**: Adds missing `NODE` declarations to endpoint files
- **Include Files**: Comments out `INCLUDE` statements and offers to move .incl files to backup

#### ⚠️ **Manual Fix Required**
- **DynamoDB Connections**: Requires manual migration strategy
- **Version Tags**: Needs manual setup of version management

### Migration Compatibility Rules

#### ❌ **BLOCKING Issues** (Must Fix Before Migration)
- **Sinks**: Not supported in Tinybird Forward (**Auto-fixable** ✅)
- **Shared Datasources**: Not supported in Tinybird Forward (**Auto-fixable** ✅)

#### ⚠️ **WARNING Issues** (Review Required)
- **DynamoDB Connections**: May have limitations in Forward
- **Include Files**: Need to verify compatibility (**Auto-fixable** ✅)
- **Version Tags**: Recommended for migration tracking

#### ℹ️ **Important Notes**
- **BI Connector**: Not available in Tinybird Forward - migrate to REST/SQL APIs

## Auto-Fix Process

When the agent detects fixable issues, it will:

1. **🔍 Identify** the specific problems
2. **💬 Ask for confirmation** before making any changes
3. **📄 Create backup files** with `.backup` extension
4. **🔧 Apply the fixes** safely
5. **📋 Report** what was changed

### Example Auto-Fix Session

```
🔧 Found 2 sink-related issues that can be auto-fixed:
  - Sink found in tinybird/pipes/s3_sink_example.pipe
  - Export configurations detected

Would you like to automatically comment out sink declarations? (y/n): y

📄 Created backup: tinybird/pipes/s3_sink_example.pipe.backup
✅ Fixed 1 sink issues
```

## Output

The agent generates:

1. **Console Output**: Real-time progress and summary
2. **migration.md**: Detailed migration report with:
   - Executive summary
   - Detailed check results
   - Specific recommendations
   - Step-by-step migration plan
   - BI Connector migration warning

## Example Output

```
🚀 Starting Tinybird migration check for: ./tinybird

🔍 Starting Tinybird migration compatibility check...
📁 Found 4 Tinybird files

📋 Running migration checks:
  1️⃣ Checking version tags...
     Status: WARNING
  2️⃣ Checking for sinks...
     Status: FAIL
  3️⃣ Checking shared datasources...
     Status: FAIL
  4️⃣ Checking DynamoDB connections...
     Status: WARNING
  5️⃣ Checking endpoint types...
     Status: PASS
  6️⃣ Checking include files...
     Status: PASS

🤖 Generating migration analysis...

✅ Migration check complete!
📄 Report saved to: migration.md
```

## Sample Project Structure

The included sample project demonstrates common migration issues and auto-fixes:

```
tinybird/
├── datasources/
│   ├── sample_data.datasource      # DynamoDB connection (WARNING)
│   └── shared_data.datasource      # Shared datasource (AUTO-FIXABLE)
├── pipes/
│   ├── s3_sink_example.pipe        # Sink usage (AUTO-FIXABLE)
│   └── example_with_include.pipe   # Include statements (AUTO-FIXABLE)
├── endpoints/
│   └── sample_endpoint.endpoint    # Regular endpoint (PASS)
└── includes/
    └── common_filters.incl         # Include file (AUTO-FIXABLE)
```

## Backup and Recovery

### Backup Files
The agent automatically creates backup files before making changes:
- Original: `file.datasource`
- Backup: `file.datasource.backup`

### Restoring from Backup
To restore original files:

```bash
# Restore a specific file
cp tinybird/datasources/shared_data.datasource.backup tinybird/datasources/shared_data.datasource

# Restore all files from backups (be careful!)
find tinybird/ -name "*.backup" | while read backup; do
    original="${backup%.backup}"
    cp "$backup" "$original"
done
```

### Include Files Backup
Include files are moved to `tinybird/includes_backup/` directory for safe keeping.

## Troubleshooting

### Authentication Issues
- Ensure Google Cloud credentials are properly set
- Verify your project has Vertex AI API enabled
- Check that your service account has the necessary permissions

### File Permission Issues
- Ensure the agent has read access to your Tinybird project directory
- Check that it can write to the current directory for the migration.md report

### No Tinybird Files Found
- Verify the path to your Tinybird project is correct
- Ensure your project has .datasource, .pipe, or .endpoint files

## Contributing

Feel free to contribute improvements or report issues. The agent is designed to be extensible for additional migration checks.

## License

MIT License - see LICENSE file for details. 