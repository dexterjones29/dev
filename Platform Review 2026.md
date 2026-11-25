# Commercial Bank Control Automation Platform: 2026 Architectural Review & Year-End Impact Analysis

**Author:** Dexter Jones  
**Organization:** Key Commercial Bank — 1LOD Technology & AI Risk  
**Evaluator:** Marc Sue  
**Review Period:** 2026 Performance Year (Focus: H2 Platform Evolution)  
**Document Generated:** November 5, 2026  

---

## Executive Summary

During the first half of 2026, automation efforts were focused on building isolated, high-impact "intelligent" scripts (e.g., FIS Check Request fuzzy-logic validation, ACH Risk Criteria 5-threshold risk modeling, PCard Temp Line regex compliance parsing, and SAS-to-Python escheatment data pipeline modernization).

Between September and November 2026, the operating paradigm shifted completely: recognizing that rebuilding orchestration for individual controls was unsustainable, the **Commercial Bank Control Automation Platform** was conceived, architected, and deployed. Rather than treating automation as a collection of bespoke scripts, the platform operates as an enterprise **Control Automation Factory**. 

Individual controls are strictly responsible for defining their evaluated population and risk criteria; the platform handles all repeatable execution, data freshness validation, BigQuery history persistence, certificate-authenticated SharePoint review workflows, dual-tier telemetry, automated governance document generation, containerized Cloud Run deployments, and executive portfolio tracking.

---

## 1. End-to-End System Architecture

```text
                          [ENTERPRISE GRC]   ◄── (GRC_SRC_DATA)
                                  │ 
                                  ▼
                        ┌─────────────────┐
                        │ GRC_Config_Sync │  ◄── Guardrails (Max 5% / 10 drops),
                        └─────────┬───────┘      SHA-256 Hashing, Stage/Diff/Apply
                                  ▼
                       [CONFIG & CONFIG_STAGE]
                                  │
             ┌────────────────────┴────────────────────┐
             ▼                                         ▼
┌─────────────────────┐                    ┌────────────────────────┐
│ Control_Assembly.py │                    │ Governance_Assembly.py │
└────────────┬────────┘                    └───────────┬────────────┘
             │ Standardized code contract              │ SOP & GRC proposals
             ▼                                         │ Zero-hallucination rules
┌────────────────────────┐                             ▼ 
│ Production Controls    │                 [Audit-Ready DOCX Artifacts]              
│ (e.g. COS_CP_11226203) │              
└────────────┬───────────┘
             │
             ▼
 ┌───────────────────────────────────────────────────────────────────────────────┐   
 │                            SHARED RUNTIME ENGINE                              │   
 │                                                                               │   
 │• utils.py: Freshness Gateways, BQ I/O, Safe Transports, Aptos Excel Styling   │   
 │• logs.py: Dual Telemetry (EXECUTION_LOG run-level + DIAGNOSTIC_LOG step-level)│   
 │• sp.py: Cert-based Auth, Dynamic Review Lists, Unique RUN_ID Ingestion        │   
 │• monday.py: Schema-mapped GraphQL Mutations, Automated Board Population       │   
 └──────────────────────────────────────┬────────────────────────────────────────┘   
                                        │
                                        ▼
 ┌───────────────────────────────────────────────────────────────────────────────┐
 │                        FLEET ORCHESTRATION & CLOUD OPS                        │
 │                                                                               │
 │• control_job_list.conf: Single Source of Truth for production job schedules   │
 │• cloud_run_jobs_*.sh: Containerized GCP deployments, test-mode toggles,       │
 │  fleet image updates, and Cloud Scheduler HTTP synchronization                │
 │• Project_Board_History.py: Automated leadership reporting                     │
 │• VM_Backup.py & nightly_git_commit.sh: disaster recovery and code snapshots   │
 └───────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Layers & Implementation Analysis

### Layer 1: Authoritative Configuration & Governance Sync
* **`GRC_Config_Sync.py`:**
  * Establishes `taw-entpayments-prod-2935.AW_COMMERCIAL_CP.CONFIG` as the governed registry, cleanly separating GRC-owned metadata (owners, testing procedures, cadences) from platform-owned automation metadata (automation status, timestamps, row hashes, change classification).
  * **Enterprise Guardrails:** 
  Enforces `MAX_CONTROL_DROP_COUNT = 10` and `MAX_CONTROL_DROP_PCT = 0.05` to prevent inadvertent configuration regressions.
  * **Deterministic Change Detection:** 
  Employs canonical SHA-256 row fingerprints and array-based change classification (`MBU`, `Placement`, `Design`, `Frequency`, `Procedure Name`, `Owner`, `Delegates`, `Detailed Procedure`, `Testing Procedures`, `Source Docs`). Supports `--dry-run` and `--apply` operating modes.
* **`Procedure_Directory_Update.py`:**
  * Programmatically provisions and synchronizes active control procedures from `CONFIG` into the enterprise SharePoint Procedure Directory.
  * Automatically resolves human owners to internal SharePoint user IDs (`ctx.web.ensure_user()`), eliminating manual registry maintenance.

### Layer 2: Control Development & Code Assembly
* **`Control_Assembly.py`:**
  * Acts as the code-generation engine for the platform. Given a single `--cp-number`, it retrieves authoritative configuration, derives standardized technical identifiers, tables, and lists, and outputs a complete, preassembled Python control script.
  * **Standardized Control Contract:** 
  Enforces an immutable two-query structure:
    1. `query_population_evaluated()`: Defines the complete, authoritative denominator evaluated by the documented procedure.
    2. `query_risk_logic()`: Applies documented criteria to identify records requiring review (`REVIEW_CRITERIA`).
  * Wraps control logic with standard execution boilerplate: freshness checks, configuration verification, hashing, BigQuery result persistence, SharePoint review list synchronization, and telemetry logging.

### Layer 3: Automated Governance Compilation
* **`Governance_Assembly.py`:**
  * Directly addresses manager feedback from the Mid-Year Review regarding driving automation through implementation, desktop procedure publication, and ASR updates.
  * Ingests authoritative `CONFIG`, current operating SOPs, the implemented code contract, and approved DOCX templates.
  * **Zero-Hallucination Design:** 
  Interacts with LLM endpoints (`temperature=0`) under strict risk mandates: never invent business facts. Missing items are explicitly flagged as `[BUSINESS CONFIRMATION REQUIRED: ...]`, and contradictions between code and documentation are captured in `source_conflicts`.
  * Generates formatted, corporate-branded Word documents (`python-docx` with XML shading and Aptos typography) ready for BRC review and challenge.

### Layer 4: Shared Runtime Services
* **`utils.py`:**
  * **Fail-Safe Freshness Validation (`validate_table_freshness`):** 
  Queries `MAX(date_field)` across all dependent source tables against control cadences (Daily, Weekly, Monthly, Quarterly, Annually). Halts execution on stale data to prevent false-positive "clean" runs against incomplete data.
  * **Standardized BigQuery I/O:** 
  Provides safe client instantiation, table creation, and merge-key deduplication.
  * **Enterprise Notifications:** 
  Formats and delivers branded HTML completion emails and Teams webhook adaptive cards.
* **`logs.py`:**
  * Implements institutional-grade observability:
    * `EXECUTION_LOG`: Run-level operational metrics (run duration, evaluated count, review count, status, query hashes, git commit, container image tag).
    * `DIAGNOSTIC_LOG`: Granular, step-level telemetry (BigQuery job IDs, bytes processed, component timing, source table/field validation, stack traces).
* **`sp.py`:**
  * Manages PKCS#12 certificate-based authentication via MSAL and Entra ID across departmental SharePoint sites (CPC, PPC, CTF, KMS, 1LOD, DLR, PMT), eliminating plain-text secrets.
  * Automates creation and maintenance of SharePoint Review Lists, enforcing idempotency using `RUN_ID` as a unique key.
* **`monday.py`:**
  * Implements cursor-paginated GraphQL integration with Monday.com to map, retrieve, create, and update board items.

### Layer 5: Cloud Infrastructure & Fleet Operations
* **`control_job_list.conf`:**
  * The declarative source of truth for the production Cloud Run job fleet, defining job names, script targets, and cron schedules.
* **Shell IaC Utilities (`utilities/`):**
  * `cloud_run_jobs_deploy.sh`: Deploys containerized jobs to Google Cloud Run with VPC connector routing (`svac-prod-usc1-01`), 1 vCPU / 512MiB configurations, 3 retries, and 600s timeouts.
  * `cloud_run_jobs_schedule.sh`: Provisions and synchronizes Cloud Scheduler HTTP trigger jobs in `America/New_York` timezone.
  * `cloud_run_jobs_update_image.sh` & `cloud_run_jobs_test_mode.sh`: Enables zero-downtime fleet container image updates and global notification test-mode toggles.
  * `fleet_test_controls.sh`: Sequential portfolio regression test harness validating the entire script inventory against live enterprise databases.
  * `VM_Backup.py` & `nightly_git_commit.sh`: Automated disaster recovery to Google Cloud Storage (`gs://commercial_payments_controls/dexter-jones`) with regex exclusion filters and nightly Git version control snapshots.
* **`00-Commands.txt`:**
  * 1,100+ line operational runbook covering syntax checking (`py_compile`, `compileall`), execution commands, deployment checklists, and log investigation queries.

### Layer 6: Executive Portfolio Measurement
* **`Project_Board_History.py`:**
  * Connects to Monday.com, archives weekly item-level snapshots to BigQuery (`PROJECT_BOARD_HISTORY`), and tracks velocity across lifecycle stage gates (`Data Discovery` → `Ready to Develop` → `ASR Submitted` → `Project Completed`).
  * Dynamically calculates Commercial Bank's automation progress and remaining distance toward the bank's **60% and 75% automation objectives**.
  * Distributes branded, executive-ready HTML status reports directly to leadership.

### Layer 7: Reference Implementation (`COS_CP_11226203.py`)
* End-to-end production implementation for *Quality Review for Franchise SBA DDA Accounts*:
  * Sources complex, cross-domain data: nCino loan origination (`NCINO_CRNT_BV`), Hogan core DDA extracts (`DDAEXTRACT_V`), and Scan Index Document Capture (`SCAN_INDEX_DOCUMENTS`).
  * Evaluates SBA 7(a) franchise loans against newly opened DDAs within 30 days, joining to Hogan imaging systems to verify signature card capture (Doc Type 7161).
  * Automatically coordinates freshness checks, BigQuery history persistence, SharePoint review list updates, and standardized HTML email alerts.

---

## 3. Performance Journey: Mid-Year (July) vs. Current (November)

| Dimension | Mid-Year 2026 (July) | Current State (November 2026) | Role Implication |
| :--- | :--- | :--- | :--- |
| **Operational Paradigm** | Building isolated, bespoke automation scripts (FIS Check Requests, ACH Risk Criteria, PCard Temp Lines). | Designed and deployed an **Enterprise Control Automation Factory** with standardized, reusable layers. | **Analyst ➔ Architect** |
| **Configuration Management** | Static, hardcoded parameters embedded in standalone scripts. | Governed control registry (`CONFIG`) continuously synchronized with enterprise GRC via `GRC_Config_Sync.py`. | **Task Execution ➔ Systems Design** |
| **Governance & Documentation** | Evaluator noted: *"Dexter should continue focusing on driving automation work through implementation, including related ASRs [and] desktop procedures..."* | Engineered `Governance_Assembly.py` to auto-generate audit-ready SOPs and GRC proposals deterministically. | **Reactive Documentation ➔ Platform Innovation** |
| **Runtime & Deployment** | Local / Jupyter-executed batch runs. | Containerized **GCP Cloud Run Jobs** orchestrated via Cloud Scheduler, IaC shell scripts, and fleet image management. | **Script Developer ➔ Cloud Platform Engineer** |
| **Observability & Audit** | Basic script-level print statements and ad-hoc logging. | Dual-tier telemetry (`EXECUTION_LOG` + `DIAGNOSTIC_LOG`) capturing BigQuery job IDs, query hashes, bytes processed, and execution timing. | **Developer ➔ Enterprise Risk Engineer** |
| **Portfolio Impact** | Focus on individual control outputs and script delivery. | Programmatic tracking of Commercial Bank's progress toward **60% & 75% automation objectives** (`Project_Board_History.py`). | **Contributor ➔ Strategic Partner** |

---

## 4. Conclusion & Leveling Justification

While HR records currently reflect the title of **Senior Analyst**, the technical scope, architectural depth, and operational leadership demonstrated across this codebase are characteristic of a **Lead Platform Architect / Principal Automation Engineer**:

1. **Strategic Decoupling:** Replaced fragmented, bespoke scripting with a factory model that isolates business risk logic from orchestration infrastructure.
2. **Managerial Alignment:** Transformed mid-year developmental feedback into an automated platform asset (`Governance_Assembly.py`), eliminating the operational bottleneck between code completion and governance approval.
3. **Enterprise Resilience:** Enforced data freshness tripwires, dual-tier telemetry, certificate-based IAM authentication, automated regression testing, and cloud disaster recovery.
4. **Executive Observability:** Established automated tracking against enterprise risk automation targets, providing executive leadership with verifiable portfolio progress metrics.
