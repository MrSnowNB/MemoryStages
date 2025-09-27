# TUI Operations Dashboard Guide

**Stage 5 scope only. Do not implement beyond this file's responsibilities.**

Complete guide for operating the MemoryStages Terminal User Interface (TUI) dashboard - secure administrative interface for monitoring and maintenance.

---

## Overview

The TUI Operations Dashboard provides secure administrative access to MemoryStages system monitoring, manual triggers, and maintenance tools. Built with Textual for a modern terminal interface, it ensures:

- **Secure authentication** with token-based access control
- **Role-appropriate permissions** for different administrative levels
- **Comprehensive audit logging** of all dashboard operations
- **Privacy-aware data viewing** with automatic sensitive data protection

---

## Prerequisites

### System Requirements
- Python 3.10+
- Textual library installed (`pip install textual`)
- Terminal with UTF-8 support and 80x24 minimum size

### Configuration (Required)

```bash
# Enable dashboard
DASHBOARD_ENABLED=true

# Set authentication token (REQUIRED)
DASHBOARD_AUTH_TOKEN=your_secure_admin_token_here

# Optional: Enable sensitive data operations
DASHBOARD_SENSITIVE_ACCESS=true

# Optional: Enable maintenance tools
DASHBOARD_MAINTENANCE_MODE=true
```

### Feature Compatibility Matrix

| Setting | Basic Monitoring | Manual Triggers | Log Viewer | Sensitive Data | Maintenance |
|---------|-----------------|----------------|------------|----------------|-------------|
| Default (no flags) | ⚠️  Realm (authenticated, basic access)
| `SENSITIVE_ACCESS=true` | ✅ Basic access + view sensitive logs | ❌ No change | ✅ Explicit reveal | ✅ Full sensitive operations | ❌ No change |
| `MAINTENANCE_MODE=true` | ✅ Basic access | ✅ Basic triggers | ✅ Basic logs | ✅ If SENSITIVE_ACCESS=true | ✅ Full maintenance |

---

## Authentication Process

### Starting the Dashboard
```bash
# From project root
export DASHBOARD_ENABLED=true
export DASHBOARD_AUTH_TOKEN=admin123
python scripts/run_dashboard.py
```

**Authentication Screen:**
```
🔐 MemoryStages Operations Dashboard
Please authenticate to continue

Auth Token: [input field]
[Authenticate]  [ESC to cancel]
```

### Token Validation
- Tokens are validated securely with constant-time comparison
- Authentication attempts are logged to episodic events
- Invalid attempts display error and allow retry
- Press ESC to cancel authentication

### Successful Login
- Dashboard switches to main monitoring screen
- Authentication event logged
- All subsequent operations are audit logged

---

## Main Dashboard Interface

```
📊 MemoryStages Operations Dashboard
Administrative controls and monitoring

┌─ System Health ──────────┐  ┌─ Manual Triggers ──────┐  ┌─ Log Viewer ──────────┐
│ ● Database: Ready       │  │ [Run Heartbeat]       │  │ [View Recent Events]  │
│ ● Vector Store: Ready   │  │ [Scan for Drift]       │  │ [Search Events]       │
│ ● Features: Enabled     │  │ [View Approvals]       │  └───────────────────────┘
└─────────────────────────┘  └───────────────────────┘

Press ESC to return to auth, Q to quit
```

### System Health Section
Displays current system status:
- **Database**: Connection status and readiness
- **Vector Store**: Availability and health
- **Features**: Current flag configuration summary

### Manual Triggers Section
Provides buttons for administrative operations:
- **Run Heartbeat**: Manually trigger heartbeat cycle
- **Scan for Drift**: Manually trigger drift detection
- **View Approvals**: Access pending approval management

### Log Viewer Section
Access to audit and event logging:
- **View Recent Events**: Browse recent system events with privacy indicators (🔐 sensitive, 📄 normal)
- **View Audit Summary**: Summary statistics including operation types, actor activity, time-based metrics
- **Search Events**: Full-text search through event logs with date ranges, actor filtering, operation type filtering

---

## Manual Trigger Operations

### Heartbeat Trigger
```bash
DASHBOARD_SENSITIVE_ACCESS=true  # Recommended
DASHBOARD_MAINTENANCE_MODE=true  # Recommended
```

**Process:**
1. Click "Run Heartbeat" button
2. Dialog confirms operation
3. System executes heartbeat cycle
4. Results notification shows status
5. All operations logged to episodic events

**What it does:**
- Executes drift detection scan
- Applies approved corrections
- Updates heartbeat last-run timestamp
- Generates comprehensive audit trail

### Drift Scan Trigger
**Process:**
1. Click "Scan for Drift"
2. Dialog confirms scan parameters
3. System scans for data consistency issues
4. Results show potential corrections needed
5. All findings logged

### Approval Management
**Process:**
1. Click "View Pending Approvals"
2. Shows count of pending approvals
3. Provides approve/reject interface
4. Each decision logged with admin justification
5. Updates workflow state

---

## Event Log Viewer Operations

### Recent Events View
**Purpose:** Quick overview of recent system activity

**Access:**
- Click "View Recent Events"
- Displays last 10 system events
- Includes operation types, timestamps, and high-level details

**Privacy:** Sensitive operation payloads automatically redacted

### Event Search
**Purpose:** Full investigation of system activity

**Access:**
- Click "Search Events"
- Supports multiple search criteria:
  - Date range filtering
  - Actor/user filtering
  - Operation type filtering
  - Full-text content search

**Search Examples:**
```
# Find all approval operations
actor:*approval*

# Find operations by specific user
actor:admin

# Find events in last hour
timestamp>=-1hour

# Find sensitive data access
action:*sensitive*
```

### Sensitive Data Handling

**Default Behavior:**
- All potentially sensitive fields automatically redacted
- Clear indicators show "[REDACTED]" for protected data
- Access attempts logged

**Explicit Reveal:**
- Requires `DASHBOARD_SENSITIVE_ACCESS=true`
- Shows confirmation dialog with admin reason requirement
- Logs sensitive data access as high-privilege event
- Reason stored in audit trail

---

## Maintenance Tools (Advanced)

**Requires:** `DASHBOARD_MAINTENANCE_MODE=true`

### Available Tools
- **Vector Index Rebuild**: Recreate vector store from SQLite state
- **System Health Check**: Comprehensive integrity validation
- **Data Backup**: Create system state snapshots
- **Configuration Audit**: Validate all feature flag combinations

### Safety Controls

**Confirmation Required:**
- All maintenance operations show impact warnings
- "Are you sure?" prompts prevent accidental execution
- Confirmation tokens required for destructive operations

**Rollback Capability:**
- Non-destructive operations can be undone
- Backup creation before destructive changes
- Clear audit trail of all modifications

**Logging:**
- All maintenance actions comprehensively logged
- Before/after state captured
- Admin user and timestamp recorded

---

## Security and Audit

### Authentication Security
- **No persistent sessions** - authentication required per operation
- **Token exposure prevention** - tokens never logged or cached
- **Brute force protection** - authentication attempts rate limited and logged
- **Session timeout** - automatic logout after period of inactivity

### Operational Auditing
- **All dashboard operations logged** to episodic events
- **Command correlation IDs** for tracking user action chains
- **Admin user identification** in all audit entries
- **Sensitive operation flags** highlighting high-impact actions

### Data Privacy Controls
- **Automatic sensitive data detection** and redaction
- **Compliance-level access logging** for privacy audits
- **PII and sensitive field scanners** with configurable rules
- **Tamper-evident audit trail** using cryptographic hashing

---

## Configuration Examples

### Basic Administrative Access
```bash
# Enable dashboard with basic admin access
DASHBOARD_ENABLED=true
DASHBOARD_AUTH_TOKEN=admin_secure_token_2025
DASHBOARD_TYPE=tui
```

### Full Administrative Access
```bash
# Enable dashboard with sensitive data and maintenance access
DASHBOARD_ENABLED=true
DASHBOARD_AUTH_TOKEN=admin_secure_token_2025
DASHBOARD_SENSITIVE_ACCESS=true
DASHBOARD_MAINTENANCE_MODE=true
```

### Audit-Only Access
```bash
# Enable dashboard for viewing logs only
DASHBOARD_ENABLED=true
DASHBOARD_AUTH_TOKEN=auditor_token_2025
# SENSITIVE_ACCESS=false (default)
# MAINTENANCE_MODE=false (default)
```

---

## Troubleshooting

### Common Issues

**"Dashboard feature disabled"**
```
Solution: Set DASHBOARD_ENABLED=true
```

**"DASHBOARD_AUTH_TOKEN must be set"**
```
Solution: Set DASHBOARD_AUTH_TOKEN environment variable
```

**"Textual library not found"**
```
Solution: pip install textual==0.38.1
```

**"Terminal size too small"**
```
Solution: Resize terminal to at least 80x24 characters
```

### Authentication Issues

**Token repeatedly rejected:**
- Check DASHBOARD_AUTH_TOKEN is correctly set
- Verify no extra spaces in token
- Check authentication attempts logged in system logs

**Dashboard exits immediately:**
- Verify DASHBOARD_ENABLED=true
- Check configuration validation errors in logs

### Operational Issues

**Triggers show disabled:**
- Check corresponding feature flags (HEARTBEAT_ENABLED, etc.)
- Verify feature interactions in config validation

**Empty log views:**
- Check episodic event table has recent entries
- Verify privacy filters aren't hiding all results

---

## Keyboard Shortcuts

### Global Shortcuts
- **`Q`**: Quit dashboard completely
- **`ESC`**: Return to authentication screen

### Navigation
- **`Tab`**: Move between UI elements
- **`Arrow Keys`**: Navigate within interfaces
- **`Enter`**: Activate selected button/interface

### Modal Dialogs
- **`Y`**: Confirm operation
- **`N`**: Cancel operation
- **`ESC`**: Close dialog without action

---

## Best Practices

### Daily Operations
1. Start dashboard with appropriate permissions
2. Review system health status
3. Check pending approvals regularly
4. Review recent event logs for anomalies

### Maintenance Windows
1. Schedule maintenance during low-activity periods
2. Create backups before major operations
3. Test operations in development environment first
4. Document maintenance activities

### Security Practices
- Use strong, unique authentication tokens
- Rotate tokens regularly
- Limit `SENSITIVE_ACCESS` to essential personnel
- Review audit logs weekly for suspicious activity
- Log out after administrative sessions

### Performance Monitoring
- Monitor dashboard response times
- Watch for audit log file size growth
- Review trigger operation durations
- Track approval queue lengths

---

## Integration with System Features

### Stage 1 Core Operations
- Dashboard accesses via existing DAO interfaces
- Respects `sensitive` data flags
- Tombstones properly filtered from displays

### Stage 2 Vector Operations
- Index rebuild triggers use existing rebuild_index.py
- Vector health checks coordinate with vector store status
- Search operations respect feature enablement

### Stage 3 Heartbeat/Corrections
- Manual triggers invoke existing heartbeat scripts
- Correction workflows respect approval system
- Drift findings displayed with appropriate formatting

### Stage 4 Approval/Audit
- Approval workflow fully integrated
- Comprehensive audit logging applied to all operations
- Privacy controls respect existing sensitive data handling

---

This guide covers the complete operation of the MemoryStages TUI dashboard, providing secure administrative access while maintaining the educational and operational integrity of the system.</content>
