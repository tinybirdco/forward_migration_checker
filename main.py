import asyncio
from typing import List, Dict, Optional
from pathlib import Path
import re
from dataclasses import dataclass
import shutil

from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from pydantic import BaseModel


@dataclass
class MigrationCheckResult:
    """Result of a single migration check step"""
    step_name: str
    status: str  # "PASS", "FAIL", "WARNING"
    issues: List[str]
    files_checked: List[str]
    details: str
    auto_fixable: bool = False
    fixed_issues: List[str] = None


class MigrationReport(BaseModel):
    """Complete migration assessment report"""
    version_check: Optional[MigrationCheckResult] = None
    sinks_check: Optional[MigrationCheckResult] = None
    shared_datasources_check: Optional[MigrationCheckResult] = None
    dynamodb_check: Optional[MigrationCheckResult] = None
    endpoint_type_check: Optional[MigrationCheckResult] = None
    include_files_check: Optional[MigrationCheckResult] = None
    summary: str
    migration_plan: str


class TinybirdMigrationAgent:
    def __init__(self, project_path: str = "./tinybird"):
        self.project_path = Path(project_path)
        self.model = GeminiModel('gemini-2.0-flash-001', provider='google-vertex')
        self.agent = Agent(
            self.model,
            result_type=MigrationReport,
            system_prompt="""
            You are an expert Tinybird migration analyst. Your job is to analyze Tinybird Classic projects 
            and determine their compatibility for migration to Tinybird Forward.
            
            You will be provided with the results of various checks performed on the codebase.
            Based on these results, you should:
            1. Identify all migration blockers and issues
            2. Provide specific recommendations for fixing each issue
            3. Generate a comprehensive migration plan
            4. Include warnings about features not available in Forward (like BI connector)
            
            Be thorough, specific, and actionable in your recommendations.
            """
        )

    def backup_file(self, file_path: Path) -> Path:
        """Create a backup of a file before modifying it"""
        backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
        shutil.copy2(file_path, backup_path)
        return backup_path

    def ask_user_confirmation(self, message: str) -> bool:
        """Ask user for confirmation with y/n input"""
        while True:
            response = input(f"{message} (y/n): ").strip().lower()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")

    def find_tinybird_files(self) -> Dict[str, List[Path]]:
        """Find all Tinybird-related files in the project"""
        if not self.project_path.exists():
            return {}
        
        files = {
            'datasources': [],
            'pipes': [],
            'endpoints': [],
            'includes': [],
            'vendor': []
        }
        
        for file_path in self.project_path.rglob("*"):
            if file_path.is_file():
                if file_path.suffix == '.datasource':
                    files['datasources'].append(file_path)
                elif file_path.suffix == '.pipe':
                    files['pipes'].append(file_path)
                elif file_path.suffix == '.endpoint':
                    files['endpoints'].append(file_path)
                elif file_path.suffix == '.incl':
                    files['includes'].append(file_path)
                elif 'vendor' in file_path.parts:
                    files['vendor'].append(file_path)
        
        return files

    def fix_sinks(self, files: Dict[str, List[Path]], issues: List[str]) -> List[str]:
        """Auto-fix sink issues by commenting out sink declarations"""
        fixed_issues = []
        sink_pattern = re.compile(r'(TYPE\s+sink)', re.IGNORECASE)
        
        for pipe_file in files['pipes']:
            try:
                content = pipe_file.read_text()
                if sink_pattern.search(content):
                    # Create backup
                    backup_path = self.backup_file(pipe_file)
                    print(f"📄 Created backup: {backup_path}")
                    
                    # Comment out sink-related lines
                    lines = content.split('\n')
                    modified_lines = []
                    in_sink_section = False
                    
                    for line in lines:
                        if re.match(r'^\s*TYPE\s+sink', line, re.IGNORECASE):
                            modified_lines.append(f"# COMMENTED OUT FOR FORWARD MIGRATION: {line}")
                            in_sink_section = True
                        elif in_sink_section and (line.strip().startswith('EXPORT_') or line.strip().startswith('IMPORT_')):
                            modified_lines.append(f"# COMMENTED OUT FOR FORWARD MIGRATION: {line}")
                        elif in_sink_section and (line.strip() == '' or not line.strip().startswith('#')):
                            if line.strip() and not line.strip().startswith('NODE') and not line.strip().startswith('SQL'):
                                modified_lines.append(f"# COMMENTED OUT FOR FORWARD MIGRATION: {line}")
                            else:
                                modified_lines.append(line)
                                if line.strip() and not line.strip().startswith('#'):
                                    in_sink_section = False
                        else:
                            modified_lines.append(line)
                    
                    # Write modified content
                    pipe_file.write_text('\n'.join(modified_lines))
                    fixed_issues.append(f"Commented out sink declarations in {pipe_file}")
                    
            except Exception as e:
                print(f"❌ Error fixing {pipe_file}: {e}")
        
        return fixed_issues

    def fix_shared_datasources(self, files: Dict[str, List[Path]], issues: List[str]) -> List[str]:
        """Auto-fix shared datasource issues by removing SHARED_WITH declarations"""
        fixed_issues = []
        shared_pattern = re.compile(r'SHARED_WITH\s*>.*?(?=\n\n|\n[A-Z]|\Z)', re.IGNORECASE | re.DOTALL)
        
        for ds_file in files['datasources']:
            try:
                content = ds_file.read_text()
                if re.search(r'SHARED_WITH\s*>', content, re.IGNORECASE):
                    # Create backup
                    backup_path = self.backup_file(ds_file)
                    print(f"📄 Created backup: {backup_path}")
                    
                    # Remove SHARED_WITH section
                    modified_content = shared_pattern.sub('', content)
                    # Clean up extra newlines
                    modified_content = re.sub(r'\n{3,}', '\n\n', modified_content)
                    
                    ds_file.write_text(modified_content)
                    fixed_issues.append(f"Removed SHARED_WITH declaration from {ds_file}")
                    
            except Exception as e:
                print(f"❌ Error fixing {ds_file}: {e}")
        
        # Handle vendor directory
        if files['vendor']:
            vendor_dir = None
            for vendor_file in files['vendor']:
                if 'vendor' in vendor_file.parts:
                    vendor_dir = vendor_file.parent
                    while vendor_dir.name != 'vendor' and vendor_dir.parent != vendor_dir:
                        vendor_dir = vendor_dir.parent
                    break
            
            if vendor_dir and vendor_dir.exists():
                print(f"🗂️ Found vendor directory: {vendor_dir}")
                if self.ask_user_confirmation(f"Remove entire vendor directory '{vendor_dir}'?"):
                    shutil.rmtree(vendor_dir)
                    fixed_issues.append(f"Removed vendor directory {vendor_dir}")
        
        return fixed_issues

    def fix_include_files(self, files: Dict[str, List[Path]], issues: List[str]) -> List[str]:
        """Auto-fix include file issues by commenting out INCLUDE statements"""
        fixed_issues = []
        include_pattern = re.compile(r'(INCLUDE\s+[^\n]+)', re.IGNORECASE)
        
        all_files = files['pipes'] + files['datasources'] + files['endpoints']
        
        for file_path in all_files:
            try:
                content = file_path.read_text()
                if include_pattern.search(content):
                    # Create backup
                    backup_path = self.backup_file(file_path)
                    print(f"📄 Created backup: {backup_path}")
                    
                    # Comment out INCLUDE statements
                    modified_content = include_pattern.sub(r'# COMMENTED OUT FOR FORWARD MIGRATION: \1', content)
                    
                    file_path.write_text(modified_content)
                    fixed_issues.append(f"Commented out INCLUDE statements in {file_path}")
                    
            except Exception as e:
                print(f"❌ Error fixing {file_path}: {e}")
        
        # Handle .incl files
        if files['includes']:
            print(f"📁 Found {len(files['includes'])} include files:")
            for incl_file in files['includes']:
                print(f"  - {incl_file}")
            
            if self.ask_user_confirmation("Move .incl files to a backup directory?"):
                backup_dir = self.project_path / "includes_backup"
                backup_dir.mkdir(exist_ok=True)
                
                for incl_file in files['includes']:
                    backup_path = backup_dir / incl_file.name
                    shutil.move(incl_file, backup_path)
                    fixed_issues.append(f"Moved {incl_file} to {backup_path}")
        
        return fixed_issues

    def fix_endpoint_types(self, files: Dict[str, List[Path]], issues: List[str]) -> List[str]:
        """Auto-fix endpoint type issues by adding missing NODE declarations"""
        fixed_issues = []
        
        for endpoint_file in files['endpoints']:
            try:
                content = endpoint_file.read_text()
                if 'NODE' not in content:
                    # Create backup
                    backup_path = self.backup_file(endpoint_file)
                    print(f"📄 Created backup: {backup_path}")
                    
                    # Add NODE declaration at the beginning
                    lines = content.split('\n')
                    modified_lines = ['NODE endpoint'] + lines
                    
                    endpoint_file.write_text('\n'.join(modified_lines))
                    fixed_issues.append(f"Added missing NODE declaration to {endpoint_file}")
                    
            except Exception as e:
                print(f"❌ Error fixing {endpoint_file}: {e}")
        
        return fixed_issues

    def check_version_tags(self, files: Dict[str, List[Path]]) -> MigrationCheckResult:
        """Check for version tags in the project"""
        issues = []
        files_checked = []
        
        # Look for version tag files
        version_files = list(self.project_path.rglob("*version*"))
        version_files.extend(list(self.project_path.rglob("*.mdc")))
        
        files_checked = [str(f) for f in version_files]
        
        if not version_files:
            issues.append("No version tag files found. Version management is recommended for migration tracking.")
        
        status = "WARNING" if issues else "PASS"
        return MigrationCheckResult(
            step_name="Version Tags Check",
            status=status,
            issues=issues,
            files_checked=files_checked,
            details="Checked for version tag files and version management practices.",
            auto_fixable=False
        )

    def check_sinks(self, files: Dict[str, List[Path]]) -> MigrationCheckResult:
        """Check for sink usage in pipe files"""
        issues = []
        files_checked = []
        sink_pattern = re.compile(r'TYPE\s+sink', re.IGNORECASE)
        
        for pipe_file in files['pipes']:
            files_checked.append(str(pipe_file))
            try:
                content = pipe_file.read_text()
                if sink_pattern.search(content):
                    issues.append(f"Sink found in {pipe_file}: Sinks are not supported in Tinybird Forward")
            except Exception as e:
                issues.append(f"Error reading {pipe_file}: {e}")
        
        result = MigrationCheckResult(
            step_name="Sinks Check",
            status="FAIL" if issues else "PASS",
            issues=issues,
            files_checked=files_checked,
            details="Checked all .pipe files for TYPE sink declarations.",
            auto_fixable=bool(issues)
        )
        
        # Auto-fix if requested
        if issues and result.auto_fixable:
            print(f"\n🔧 Found {len(issues)} sink-related issues that can be auto-fixed:")
            for issue in issues:
                print(f"  - {issue}")
            
            if self.ask_user_confirmation("Would you like to automatically comment out sink declarations?"):
                fixed_issues = self.fix_sinks(files, issues)
                result.fixed_issues = fixed_issues
                if fixed_issues:
                    result.status = "FIXED"
                    print(f"✅ Fixed {len(fixed_issues)} sink issues")
        
        return result

    def check_shared_datasources(self, files: Dict[str, List[Path]]) -> MigrationCheckResult:
        """Check for shared datasources"""
        issues = []
        files_checked = []
        shared_pattern = re.compile(r'SHARED_WITH\s*>', re.IGNORECASE)
        
        # Check for SHARED_WITH in datasource files
        for ds_file in files['datasources']:
            files_checked.append(str(ds_file))
            try:
                content = ds_file.read_text()
                if shared_pattern.search(content):
                    issues.append(f"Shared datasource found in {ds_file}: Shared datasources are not supported in Forward")
            except Exception as e:
                issues.append(f"Error reading {ds_file}: {e}")
        
        # Check for vendor directory
        if files['vendor']:
            issues.append(f"Vendor directory found with {len(files['vendor'])} files: Vendor datasources not supported in Forward")
            files_checked.extend([str(f) for f in files['vendor']])
        
        result = MigrationCheckResult(
            step_name="Shared Datasources Check",
            status="FAIL" if issues else "PASS",
            issues=issues,
            files_checked=files_checked,
            details="Checked for SHARED_WITH declarations and vendor directory.",
            auto_fixable=bool(issues)
        )
        
        # Auto-fix if requested
        if issues and result.auto_fixable:
            print(f"\n🔧 Found {len(issues)} shared datasource issues that can be auto-fixed:")
            for issue in issues:
                print(f"  - {issue}")
            
            if self.ask_user_confirmation("Would you like to automatically remove shared datasource declarations?"):
                fixed_issues = self.fix_shared_datasources(files, issues)
                result.fixed_issues = fixed_issues
                if fixed_issues:
                    result.status = "FIXED"
                    print(f"✅ Fixed {len(fixed_issues)} shared datasource issues")
        
        return result

    def check_dynamodb_connections(self, files: Dict[str, List[Path]]) -> MigrationCheckResult:
        """Check for DynamoDB connections"""
        issues = []
        files_checked = []
        dynamodb_pattern = re.compile(r'IMPORT_SERVICE\s+"?dynamodb"?', re.IGNORECASE)
        
        for ds_file in files['datasources']:
            files_checked.append(str(ds_file))
            try:
                content = ds_file.read_text()
                if dynamodb_pattern.search(content):
                    issues.append(f"DynamoDB connection found in {ds_file}: DynamoDB imports may have limitations in Forward")
            except Exception as e:
                issues.append(f"Error reading {ds_file}: {e}")
        
        status = "WARNING" if issues else "PASS"
        return MigrationCheckResult(
            step_name="DynamoDB Connections Check",
            status=status,
            issues=issues,
            files_checked=files_checked,
            details="Checked all .datasource files for DynamoDB import services.",
            auto_fixable=False  # DynamoDB connections require manual migration strategy
        )

    def check_endpoint_types(self, files: Dict[str, List[Path]]) -> MigrationCheckResult:
        """Check endpoint types"""
        issues = []
        files_checked = []
        
        for endpoint_file in files['endpoints']:
            files_checked.append(str(endpoint_file))
            try:
                content = endpoint_file.read_text()
                # Basic check for endpoint structure
                if 'NODE' not in content:
                    issues.append(f"Endpoint {endpoint_file} may have incorrect structure")
            except Exception as e:
                issues.append(f"Error reading {endpoint_file}: {e}")
        
        result = MigrationCheckResult(
            step_name="Endpoint Types Check",
            status="WARNING" if issues else "PASS",
            issues=issues,
            files_checked=files_checked,
            details="Checked endpoint file structures.",
            auto_fixable=bool(issues)
        )
        
        # Auto-fix if requested
        if issues and result.auto_fixable:
            print(f"\n🔧 Found {len(issues)} endpoint structure issues that can be auto-fixed:")
            for issue in issues:
                print(f"  - {issue}")
            
            if self.ask_user_confirmation("Would you like to automatically add missing NODE declarations?"):
                fixed_issues = self.fix_endpoint_types(files, issues)
                result.fixed_issues = fixed_issues
                if fixed_issues:
                    result.status = "FIXED"
                    print(f"✅ Fixed {len(fixed_issues)} endpoint issues")
        
        return result

    def check_include_files(self, files: Dict[str, List[Path]]) -> MigrationCheckResult:
        """Check for include files usage"""
        issues = []
        files_checked = []
        include_pattern = re.compile(r'INCLUDE\s+', re.IGNORECASE)
        
        all_files = files['pipes'] + files['datasources'] + files['endpoints']
        
        for file_path in all_files:
            files_checked.append(str(file_path))
            try:
                content = file_path.read_text()
                if include_pattern.search(content):
                    issues.append(f"Include statement found in {file_path}: Verify include file compatibility")
            except Exception as e:
                issues.append(f"Error reading {file_path}: {e}")
        
        if files['includes']:
            files_checked.extend([str(f) for f in files['includes']])
            issues.append(f"Found {len(files['includes'])} include files: Review for Forward compatibility")
        
        result = MigrationCheckResult(
            step_name="Include Files Check",
            status="WARNING" if issues else "PASS",
            issues=issues,
            files_checked=files_checked,
            details="Checked for INCLUDE statements and .incl files.",
            auto_fixable=bool(issues)
        )
        
        # Auto-fix if requested
        if issues and result.auto_fixable:
            print(f"\n🔧 Found {len(issues)} include file issues that can be auto-fixed:")
            for issue in issues:
                print(f"  - {issue}")
            
            if self.ask_user_confirmation("Would you like to automatically handle include files?"):
                fixed_issues = self.fix_include_files(files, issues)
                result.fixed_issues = fixed_issues
                if fixed_issues:
                    result.status = "FIXED"
                    print(f"✅ Fixed {len(fixed_issues)} include file issues")
        
        return result

    async def run_migration_check(self) -> MigrationReport:
        """Run the complete migration check process"""
        print("🔍 Starting Tinybird migration compatibility check...")
        
        # Find all relevant files
        files = self.find_tinybird_files()
        print(f"📁 Found {sum(len(f) for f in files.values())} Tinybird files")
        
        # Run all checks
        print("\n📋 Running migration checks:")
        
        print("  1️⃣ Checking version tags...")
        version_check = self.check_version_tags(files)
        print(f"     Status: {version_check.status}")
        
        print("  2️⃣ Checking for sinks...")
        sinks_check = self.check_sinks(files)
        print(f"     Status: {sinks_check.status}")
        
        print("  3️⃣ Checking shared datasources...")
        shared_check = self.check_shared_datasources(files)
        print(f"     Status: {shared_check.status}")
        
        print("  4️⃣ Checking DynamoDB connections...")
        dynamodb_check = self.check_dynamodb_connections(files)
        print(f"     Status: {dynamodb_check.status}")
        
        print("  5️⃣ Checking endpoint types...")
        endpoint_check = self.check_endpoint_types(files)
        print(f"     Status: {endpoint_check.status}")
        
        print("  6️⃣ Checking include files...")
        include_check = self.check_include_files(files)
        print(f"     Status: {include_check.status}")
        
        # Compile results
        all_checks = [
            version_check, sinks_check, shared_check, dynamodb_check, endpoint_check, include_check
        ]
        
        # Generate summary with AI
        print("\n🤖 Generating migration analysis...")
        
        check_results = "\n".join([
            f"**{check.step_name}**: {check.status}\n"
            f"Issues: {'; '.join(check.issues) if check.issues else 'None'}\n"
            f"Files checked: {len(check.files_checked)}\n"
            for check in all_checks
        ])
        
        prompt = f"""
        Based on the following Tinybird migration check results, provide a comprehensive migration assessment:

        {check_results}

        Please provide:
        1. A summary of all issues found
        2. Specific recommendations for each issue
        3. A step-by-step migration plan
        4. Include a warning about BI connector not being available in Tinybird Forward
        
        Focus on actionable items and prioritize blocking issues.
        """
        
        result = await self.agent.run(prompt)
        
        # Create the complete report
        report = MigrationReport(
            version_check=version_check,
            sinks_check=sinks_check,
            shared_datasources_check=shared_check,
            dynamodb_check=dynamodb_check,
            endpoint_type_check=endpoint_check,
            include_files_check=include_check,
            summary=result.data.summary,
            migration_plan=result.data.migration_plan
        )
        
        return report

    def generate_migration_md(self, report: MigrationReport) -> str:
        """Generate a migration.md file content"""
        
        def format_check_section(check: MigrationCheckResult, number: int, name: str) -> str:
            section = f"""### {number}. {name}
**Status**: {check.status}
- **Issues**: {'; '.join(check.issues) if check.issues else 'None'}
- **Files Checked**: {len(check.files_checked)}"""
            
            if check.fixed_issues:
                section += f"""
- **🔧 Auto-Fixes Applied**: {len(check.fixed_issues)} issues were automatically fixed
  - {'; '.join(check.fixed_issues)}"""
            
            return section
        
        md_content = f"""# Tinybird Classic to Forward Migration Plan

## Executive Summary

{report.summary}

## Check Results

{format_check_section(report.version_check, 1, "Version Tags Check")}

{format_check_section(report.sinks_check, 2, "Sinks Check")}

{format_check_section(report.shared_datasources_check, 3, "Shared Datasources Check")}

{format_check_section(report.dynamodb_check, 4, "DynamoDB Connections Check")}

{format_check_section(report.endpoint_type_check, 5, "Endpoint Types Check")}

{format_check_section(report.include_files_check, 6, "Include Files Check")}

## ⚠️ Important Warning

**BI Connector Deprecation**: Please note that the BI Connector feature is not available in Tinybird Forward. If your current setup relies on BI Connector integrations, you will need to migrate to alternative connection methods such as:
- REST API endpoints
- SQL API
- Direct integrations with supported BI tools

## Migration Plan

{report.migration_plan}

## Auto-Fixes Summary

The following issues were automatically fixed during this migration check:

"""
        
        # Add auto-fixes summary
        all_checks = [
            report.version_check, report.sinks_check, report.shared_datasources_check,
            report.dynamodb_check, report.endpoint_type_check, report.include_files_check
        ]
        
        total_fixes = 0
        for check in all_checks:
            if check.fixed_issues:
                total_fixes += len(check.fixed_issues)
                md_content += f"\n**{check.step_name}**:\n"
                for fix in check.fixed_issues:
                    md_content += f"- {fix}\n"
        
        if total_fixes == 0:
            md_content += "No automatic fixes were applied during this run.\n"
        else:
            md_content += f"\n**Total**: {total_fixes} issues were automatically resolved.\n"
        
        md_content += """
## Next Steps

1. Review all identified issues above
2. For any remaining issues, implement the recommended fixes
3. Test your modified configuration in a development environment
4. Contact Tinybird support if you need assistance with specific migration challenges

## Backup Files

If automatic fixes were applied, backup files were created with the `.backup` extension. You can restore the original files if needed:

```bash
# To restore a file from backup
cp file.datasource.backup file.datasource
```

---
*Generated by Tinybird Migration Agent*
"""
        return md_content


async def main():
    """Main function to run the migration check"""
    import sys
    
    # Get project path from command line or use default
    project_path = sys.argv[1] if len(sys.argv) > 1 else "./tinybird"
    
    print(f"🚀 Starting Tinybird migration check for: {project_path}")
    
    # Initialize the agent
    agent = TinybirdMigrationAgent(project_path)
    
    try:
        # Run the migration check
        report = await agent.run_migration_check()
        
        # Generate and save the migration report
        md_content = agent.generate_migration_md(report)
        
        with open("migration.md", "w") as f:
            f.write(md_content)
        
        print("\n✅ Migration check complete!")
        print("📄 Report saved to: migration.md")
        
        # Print summary
        print("\n📊 Summary:")
        print(f"   Version Check: {report.version_check.status}")
        print(f"   Sinks Check: {report.sinks_check.status}")
        print(f"   Shared Datasources: {report.shared_datasources_check.status}")
        print(f"   DynamoDB Connections: {report.dynamodb_check.status}")
        print(f"   Endpoint Types: {report.endpoint_type_check.status}")
        print(f"   Include Files: {report.include_files_check.status}")
        
    except Exception as e:
        print(f"❌ Error during migration check: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 