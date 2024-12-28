# PandoraTrace

PandoraTrace is a comprehensive benchmarking framework designed to generate and evaluate distributed tracing data from microservice applications under various error conditions. While developed as part of the Gen-T project, PandoraTrace functions as a standalone tool for generating realistic trace data for observability research.

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
  - [Creating Raw Traces](#creating-raw-traces)
  - [Comparing Results](#comparing-results)
- [Contributing](#contributing)
- [License](#license)

## Overview

PandoraTrace enables programmatic generation and analysis of traces exhibiting specific incidents through four key components:

### Components

1. **Applications**
   - Integrates with DeathStarBench microservices suite:
     - socialNetwork
     - hotelReservation
     - mediaMicroservices

2. **Request Patterns**
   - Leverages RESTler (stateful REST API fuzzer)
   - Generates diverse trace request patterns
   - Simulates realistic user interaction patterns

3. **Incident Types**
   - Simulates 10 distinct incident types:
     - Service delays
     - Internal errors
     - Resource constraints

4. **Query Templates**
   - Implements 10 standardized queries
   - Based on industry-standard query languages:
     - TraceQL
     - Jaeger
     - PromQL

## Getting Started

### Prerequisites

- Python 3.8+
- pip (package installer)
- Docker (for running microservices)
- DeathStarBench repository
- RESTler Docker image

### Installation

1. Clone PandoraTrace repository:
```bash
git clone https://github.com/saart/PandoraTrace.git
cd PandoraTrace

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

2. Clone and set up DeathStarBench:
```bash
git clone https://github.com/delimitrou/DeathStarBench.git
```

3. Clone and build RESTler Docker image:
```bash
# Clone RESTler repository
git clone https://github.com/microsoft/restler-fuzzer.git

# Build Docker image
cd restler-fuzzer
docker build -t restler .
```
Note: if you get an error during the docker build, follow the suggestion at: https://github.com/microsoft/restler-fuzzer/issues/901 (add `--break-system-packages` to the `pip install` command in the Dockerfile)

## Usage

PandoraTrace operates in two primary modes:

1. Raw trace generation
2. Trace comparison analysis

### Creating Raw Traces

The framework provides three main functionalities for trace generation. From the PandoraTrace main directory:
```bash
cd src/pandora_trace
```

#### 1. Baseline Trace Creation
```bash
python run_benchmark.py <app_name> --deathstar_dir /path/to/DeathStarBench --create_baseline [--working_dir /path/to/output]
```
Generates baseline traces without incident injection.

Optional parameters:
- `--num_traces`: Minimum number of traces to generate (default: 10,000).

Available applications (`<app_name>`):
- socialNetwork
- hotelReservation
- mediaMicroservices


#### 2. Incident Testing
```bash
python run_benchmark.py <app_name> --deathstar_dir /path/to/DeathStarBench --run_test [--working_dir /path/to/output]
```
- Deploys specified microservice application
- Injects configured incidents
- Generates traffic via RESTler
- Captures and converts Jaeger traces

Optional parameters:
- `--num_traces`: Minimum number of traces to generate (default: 10,000).

#### 3. Trace Merging
```bash
python run_benchmark.py <app_name> --deathstar_dir /path/to/DeathStarBench --prepare_traces [--lambda_values LAMBDA...] [--working_dir /path/to/output]
```
Combines incident and benign traces using an exponential distribution to simulate realistic incident occurrence patterns. The --lambda_values parameter controls the frequency of incidents:

- Each lambda ($\lambda$) represents the rate parameter of an exponential distribution
- Higher λ values result in more frequent incidents (e.g., λ=0.2 averages one incident every 5 traces)
- Lower λ values result in more spread out incidents (e.g., λ=0.001 averages one incident every 1000 traces)
- Default values: [0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001]

Multiple lambda values can be provided to generate different incident frequency scenarios.


## Comparing Traces

PandoraTrace provides a robust comparison framework for analyzing two traces (e.g. a baseline and a synthetic trace) using SQL queries and Wasserstein distance metrics.

Before running comparisons, you need to have a SQLite database containing your traces. The database should have tables for both synthetic and baseline traces with the following schema:

Required columns:
- `traceId`: Unique identifier for each trace
- `spanId`: Unique identifier for each span within a trace
- `parentId`: Reference to parent span's ID
- `serviceName`: Name of the service that generated the span
- `startTime`: Timestamp when the span started
- `endTime`: Timestamp when the span ended
- `status`: Status code (0 for success, 1 for error)

Optional columns can include additional attributes you want to analyze.


Example table structure:
```sql
CREATE TABLE traces (
    traceId TEXT,
    spanId TEXT,
    parentId TEXT,
    serviceName TEXT,
    startTime INTEGER,
    endTime INTEGER,
    status INTEGER,
    -- Additional attributes can be added here
    PRIMARY KEY (traceId, spanId)
);
```

### Basic Implementation

```python
import sqlite3
from comparison import TraceComparator

# Initialize database connection
# Note: You need to create this database first with your trace data
conn = sqlite3.connect("traces.db")
comparator = TraceComparator(conn)

# Configure comparison parameters
parameters = {
    "entry_point": ["frontend", "backend"],
    "service_name": ["auth", "cart", "orders"],
    "service_name2": ["payment", "user"],
    "attr_name": ["status", "spanId"],
    "int_attr_name": ["duration", "startTime"]
}

# Execute comparison
results = comparator.compare_traces(
    table1="synthetic_traces",
    table2="baseline_traces",
    parameters=parameters
)
```

#### Available Query Templates

1. **Error Analysis**
   - Template: `error_traces`
   - Purpose: Error detection and analysis
   - Parameters: `entry_point`
   - Applicable incidents: crush, packet_loss

2. **Attribute Analysis**
   - Template: `attribute_traces`
   - Purpose: Attribute pattern analysis
   - Parameters: `entry_point`, `attr_name`
   - Applicable incidents: crush, packet_loss

3. **Architecture Discovery**
   - Template: `system_architecture`
   - Purpose: Service interaction analysis
   - Parameters: `service_name`, `service_name2`
   - Applicable incidents: crush, packet_loss

4. **Performance Analysis**
   - Template: `bottlenecks`
   - Purpose: Performance bottleneck detection
   - Parameters: `entry_point`, `service_name`
   - Applicable incidents: cpu_load, disk_io_stress, latency, memory_stress

5. **RED Metrics Suite**
   - Rate, Error, and Duration analysis
   - Parameters: `service_name`
   - Comprehensive incident coverage

6. **Advanced Attribute Analytics**
   - Frequency analysis
   - Time-window maximums
   - Filtered attribute analysis
   - Parameters: `attr_name`, `int_attr_name`, `service_name`

#### Custom Query Implementation

```python
from comparison import QueryTemplate

custom_query = QueryTemplate(
    name="custom_metric",
    query="""
    SELECT duration / 1000 as f, COUNT(*) as c
    FROM {table_name}
    WHERE serviceName = '{service_name}'
    GROUP BY duration / 1000
    """,
    relevant_incidents=["latency", "timeout"],
    description="Distribution of request durations"
)
```

#### Query Requirements

- Two-column output (`f`, `c`)
- Table name parameterization
- Parameter placeholder consistency
- Numerical output for distance calculation

## Contributing

We welcome community contributions to PandoraTrace. Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/enhancement`)
3. Commit changes (`git commit -m 'Add enhancement'`)
4. Push to branch (`git push origin feature/enhancement`)
5. Submit a Pull Request

## License

This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.


## Troubleshooting

### No traces collected
If you encounter the following error:
```
Baseline collected 0 traces in the <i>th iteration
```
Please follow the suggestion in https://github.com/delimitrou/DeathStarBench/issues/351 to downgrade the version of jaeger.

Specifically, in the file `<DeathStarBench_dir>/<app>/docker-compose.yml`, change the line from:
```
image: jaegertracing/all-in-one:latest
```
to
```
image: jaegertracing/all-in-one:1.62.0
```

## References

If you use this code in a publication, please cite the following work: 

@inproceedings{tochner2023gen,\
    title={Gen-T: Reduce Distributed Tracing Operational Costs Using Generative Models},\  
    author={Tochner, Saar and Fanti, Giulia and Sekar, Vyas},\
    booktitle={Temporal Graph Learning Workshop@ NeurIPS 2023},\
    year={2023}\
}
