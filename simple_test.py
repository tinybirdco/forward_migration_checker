#!/usr/bin/env python3

"""
Simple validation script for the Tinybird Migration Agent sample project
This script validates the sample project structure without requiring any dependencies.
"""

from pathlib import Path
import re


def check_tinybird_structure():
    """Check the sample Tinybird project structure"""
    print("🧪 Validating Tinybird Migration Agent Sample Project")
    print("=" * 55)
    
    tinybird_path = Path("./tinybird")
    
    if not tinybird_path.exists():
        print("❌ ./tinybird directory not found!")
        return False
    
    print("✅ Found ./tinybird directory")
    
    # Expected files and their patterns
    expected_files = {
        "datasources/sample_data.datasource": [
            r'IMPORT_SERVICE\s+"dynamodb"',
            r'IMPORT_CONNECTION_NAME',
            r'IMPORT_TABLE_ARN'
        ],
        "datasources/shared_data.datasource": [
            r'SHARED_WITH\s*>',
            r'cs_alerting'
        ],
        "pipes/s3_sink_example.pipe": [
            r'TYPE\s+sink',
            r'EXPORT_SERVICE',
            r'EXPORT_BUCKET_URI'
        ],
        "pipes/example_with_include.pipe": [
            r'INCLUDE\s+"includes/common_filters\.incl"'
        ],
        "endpoints/sample_endpoint.endpoint": [
            r'NODE\s+endpoint',
            r'SELECT.*airline'
        ],
        "includes/common_filters.incl": [
            r'WHERE\s+timestamp',
            r'AND\s+status\s*='
        ]
    }
    
    all_good = True
    
    for file_path, patterns in expected_files.items():
        full_path = tinybird_path / file_path
        
        if not full_path.exists():
            print(f"❌ Missing: {file_path}")
            all_good = False
            continue
        
        print(f"✅ Found: {file_path}")
        
        try:
            content = full_path.read_text()
            
            for pattern in patterns:
                if not re.search(pattern, content, re.IGNORECASE):
                    print(f"   ⚠️  Pattern not found: {pattern}")
                else:
                    print(f"   ✅ Pattern found: {pattern}")
            
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
            all_good = False
    
    return all_good


def simulate_migration_check():
    """Simulate what the migration agent would find"""
    print("\n🔍 Simulated Migration Check Results")
    print("=" * 40)
    
    tinybird_path = Path("./tinybird")
    
    # Find all files
    files = {
        'datasources': list(tinybird_path.glob("**/*.datasource")),
        'pipes': list(tinybird_path.glob("**/*.pipe")),
        'endpoints': list(tinybird_path.glob("**/*.endpoint")),
        'includes': list(tinybird_path.glob("**/*.incl")),
    }
    
    print("📁 Files discovered:")
    for category, file_list in files.items():
        print(f"  {category}: {len(file_list)} files")
        for file_path in file_list:
            print(f"    - {file_path}")
    
    # Simulate issue detection
    print("\n🚨 Issues that would be detected:")
    
    issues = []
    auto_fixable = []
    
    # Check for sinks
    for pipe_file in files['pipes']:
        content = pipe_file.read_text()
        if re.search(r'TYPE\s+sink', content, re.IGNORECASE):
            issue = f"Sink found in {pipe_file.name}"
            issues.append(issue)
            auto_fixable.append(issue + " (AUTO-FIXABLE)")
    
    # Check for shared datasources
    for ds_file in files['datasources']:
        content = ds_file.read_text()
        if re.search(r'SHARED_WITH\s*>', content, re.IGNORECASE):
            issue = f"Shared datasource in {ds_file.name}"
            issues.append(issue)
            auto_fixable.append(issue + " (AUTO-FIXABLE)")
    
    # Check for DynamoDB
    for ds_file in files['datasources']:
        content = ds_file.read_text()
        if re.search(r'IMPORT_SERVICE\s+"?dynamodb"?', content, re.IGNORECASE):
            issue = f"DynamoDB connection in {ds_file.name}"
            issues.append(issue)
            # Not auto-fixable
    
    # Check for includes
    all_files = files['pipes'] + files['datasources'] + files['endpoints']
    for file_path in all_files:
        content = file_path.read_text()
        if re.search(r'INCLUDE\s+', content, re.IGNORECASE):
            issue = f"Include statement in {file_path.name}"
            issues.append(issue)
            auto_fixable.append(issue + " (AUTO-FIXABLE)")
    
    if files['includes']:
        issue = f"Found {len(files['includes'])} include files"
        issues.append(issue)
        auto_fixable.append(issue + " (AUTO-FIXABLE)")
    
    # Print results
    for issue in issues:
        if any(af.startswith(issue) for af in auto_fixable):
            print(f"  🔧 {issue} (AUTO-FIXABLE)")
        else:
            print(f"  ⚠️  {issue} (manual fix required)")
    
    print("📊 Summary:")
    print(f"  Total issues: {len(issues)}")
    print(f"  Auto-fixable: {len(auto_fixable)}")
    print(f"  Manual fixes: {len(issues) - len(auto_fixable)}")
    
    return len(issues), len(auto_fixable)


def main():
    """Main test function"""
    
    # Validate structure
    structure_ok = check_tinybird_structure()
    
    if not structure_ok:
        print("\n❌ Sample project structure validation failed!")
        return 1
    
    # Simulate migration check
    total_issues, auto_fixable_issues = simulate_migration_check()
    
    print("\n" + "=" * 55)
    print("✅ Sample project validation completed!")
    
    if total_issues > 0:
        print(f"🎯 Found {total_issues} migration issues ({auto_fixable_issues} auto-fixable)")
        print("💡 This demonstrates the agent's issue detection capabilities.")
    else:
        print("🎯 No migration issues found in sample project.")
    
    print("\n📋 Next Steps:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Set up Google Cloud credentials")
    print("  3. Run full migration check: python main.py")
    
    return 0


if __name__ == "__main__":
    exit(main()) 