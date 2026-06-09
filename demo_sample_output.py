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

def demo_bulk_rename_resources():
    """Demonstrate generic bulk rename (services / schedules / escalation policies)."""
    print("=== Bulk resource rename demo ===")
    print("Command: python pd_rename_resources.py --resource services --suffix \" SVC\" --dry-run")
    print()
    sample = [
        ["SVC101JKL", "Database Monitoring", "Would add suffix if missing"],
        ["SVC202MNO", "Server Monitoring SVC", "Already ends with affix — skipped"],
        ["SVC303PQR", "API Gateway", "Would become 'API Gateway SVC' (if suffix is ' SVC')"],
    ]
    print(tabulate(sample, headers=["Resource ID", "Current name", "Note"], tablefmt="github"))
    print()

def demo_flat_directory():
    """Demonstrate flat user/team list scripts."""
    print("=== Flat directory exports ===")
    print("Commands: python pd_list_users.py -f csv")
    print("          python pd_list_teams.py --filter Infra -f json")
    print()
    users = [
        ["PABC123", "Ada Lovelace", "ada@example.com", "user", "SRE"],
        ["PDEF456", "Grace Hopper", "grace@example.com", "admin", "Platform"],
    ]
    print(tabulate(users, headers=["id", "name", "email", "role", "job_title"], tablefmt="github"))
    print()

def demo_incidents_export():
    """Demonstrate incident list/export for ops pipelines."""
    print("=== Incident export demo ===")
    print(
        "Command: python pd_list_incidents.py --since 2026-01-01T00:00:00Z "
        "--status triggered,acknowledged -f csv -o incidents.csv"
    )
    print()
    rows = [
        [
            "Q1ABCDEF",
            "42",
            "Elevated error rate on checkout",
            "triggered",
            "high",
            "2026-01-15T14:22:00Z",
            "https://example.pagerduty.com/incidents/Q1ABCDEF",
            "PABCD12",
            "Checkout API",
            "Ada Lovelace (PUSER01)",
        ],
        [
            "Q2ABCDEF",
            "41",
            "Disk space low on db-primary",
            "acknowledged",
            "low",
            "2026-01-15T13:05:00Z",
            "https://example.pagerduty.com/incidents/Q2ABCDEF",
            "PABCD34",
            "Database",
            "Grace Hopper (PUSER02) | On-Call Escalation (PXYZ99)",
        ],
    ]
    headers = [
        "id",
        "incident_number",
        "title",
        "status",
        "urgency",
        "created_at",
        "html_url",
        "service_id",
        "service_summary",
        "assignees",
    ]
    print(tabulate(rows, headers=headers, tablefmt="github"))
    print()

def demo_eo_and_alert_grouping():
    """Event Orchestration export/apply workflow and alert grouping CRUD pointers."""
    print("=== Event Orchestration + Alert Grouping ===")
    print("Export rules to git:")
    print("  python pd_event_orchestration_rules.py -o event_orchestrations/")
    print("Diff live vs JSON (no writes):")
    print("  python pd_apply_event_orchestration_rules.py -d event_orchestrations/")
    print("Apply after review (requires -y):")
    print("  python pd_apply_event_orchestration_rules.py -d event_orchestrations/ --apply -y")
    print()
    print("Alert grouping: list / get-json / create-json / update-json / delete / attach-from-CSV")
    print("  python pd_alert_grouping.py --list")
    print("  python pd_alert_grouping.py --get-json PZC4OM1 -o setting.json")
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

def main():
    """Run all demo functions."""
    print("🚀 PagerDuty Operations Scripts - Demo Output")
    print("=" * 50)
    print()
    
    demo_export_ids()
    demo_team_members()
    demo_bulk_rename_resources()
    demo_flat_directory()
    demo_incidents_export()
    demo_eo_and_alert_grouping()
    demo_json_export()
    
    print("=" * 50)
    print("📋 Summary of Available Scripts:")
    print("• pd_export_ids.py - Export all PagerDuty objects with IDs (relational)")
    print("• pd_rename_resources.py - Configurable prefix/suffix renames (services, schedules, EPs)")
    print("• pd_list_users.py / pd_list_teams.py - Flat user and team directory (table/csv/json)")
    print("• pd_list_incidents.py - Filtered incident export for ticketing / SIEM (table/csv/json)")
    print("• pd_event_orchestration_rules.py / pd_apply_event_orchestration_rules.py - EO export, diff, apply (-y)")
    print("• pd_alert_grouping.py - Alert grouping list, CRUD JSON, CSV attach")
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
