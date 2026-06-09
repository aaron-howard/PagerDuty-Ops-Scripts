#!/usr/bin/env python3
"""
PagerDuty Scripts Demo - Sample Output Generator

This script demonstrates what the output of various PagerDuty operations scripts
would look like using sample data. This is useful for showcasing functionality
without requiring actual PagerDuty API access.
"""

import json
from prettytable import PrettyTable
from tabulate import tabulate

def demo_export_ids():
    """Demonstrate the export IDs script output."""
    print("=== PagerDuty Export IDs Demo ===")
    print("Command: python pd_export_ids.py --format table")
    print()
    
    # Sample data
    sample_data = [
        {
            "Team ID": "P123ABC",
            "Team Name": "Infrastructure Team",
            "Schedule ID": "SCH456DEF",
            "Schedule Name": "Primary On-Call SCH",
            "Escalation Policy ID": "EP789GHI",
            "Escalation Policy Name": "Critical Alerts EP",
            "Service ID": "SVC101JKL",
            "Service Name": "Database Monitoring SVC",
            "Webhook ID": "WH202MNO",
            "Webhook Name": "Slack Integration"
        },
        {
            "Team ID": "P123ABC",
            "Team Name": "Infrastructure Team",
            "Schedule ID": "SCH303PQR",
            "Schedule Name": "Secondary On-Call SCH",
            "Escalation Policy ID": "",
            "Escalation Policy Name": "",
            "Service ID": "SVC404STU",
            "Service Name": "Server Monitoring SVC",
            "Webhook ID": "",
            "Webhook Name": ""
        },
        {
            "Team ID": "P555VWX",
            "Team Name": "Application Team",
            "Schedule ID": "SCH666YZA",
            "Schedule Name": "App Support SCH",
            "Escalation Policy ID": "EP777BCD",
            "Escalation Policy Name": "Application Alerts EP",
            "Service ID": "SVC888EFG",
            "Service Name": "API Gateway SVC",
            "Webhook ID": "WH999HIJ",
            "Webhook Name": "Teams Integration"
        }
    ]
    
    table = PrettyTable()
    table.field_names = list(sample_data[0].keys())
    for row in sample_data:
        table.add_row(list(row.values()))
    
    print(table)
    print()

def demo_team_members():
    """Demonstrate the team members script output."""
    print("=== Team Members Demo ===")
    print("Command: python pd_get_teams_user_role.py")
    print()
    
    sample_members = [
        ["P123ABC", "user", "john.doe@company.com", "manager"],
        ["P456DEF", "user", "jane.smith@company.com", "responder"],
        ["P789GHI", "user", "bob.wilson@company.com", "responder"],
        ["P101JKL", "user", "alice.brown@company.com", "observer"]
    ]
    
    print(tabulate(sample_members, headers=["ID", "Type", "Summary", "Role"], tablefmt="github"))
    print()

def demo_service_updates():
    """Demonstrate the service name update script output."""
    print("=== Service Name Updates Demo ===")
    print("Command: python pd_update_service_names.py --dry-run --list")
    print()
    
    sample_services = [
        ["SVC101JKL", "Database Monitoring", "Database Monitoring SVC", "✅ Already has SVC suffix"],
        ["SVC202MNO", "Server Monitoring", "Server Monitoring SVC", "✅ Already has SVC suffix"],
        ["SVC303PQR", "API Gateway", "API Gateway SVC", "✅ Already has SVC suffix"],
        ["SVC404STU", "Load Balancer", "Load Balancer SVC", "✅ Already has SVC suffix"],
        ["SVC505VWX", "Cache Service", "Cache Service SVC", "✅ Already has SVC suffix"]
    ]
    
    print(tabulate(sample_services, headers=["Service ID", "Current Name", "New Name", "Status"], tablefmt="github"))
    print()

def demo_schedule_updates():
    """Demonstrate the schedule name update script output."""
    print("=== Schedule Name Updates Demo ===")
    print("Command: python pd_update_schedule_names.py --dry-run --list")
    print()
    
    sample_schedules = [
        ["SCH101JKL", "Primary On-Call", "Primary On-Call SCH", "✅ Already has SCH suffix"],
        ["SCH202MNO", "Secondary On-Call", "Secondary On-Call SCH", "✅ Already has SCH suffix"],
        ["SCH303PQR", "Weekend Coverage", "Weekend Coverage SCH", "✅ Already has SCH suffix"],
        ["SCH404STU", "Holiday Schedule", "Holiday Schedule SCH", "✅ Already has SCH suffix"]
    ]
    
    print(tabulate(sample_schedules, headers=["Schedule ID", "Current Name", "New Name", "Status"], tablefmt="github"))
    print()

def demo_json_export():
    """Demonstrate JSON export format."""
    print("=== JSON Export Demo ===")
    print("Command: python pd_export_ids.py --format json")
    print()
    
    sample_json = {
        "teams": [
            {
                "id": "P123ABC",
                "name": "Infrastructure Team",
                "schedules": [
                    {"id": "SCH456DEF", "name": "Primary On-Call SCH"}
                ],
                "services": [
                    {"id": "SVC101JKL", "name": "Database Monitoring SVC"}
                ]
            }
        ],
        "export_timestamp": "2024-01-15T10:30:00Z",
        "total_teams": 1,
        "total_schedules": 1,
        "total_services": 1
    }
    
    print(json.dumps(sample_json, indent=2))
    print()


def demo_compliance_exports():
    """Sample rows shaped like pd_export_log_entries / pd_export_change_events CSV."""
    print("=== Compliance export — log entries (sample CSV shape) ===")
    print("Command: python pd_export_log_entries.py --since ... --until ... -f csv -o log_entries.csv")
    print()
    log_rows = [
        [
            "Q02JTSNZWHSEKV",
            "2026-05-10T14:22:01Z",
            "annotate_log_entry",
            "Added note: rolling restart complete",
            "PXPGF42",
            "Jane Smith",
            "PIJ90N7",
            "API Gateway",
            "PT4KHLK",
            "12345",
        ],
        [
            "Q02JTSNZWHSEKW",
            "2026-05-10T14:05:00Z",
            "resolve_log_entry",
            "Resolved through the web UI",
            "PXPGF42",
            "Jane Smith",
            "PIJ90N7",
            "API Gateway",
            "PT4KHLK",
            "12345",
        ],
    ]
    print(
        tabulate(
            log_rows,
            headers=[
                "id",
                "created_at",
                "resource_type",
                "summary",
                "agent_id",
                "agent_summary",
                "service_id",
                "service_summary",
                "incident_id",
                "incident_number",
            ],
            tablefmt="github",
        )
    )
    print()
    print("=== Compliance export — change events (sample CSV shape) ===")
    print("Command: python pd_export_change_events.py --since ... --until ... -f csv -o changes.csv")
    print()
    chg_rows = [
        [
            "CHG01ABCDEF",
            "change_event",
            "Deployed api-gateway v2.3.1",
            "2026-05-10T13:00:00Z",
            "jenkins-prod",
            "PIJ90N7",
        ],
    ]
    print(
        tabulate(
            chg_rows,
            headers=["id", "type", "summary", "timestamp", "source", "service_ids"],
            tablefmt="github",
        )
    )
    print()


def main():
    """Run all demo functions."""
    print("🚀 PagerDuty Operations Scripts - Demo Output")
    print("=" * 50)
    print()
    
    demo_export_ids()
    demo_team_members()
    demo_service_updates()
    demo_schedule_updates()
    demo_json_export()
    demo_compliance_exports()

    print("=" * 50)
    print("📋 Summary of Available Scripts:")
    print("• pd_export_ids.py - Export all PagerDuty objects with IDs")
    print("• pd_audit_export.py / pd_export_log_entries.py / pd_export_change_events.py - Compliance exports")
    print("• pd_update_service_names.py - Standardize service naming")
    print("• pd_update_schedule_names.py - Standardize schedule naming")
    print("• pd_update_escalation_policy_names.py - Standardize policy naming")
    print("• pd_get_teams_user_role.py - List team members and roles")
    print("• pd_update_team_roles.py - Interactive role management")
    print("• pd_remove_team_members.py - Remove team members")
    print("• update_service_notifications.py - Update notification settings")
    print()
    print("🔐 Security Features:")
    print("• Secure token input using getpass")
    print("• Environment variable support")
    print("• Request timeouts and error handling")
    print("• Dry-run capabilities for safe testing")
    print()
    print("📖 For detailed usage instructions, see README.md")

if __name__ == "__main__":
    main()
