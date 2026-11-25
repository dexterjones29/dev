# Commercial Bank Control Automation Platform

## Purpose

The Commercial Bank Control Automation Platform provides a standardized framework for developing, executing, monitoring, evidencing, and governing automated and hybrid control procedures across the commercial bank. The platform is designed to increase control automation capacity by separating control-specific business logic from reusable automation infrastructure. Individual controls define what population is evaluated, what evidence is required, and what conditions require review. The platform handles the repeatable engineering required to execute those controls consistently.

## Core Design Principle

The platform is designed as a factory, not a collection of bespoke automation scripts. Each control requires its own validated business and risk logic. The surrounding execution framework should not need to be rebuilt for every control.

```text
Detailed Control Procedure
        ↓
Testing Procedure
        ↓
Business and Data Discovery
        ↓
Validated Population and Evidence
        ↓
Evaluated Population Query
        ↓
Documented Risk Logic
        ↓
Population Evaluated
        ↓
---------------------------
Control Automation Platform
        ↓
Execution
Data Freshness Validation
History Table
Review Workflow
Evidence
Notifications
Diagnostics
Monitoring
Scheduling
Governance
```

The objective is not to automate away business understanding. Rather, the objective is to automate everything that becomes repeatable once the business process and control logic have been established.

## Platform Architecture

The platform consists of five primary layers:

1. Authoritative configuration
2. Control development and assembly
3. Control execution
4. Review, evidence, and observability
5. Governance and production operations

```text
Authoritative GRC Source
        ↓
GRC_Config_Sync.py
        ↓
CONFIG_STAGE
        ↓
Validation + Change Detection + Guardrails
        ↓
CONFIG
        |____________________________
        ↓                           ↓
Control_Assembly.py         Governance_Assembly.py
        ↓                           ↓
Preassembled Control        SOP + GRC Documentation
        ↓
Control Discovery + Development
        ↓
Validated Control Logic
        ↓
Control Execution
        |
        |-- Configuration Validation
        |-- Source Freshness Validation
        |-- Population Evaluation
        |-- Risk Logic Evaluation
        |-- BigQuery History
        |-- SharePoint Review
        |-- Email / Teams Notification
        |-- Execution Logging
        |-- Diagnostic Logging
                ↓
        Cloud Run Jobs
                ↓
        Cloud Scheduler
```

## Authoritative Configuration

### GRC Configuration Sync

`GRC_Config_Sync.py` is the authoritative configuration backbone of the platform. It synchronizes the latest GRC control population into the platform while preserving the distrinction between GRC-owned control information and platform-owned automation information.

The synchronization process:

1. Loads the latest GRC snapshot into `CONFIG_STAGE`.
2. Validates schema, source date, control identity, MBU, design, status, and population integrity.
3. Compares the staged GRC population with the current platform configuration.
4. Identifies added, changed, removed, reactivated, and unchanged controls.
5. Enforces source-date and population-regression guardrails.
6. Supports dry-run review before making configuration changes.
7. Synchronizes authoritative GRC fields while preserving platform-owned fields.
8. Validates the resulting active configuration population.
9. Reports material changes.

### CONFIG

`taw-entpayments-prod-2935.AW_COMMERCIAL_CP.CONFIG`

`CONFIG` is the platform's governed control registry. It combines authoritative GRC information with platform-specific automation metadata.

Authoritative control information includes:

- Procedure ID
- Control Procedure
- Detailed Control Procedure
- Testing Procedures
- Control Owner
- Control Owner Delegates
- Control Design
- Frequency of Control
- Source Documents
- Material Business Unit

Platform information includes:

- Standardized MBU
- Automation status
- GRC active status
- GRC first-seen date
- GRC last-seen date
- Configuration sync timestamp
- GRC row hash
- Change-detected indicator
- Change classification

This allows the platform to maintain operational configuration without replacing GRC as the authoritative source for control definitions.

## Control Development

### Control Assembly

`Control_Assembly.py` is the primary control-development assembly engine.

Given a Procedure ID, Control Assembly:

1. Retrieves authoritative control information from `CONFIG`.
2. Validates the control configuration.
3. Derives standardized implementation names.
4. Creates a preassembled Python control.
5. Provides the common runtime framework required by the platform.

The developer supplies the portions that are genuinely specific to the control:

- Live email recipients
- Source tables
- Source table freshness fields
- Control frequency
- Population grain
- Reviewable result grain
- Result schema
- Merge keys
- Evaluated population query
- Documented risk logic query

The remaining execution framework is standardized.

### Control-Specific Contract

Every control must establish two fundamental queries.

### Evaluated Population Query

Defines the complete population evaluated by the documented control procedure. This is the basis for `POPULATION_EVALUATED`.

### Risk Logic Query

Applies the documented control criteria to the evaluated population and identifies records requiring review. The control-specific contract can therefore be summarized as:

```text
Authoritative Population
        ↓
Required Evidence
        ↓
Documented Control Criteria
        ↓
population_evaluated()
        ↓
risk_logic()
        ↓
Results for Review
```

A technically valid query is not considered sufficient merely because it executes successfully. Population definitions, source fields, joins, dates, thresholds, and PASS/FAIL logic must be supported by the documented control and validated business process.

## Data Discovery

Automation begins with understanding the control, not with writing code.

The standard discovery process is:

1. Review the detailed control procedure.
2. Review the testing procedure.
3. Review the most recent operating assessment where available.
4. Identify how the control is actually performed.
5. Identify the population used by the control.
6. Identify the evidence used to evaluate that population.
7. Located candidate enterprise data sources.
8. Reproduce known historical population and evidence records.
9. Validate identifiers, joins, dates, field meanings, and business rules.
10. Define deterministic evaluation logic.
11. Build and validate the control-specific queries.
12. Integrate the validated logic with the platform.

### Column Map

`taw-entpayments-prod-2935.AW_COMMERCIAL_CP.COLUMN_MAP`

The Column Map provides a centralized searchable inventory of available BigQuery tables and columns across relevant enterprise datasets. It is used as an initial discovery resource when identifiying potential population, evidence, and relationship data. Certified ESA views are preferred when they provide the data required by the documented control. Source datasets are used when necessary for control-specific evidence or data not available through certified analytical views.

## Execution Framework

Controls execute through a standardized runtime sequence.

Typical execution includes:

```text
Create Run Context
        ↓
Validate Configuration
        ↓
Validate Source Freshness
        ↓
Execute Population Query
        ↓
Calculate Population Evaluated
        ↓
Apply Risk Logic
        ↓
Persist New Results
        ↓
Publish SharePoint Review Item
        ↓
Send Notification
        ↓
Record Execution Result
```

Execution behavior is standardized so that control developers can focus on control logic rather than rebuilding orchestration.

## Data Freshness

Source-data freshness is validated before a control evaluates its population.

Controls define:

- Required source tables
- Applicable date fields
- Required freshness threshold

The platform compares the latest available source dates with the expected control frequency. Stale data can halt control execution rather than allowing an apparently successful control to run against an incomplete or outdated population. Source-level validation results are retained in diagnostic logging.

## Result History

Each control maintains persistent result history in BigQuery.

History records include:

- Run timestamp
- Unique result identifier
- Control-specific result fields
- Evidence required to understand the review condition

Results are persisted using control-defined merge keys to prevent the same underlying exception from being repeatedly inserted as a new result. The result history provides durable evidence independent of the human-facing review workflow.

## SharePoint Review Workflow

SharePoint is the primary human-facing review layer for standardized control results. The platform can automatically create and maintain a review List for a control.

Standard review information includes:

- Status
- Detailed-results link
- Run time
- Run ID

Each execution can create or update a review item linked directly to the control's detailed BigQuery history. A run with no new results can be marked complete automatically. A run containing new results is surfaced for reviewer disposition.

This separates:

```text
BigQuery
Detailed persistent control history

from

SharePoint
Human-facing review and evidence workflow
```

## Execution Logging

`taw-entpayments-prod-2935.AW_COMMERCIAL_CP.EXECUTION_LOG`

The execution log provides one standardized record for each control run.

It captures:

- Run ID
- Start and end time
- Duration
- MBU
- Procedure ID
- Control procedure
- Execution mode
- Trigger type
- Rerun indicator
- Final status
- Population evaluated
- Results identified
- Results inserted
- Results skipped
- Configuration status
- Freshness status
- Population-query status
- Review-query status
- History-write status
- Review-write status
- Email status
- Intended and actual recipients
- Email subject
- Deployment image tag
- Git commit
- Configuration hash
- Population-query hash
- Review-query hash
- Failure step
- Error message

This provides the run-level operational history of the platform.

## Diagnostic Logging

`taw-entpayments-prod-2935.AW_COMMERCIAL_CP.DIAGNOSTIC_LOG`

Diagnostic logging provides step-level evidence within each execution.

Diagnostic records can capture:

- Run ID
- Event sequence
- Event timestamp
- Execution step
- Component
- Status
- Source object
- Source field
- Exepected value
- Observed value
- Row count
- BigQuery job ID
- Bytes processed
- Query duration
- Record ID
- Destination location
- Detail message
- Error information

This creates traceability below the overall execution status and allows individual platform components to be investigated independently.

## Notifications

The platform supports standardized email and Teams notifications.

Control-completion notifications can provide:

- Population evaluated
- Results requiring review
- Overall review status
- Direct link to the SharePoint review workflow
- Direct link to detailed BigQuery result history
- Direct link to execution history

Test-mode execution can redirect notification to controlled test recipients before production activation.

## Governance Assembly

`Governance_Assembly.py` is the platform's governance-documentation assembly engine.

It brings together:

- Authoritative `CONFIG` information
- The current business standard operating procedure (SOP)
- The implemented automation contract
- Approved SOP templates
- Approved GRC templates
- Additional reviewed governance input

The assembly process creates a grounded source package from which proposed governance artificats can be produced. Missing business information is not silently invented.

Unknown requirements are explicitly identified as:

`[BUSINESS CONFIRMATION REQUIRED: ...]`

Conflicting source information is separately surfaced for resolution.

Governance Assembly can produce:

- Proposed operating procedures
- Current-versus-proposed GRC documentation
- Governance source packages
- Governance generation prompts
- Structured governance proposals

This allows technical implementation and governance documentation to be reconciled while preserving business ownership of unresolved decisions.

## Shared Platform Services

### `utils.py`

Provides shared services including:

- Environment and secret loading
- Proxy management
- BigQuery authentication
- Control configuration retrieval
- BigQuery table links
- History-table creation
- Source freshness validation
- Population evaluation
- BigQuery loading
- Email notifications
- Teams notifications
- PDF text extraction
- Excel formatting

### `logs.py`

Provides:

- Run-context creation
- Query and configuration hashing
- Diagnostic logging
- Execution logging

### `sp.py`

Provides:

- Department-aware SharePoint authentication
- File download and upload
- Recursive SharePoint discovery
- File-date filtering
- Standard review-list provisioning
- Review-list item creation and update

### `constants.py`

Provides centralized definitions for:

- Platform tables
- Execution statuses
- Component statuses
- Execution modes
- Trigger types
- MBU definitions
- GRC mappings
- Control frequencies
- Notification identities
- SharePoint department configuration

### `tables.py`

Provides standardized references to commonly used enterprise and platform data sources.

### `monday.py`

Provides reusable Monday.com functionality for:

- Board discovery
- Item retrieval
- Item creation
- Updates
- Column management
- Publishing DataFrame results

## Production Runtime

Control workloads are designed for execution through Cloud Run Jobs.

A common container image provides the platform runtime while individual Cloud Run Jobs specify the applicable control script.

This allows multiple controls to share the same standardized deployment environment without requiring an independent application stack for each control.

### Deployment

`cloud_run_jobs_deploy.sh`

Deploys configured control jobs using standardized:

- Google Cloud project
- Region
- Container image
- Service account
- VPC Connector
- CPU
- Memory
- Retry behavior
- Timeout
- Test-mode configuration

### Scheduling

`cloud_run_jobs_schedule.sh`

Creates or updates Cloud Scheduler jobs for configured control workloads.

Scheduling is standardized using:

- Cloud Run job
- Python script
- Cron schedule
- Eastern Time execution
- Scheduler service account

Controls configured for manual execution can remain outside scheduled execution.

### Image Management

`cloud_run_jobs_update_image.sh`

Allows deployed control jobs to be moved to a selected container image version as a fleet rather than redeployed independently.

### Test Mode

`cloud_run_jobs_test_mode.sh`

Provides centralized switching of deployed control jobs between test and production notification behavior.

### Cloud Configuration

`taw-entpayments-prod-2935.AW_COMMERCIAL_CP_CLOUD_CONFIG`

Cloud configuration provides control-level execution scheduling information, including:

- MBU
- Procedure ID
- Cadence
- Day
- Time
- Start month

This separates scheduling configuration from individual control logic.

## Development and Recovery

The development environment includes additional lifecycle utilities.

### Git

Source code is maintained under Git version control. Nightly commits provide regular development snapshots when source changes are present.

### Virtual Machine Backup

The development workspace is backed up nightly to Google Cloud Storage. Relevant control automation, utility, archive, logging, and preassembly directories are preserved while secrets and disposable runtime artifacts are excluded.

### Fleet Testing

Controls can be tested collectively against the configured control-job inventory before deployment.

### Codebase Compilation

The development environment can generate a consolidated source-code artifact spanning the primary automation dierctories for review and reference.

## Portfolio Measurement

Because `CONFIG` represents the governed control population, the platform can calculate automation coverage directly from authoritative control data.

Current-state reporting can identify:

- Manual controls
- Automated controls
- Hybrid controls
- IT-dependent controls
- Total active controls
- Current automation percentage
- Controls required to reach target automation levels

Automation targets such as 60% and 75% can therefore be calculated dynamically rather than maintained as disconnected project-management estimates.

## Platform Control Plane

The principal control-plane tables are:

| Table            | Purpose                                              |
| ---------------- | ---------------------------------------------------- |
| `CONFIG`         | Governed control registry and platform configuration |
| `CONFIG_STAGE`   | Staged authoritiatve GRC population                  |
| `EXECUTION_LOG`  | Run-level execution history                          |
| `DIAGNOSTIC_LOG` | Step-level execution and diagnostic evidence         |
| `CLOUD_CONFIG`   | Control scheduling configuration                     |
| `COLUMN_MAP`     | Enterprise data-discovery index                      |

Together, these tables provide the metadata, governance, execution, observability, scheduling, and discovery foundation of the platform.

## Development Philosophy

The platform follows several core principles.

### Business logic must be grounded

Automation does not begin with a plausible SQL query. It begins with the documented control, actual business process, operating evidence, and authoritative data.

### Discovery is part of development

When a business process or source system is not understood, discovery is required before automation logic is considered complete.

### BigQuery performs the heavy computational work

Filtering, joining, aggregation, transformation, windowing, population construction, and control evaluation should occur in BigQuery wherever practical. Python primarily provides orchestration around those operations.

### Reusable engineering belongs in the platform

Authentication, logging, notifications, history management, review publication, configuration, deployment, scheduling, and other common concerns should not be independently rebuilt for each control.

### Control-specific logic stays control-specific

Population definition, evidence requirements, business rules, and risk criteria remain explicit within the individual control implementation.

### Governance follow implementation without inventing business facts

Technical implementation can inform governance documentation, but it cannot manufacture missing business requirements. Unknowns remain unknown until confirmed by the appropriate business owner.

## Operating Principle

```text
Discover once where possible.
Validate every control.
Standardize everything repeatable.
Automate only what the evidence supports.
```

## Current Focus

Current development is focused on increasing automated and hybrid control coverage across the Commercial Bank control population. The platform infrastructure required to assemble, execulte, monitor, evidence, govern, deploy, and schedule control automations is substantially standardized. As a result, the primary constraint on new control development is increasingly business-process and data discovery rather than the automation framework itself. 

By design, the platform reduces the engineering cost of each new automation without reducing the standard required to understand and validate the control.

## Maintainer

Dexter Jones | Control Automation Platform Architect | 1LOD Technology & AI Risk | Key Commercial Bank
