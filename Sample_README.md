# Windows Image Builder Automation Tool (WAIT)

## Overview

WAIT is an automated Windows WIM image building and validation system designed for enterprise deployment. The system uses a distributed worker architecture to process build jobs efficiently, with separate workers for building and validation tasks.

📖 **[Deployment Guide](docs/DEPLOY_GUIDE.md)** | **[部署指南（繁體中文）](docs/DEPLOY_GUIDE_zh-TW.md)**

### Core Features

- ✅ Automated Windows WIM/ISO Image Building
- ✅ Intelligent Motherboard Driver Matching
- ✅ Multi-Customer Naming Management
- ✅ Modular Component Integration (Drivers, Updates, Language Packs)
- ✅ Two-Stage Build and Validation Process
- ✅ RESTful API and Web UI
- ✅ Real-time Status Monitoring
- ✅ ISO Support - Supports `.iso` sources and repacking to bootable ISOs.
- ✅ Automatic Soft-Fail - Driver download failures downgrade to warnings without interrupting build.
- ✅ Safe Cancellation - Prevents system locks during cancellation and auto-repairs mount errors (0xc1420127).
- ✅ Resource Path Tracking - Records driver, langpack, update, and software paths for regeneration.
- ✅ Full Reproducibility - Query all resource configs via job_id to quickly rebuild identical images.

### Tech Stack

**Backend:**

- Python 3.8+
- Flask (REST API)
- SQLAlchemy (ORM)
- SQLite (Database)

**Frontend:**

- React 18 + TypeScript
- Vite (Build Tool)
- Tailwind CSS v3 (UI Framework)
- TanStack Query (State Management)
- React Router v6 (Routing)

---

## Architecture

The system follows a separation-of-concerns design with three main components:

```
┌─────────────────┐
│   API Server    │  ← Receives build requests (GUI/Slack Bot)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SQLite DB      │  ← Centralized job queue and status tracking
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────────┐
│  Build  │ │  Validation  │  ← Background workers (polling)
│ Worker  │ │   Worker     │
└─────────┘ └──────────────┘
```

### Components

1. **API Server** (`api/server.py`)
   - REST API for job submission
   - Immediately queues jobs in database
   - Returns job ID to client
   - **No heavy processing** - keeps response time < 200ms

2. **Build Processor** (`workers/build_processor.py`)
   - Polls database for `Queued` jobs
   - Executes all build operations:
     - Driver injection
     - Update installation
     - Language pack addition
     - Product key injection
     - Image optimization
   - **Automatically runs validation after build completes**
   - Single worker handles entire job lifecycle
   - Updates status to `Verified` or `Failed_Build`/`Failed_Validation`

3. **Validation Processor** (`workers/validation_processor.py`)
   - Runs as independent background worker
   - Polls database for `Pending_Validation` jobs
   - Validates built images:
     - Checks file existence and integrity
     - Verifies MD5 checksums
     - Validates WIM structure
     - Verifies manifest content
     - Confirms component installation
   - Updates status to `Completed` or `Failed_Validation`

4. **Database** (`database/`)
   - SQLite database for job management
   - Four main tables:
     - `users` - User accounts for authentication and authorization
     - `build_jobs` - Build task queue with resource path tracking
     - `job_logs` - Structured logging for each job (with log_level support: normal/verbose)
     - `webhooks` - Webhook configurations for notifications
   - **Resource Path Tracking** - Records driver, langpack, updates, and software paths for reproducibility
   - **User Management** - Tracks job creators and webhook owners

5. **Core Modules** (`core/`)
   - `DismWrapper` - DISM.exe operations wrapper
   - `WimOperations` - WIM file handling

## Directory Structure

```

WAIT_Project/                     # Project root directory
│
├── win_imagebuilder/             # Source code directory
│   ├── api/                      # API layer
│   │   ├── server.py             # Flask REST API (main entry point)
│   │   ├── common.py             # Common utilities (shared response/conversion functions)
│   │   ├── utils.py              # API helper utilities
│   │   └── routes/               # API route modules
│   │       ├── job.py            # Simplified single-job endpoints
│   │       ├── job_clone.py      # Job history, search, and cloning
│   │       ├── resources.py      # Resource scanning endpoints
│   │       ├── outputs.py        # Build images (outputs) management
│   │       ├── webhooks.py       # Webhook management endpoints
│   │       └── streaming.py      # Server-Sent Events (SSE) streaming
│   │
│   ├── database/                 # Database layer
│   │   ├── operations.py         # Database operations (CRUD)
│   │   └── models.py             # SQLAlchemy ORM models (3 tables)
│   │
│   ├── workers/                  # Background processors
│   │   ├── build_processor.py    # Build processor
│   │   └── validation_processor.py # Validation processor
│   │
│   ├── core/                     # Core business logic
│   │   ├── wim_operations.py     # WIM file operations
│   │   ├── iso_handler.py        # ISO mounting & WIM extraction
│   │   └── dism_wrapper.py       # DISM wrapper
│   │
│   ├── config/                   # Configuration
│   │   └── settings.py           # System settings
│   │
│   ├── web/                      # React frontend
│   │   ├── src/
│   │   │   ├── components/       # React components
│   │   │   ├── pages/            # Page components
│   │   │   ├── lib/              # API client & utils
│   │   │   └── types/            # TypeScript types
│   │   ├── package.json          # Node.js dependencies
│   │   └── vite.config.ts        # Vite configuration
│   │
│   ├── init_db.py                # Database initialization script
│   ├── migrate_database.py       # Database migration script (v2.4 → v2.6)
│   ├── requirements.txt          # Python dependencies
│   ├── start_all.bat             # Windows startup script
│   ├── deploy_web.bat            # Web UI deployment script
│   ├── README.md                 # Documentation (English)
│   └── README_zh-TW.md           # Documentation (Traditional Chinese)
│
└── WAIT_Repository/              # Data repository (parallel to source code)
    ├── 1_BaseImages/             # Base Windows images (ISO/WIM support)
    │   ├── WINDOWS11_IOT_LTSC_24H2_EN_US_X64.iso    # Windows 11 24H2
    │   ├── WINDOWS11_IOT_LTSC_24H2_EN_US_X64.wim    # Windows 11 24H2
    │   ├── WINDOWS10_IOT_LTSC_21H2_EN_US_X64.iso    # Windows 10 21H2
    │   └── WINDOWS10_IOT_LTSC_21H2_EN_US_X64.wim    # Windows 10 21H2
    │
    ├── 2_Drivers/                # Motherboard drivers (by model → Windows version)
    │   ├── X13SAW/
    │   │   └── WINDOWS11_X64/
    │   │       ├── chipset/
    │   │       ├── network/
    │   │       └── storage/
    │   ├── X13SRN-H-WOHS/
    │   │   └── WINDOWS11_X64/
    │   └── x13_up/
    │       └── WINDOWS11_X64/
    │
    ├── 3_LangPacks/              # Language packages (by Windows version)
    │   ├── WIN11_IOT_24H2_X64/
    │   │   └── *.cab
    │   └── WIN10_IOT_21H2_X64/
    │       └──*.cab
    │
    ├── 4_Updates/                # Windows updates (by customer/project → Windows version)
    │   └── [customer]/
    │       ├── WIN11_24H2/
    │       │   └── *.msu,*.cab
    │       └── WIN10_21H2/
    │           └── *.msu,*.cab
    │
    ├── 5_AnswerFiles/            # Answer files (by motherboard → Windows version)
    │   └── X13SAW/
    │       └── WIN11_24H2/
    │           └── autounattend.xml
    │
    ├── 6_Software/               # Software packages (by customer/project → Windows version)
    │   └── [customer]/
    │       ├── WIN11_24H2/
    │       │   └── *.exe,*.msi, *.appx,*.msix
    │       └── WIN10_21H2/
    │           └── *.exe,*.msi
    │
    ├── 7_Tools/                  # External tools (oscdimg, etc.)
    │   └── oscdimg/
    │       └── oscdimg.exe
    │
    └── 8_Output/                 # Build outputs (by customer → timestamp_motherboard)
        └── AABBCCE/
            └── 20251112_090645_X13SAW/
                ├── install.wim
                ├── manifest.txt
                └── checksum.md5

```

## Database Schema

**Version 2.0 Schema** - 4-table design with user management and verbose log support

SQLAlchemy ORM models defined in `database/models.py`:

- **User** - User accounts for authentication and authorization, tracks job creators and webhook owners
- **BuildJob** - Core job tracking table with status management, resource paths for reproducibility, output paths, timestamps, and creator tracking
- **JobLog** - Structured logging system with composite primary key (job_id, timestamp) and log level filtering support (normal/verbose)
- **Webhook** - External notification endpoints with event subscription, HMAC-SHA256 signature support, and creator tracking

## Job Status Flow

```

Queued → Processing_Build → Pending_Validation → Processing_Validation → Completed
                 ↓                                           ↓
           Failed_Build                              Failed_Validation

```

**Note:** `Verified` is a legacy status kept for compatibility. New jobs use `Completed` as the final success status.

## Build Output

Upon successful validation, each job produces the following files in `8_Output/<customer_name>/`:

1. **`<image_name>.wim`** - The final customized Windows image
2. **`manifest.txt`** - Comprehensive build manifest containing:
   - Job information (ID, customer, motherboard, base image)
   - File information (path, size, MD5 hash)
   - Validation results (verified components)
   - WIM information (image details, index)
   - Complete list of installed packages
3. **`checksum.md5`** - MD5 checksum file in standard format
   - Format: `<hash> *<filename>`
   - Compatible with `md5sum -c checksum.md5` for verification
   - Can be used to verify file integrity during transfer/storage

**Example output structure:**

```

8_Output/
└── CustomerA/
    └── 20250111_143000_X13SAV/
        ├── install.wim                      # Final WIM image
        ├── manifest.txt                     # Build details & verification
        └── checksum.md5                     # MD5 hash for integrity check

```

## Installation & Setup

### Prerequisites

- **Windows OS** (required for DISM operations)
- **Administrator privileges** (required)
- Python 3.8+
- PowerShell 5.0+

### Installation Steps

1. **Clone Repository**

   ```bash
   git clone <repository_url>
   cd win_imagebuilder
   ```

2. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize Database**

   ```bash
   python init_db.py
   ```

4. **Setup Directory Structure**

   ```bash
   # Create required directories (done automatically by init_db.py)
   # Place your base images in 1_BaseImages/
   # Place drivers in 2_Drivers/<ModelName>/<WINDOWS_VERSION>/
   # Place updates in 4_Updates/
   # Place language packs in 3_LangPacks/
   ```

5. **Run Database Migration** (if upgrading from v2.4 or earlier)

   ```bash
   python migrate_database.py
   ```

## Usage

### Running Workers

**Quick Start** (Recommended):

```bash
start_all.bat   # Starts API Server + Build Processor (validation is run automatically) and opens the Web UI
```

**Manual Start**:

**Start Build Processor (includes validation)** – Terminal 1

```bash
python workers/build_processor.py
```

**Start API Server** – Terminal 2

```bash
python api/server.py
```

**Optional: Dedicated Validation Worker** – Terminal 3

```bash
python workers/validation_processor.py
```

> ℹ️ The build processor automatically invokes the validation workflow once a build finishes. Launch the standalone validation worker only when you need to keep validation running on a separate schedule (for example, when replaying validation on historical jobs).

### Creating Jobs Programmatically

Use the `DatabaseManager` class to create build jobs:

- Initialize DatabaseManager with the database path
- Call `create_build_job()` with required parameters (motherboard_model, base_image, customer_name)
- Optional parameters include product_key and components list
- Method returns the created job_id

### Checking Job Status

Use DatabaseManager to query job status:

- `get_job(job_id)` - Retrieve a specific job by ID
- `get_jobs_by_status(status)` - Get all jobs with a specific status
- Job objects contain status, output_image_path, and all other job details

## Configuration

Edit [config/settings.py](config/settings.py) to customize:

- Database path
- Directory locations
- Polling intervals
- Retry settings
- Compression options

## Key Features

### 1. **ISO and WIM Support**

- **Dual Format Support**: Accepts both ISO and WIM files as base images
- **Automatic ISO Mounting**: PowerShell-based ISO mounting (no third-party tools)
- **Intelligent WIM Extraction**: Automatically locates and extracts install.wim from ISOs
  - Searches common paths: `sources/install.wim`, `x64/sources/install.wim`, etc.
  - Recursive fallback search if not found in standard locations
- **ISO Creation**: Generate bootable ISOs using oscdimg.exe
- **Tool Management**: Centralized tools directory (`7_Tools/`) for external utilities

**Usage**:
Use the `ISOHandler` class from `core.iso_handler` module:

- Initialize handler with tools_dir parameter
- Call `extract_wim_from_iso()` with ISO path, output directory, and desired WIM name
- Method returns success status, message, and extracted WIM path
- Extracted WIM path can then be used in build jobs

### 2. Automated Driver Injection

- Automatically detects motherboard model
- Injects drivers from `2_Drivers/<ModelName>/driver/`
- Supports recursive driver installation

### 3. Component Management

- Windows Updates (.msu, .cab)
- Language Packs (.cab)
- AppX Applications (.appx)
- Custom Software

### 4. WinRE Processing

- Automatically processes WinRE.wim for language packs
- Cleanup and optimization
- Size calculation and reporting

### 5. Image Optimization

- Component cleanup (/StartComponentCleanup)
- Reset base (/ResetBase)
- Maximum compression
- MD5 verification

### 6. Product Key Injection

- Optional Windows product key injection
- Supports unattend.xml integration
- Separate builds for key/no-key variants

### 7. Retry Logic

- Automatic retry on failure (max 3 attempts)
- Exponential backoff
- Status tracking per retry

### 8. Manifest Generation

- Complete package list
- MD5 checksums
- Image information
- Build metadata

## API Documentation

Complete API documentation is available in separate files:

- **[API_ENDPOINT.md](docs/API_ENDPOINT.md)** - English API Reference
- **[API_ENDPOINT_zh-TW.md](docs/API_ENDPOINT_zh-TW.md)** - Traditional Chinese API Reference

> 🔐 **Authentication required**: All `/api/job*`, `/api/queue`, and `/api/jobs*` endpoints check for an active session. Call `POST /api/auth/login` (with JSON `{"username": "...", "password": "..."}`) first, store the returned session cookie, and reuse it for subsequent API requests to avoid 401 errors.

### Quick Start

**Basic Operations:**

- **Create a job**: POST to `/api/job` with motherboard_model and base_image in JSON body
- **Check status**: GET from `/api/job`
- **Stream logs**: GET from `/api/job/stream` (use -N flag for streaming)

### API Overview

> ⚠️ **Single-Job Mode**: WAIT now operates in single-job execution mode. Only one job can run at a time, and additional jobs will wait in queue.

**Single-Job API (Primary Interface):**

- `POST /api/job` - Create job (queues if another is active)
- `GET /api/job` - Get current/recent job status
- `GET /api/queue` - List all queued jobs
- `GET /api/job/stream` - Stream logs (SSE)
- `GET /api/job/manifest` - Get manifest
- `POST /api/job/cancel` - Cancel job
- `DELETE /api/job` - Delete job

**Job History & Clone API:**

- `GET /api/jobs` - List all jobs with filtering
- `GET /api/jobs/search` - Search jobs
- `POST /api/jobs/<id>/clone` - Clone existing job

**Webhook API:**

- `POST /api/webhooks` - Create webhook
- `GET /api/webhooks` - List webhooks
- `PATCH /api/webhooks/:id` - Update webhook
- `DELETE /api/webhooks/:id` - Delete webhook

**Resource API (Smart Filtering):**

- `GET /api/resources/motherboards` - List motherboards
- `GET /api/resources/motherboards/search` - Search motherboards with similarity scoring
- `GET /api/resources/drivers/recommend` - Get driver recommendations based on motherboard and base image
- `GET /api/resources/base-images` - List base images
- `GET /api/resources/driver-versions` - Get driver versions for motherboard
- `GET /api/resources/compatible-versions` - Get compatible versions for base image
- `GET /api/resources/langpacks` - List language packs
- `GET /api/resources/updates` - List Windows updates
- `GET /api/resources/software` - List software packages
- `GET /api/resources/answer-files` - List answer files
- `GET /api/resources/tools` - List tools

**Build Images API (Outputs):**

- `GET /api/outputs` - List all build outputs with optional search filtering
- `GET /api/outputs/<customer>/<job>/manifest` - Get manifest content (text or JSON)
- `GET /api/outputs/<customer>/<job>/download` - Download bundled ZIP (WIM + MD5 + Manifest)
- `GET /api/outputs/<customer>/<job>/download/wim` - Download WIM file only
- `GET /api/outputs/<customer>/<job>/download/checksum` - Download MD5 checksum file
- `GET /api/outputs/<customer>/<job>/download/manifest` - Download manifest file

**System API:**

- `GET /api/health` - Health check

📖 **See [API_ENDPOINT.md](docs/API_ENDPOINT.md) for complete documentation with examples.**

## Troubleshooting

### Common Issues

**1. DISM Errors**

- Ensure running as Administrator
- Check Windows version compatibility
- Verify WIM file is not corrupted

**2. Mount Failures**

- Check if previous mount is still active
- Run cleanup: `DISM /Cleanup-Wim`
- Reboot system if necessary

**3. Database Locked**

- Ensure only one worker of each type is running
- Check file permissions on wait.db

**4. Missing Drivers**

- Verify driver path: `2_Drivers/<ModelName>/driver/`
- Check directory structure matches model name
- Ensure drivers are .inf format

## Development

### Adding New Motherboards

Use the DatabaseManager `add_motherboard()` method:

- Provide model_name (required) and scrape_url (optional)
- Method adds the motherboard to the database for future job creation

### Extending Workers

Workers are designed to be extensible. To add custom processing:

1. Inherit from `BuildProcessor` or `ValidationProcessor`
2. Override `_process_job()` method
3. Add custom logic while maintaining status updates

## Performance

- **API Response**: < 200ms
- **Build Time**: 30-60 minutes (depends on components)
- **Validation Time**: 5-10 minutes
- **Execution Mode**: Single-job sequential (one job at a time)
- **Queue**: FIFO (First In, First Out) order

## Security

- **Administrator Required**: DISM operations require elevation
- **Input Validation**: All paths and inputs are validated
- **SQL Injection**: Protected by SQLAlchemy ORM
- **Environment Variables**: Sensitive data should use .env files

## License

Internal use only - SuperMicro Corporation

## Support

For issues or questions, please contact the development team or refer to the troubleshooting section above.

## Author

**Ben Lin**
Email: <benlin@supermicro.com>

## Contributors

- Original GUI Tool: Previous development team
- Architecture Refactor (v2.0): Current development team

---

**Note**: This tool must be run on Windows with Administrator privileges. DISM operations are Windows-specific and cannot be executed on other operating systems.

**Ben Lin**
Email: <benlin@supermicro.com>

---

Version: 2.0
Last Updated: 2025-01-15
