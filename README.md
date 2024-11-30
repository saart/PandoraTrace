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
   - Utilizes system tools:
     - `stress` package for CPU/memory simulation
     - `iproute2` for network latency injection

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

### Installation

```bash
# Clone repository
git clone https://github.com/saart/PandoraTrace.git
cd PandoraTrace

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

PandoraTrace operates in two primary modes:

1. Raw trace generation
2. Trace comparison analysis

### Creating Raw Traces

The framework provides three main functionalities for trace generation:

#### 1. Baseline Trace Creation
```bash
python run_benchmark.py <app_name> --create_baseline
```
Generates baseline traces without incident injection.

#### 2. Incident Testing
```bash
python run_benchmark.py <app_name> --run_test
```
- Deploys specified microservice application
- Injects configured incidents
- Generates traffic via RESTler
- Captures and converts Jaeger traces

#### 3. Trace Merging
```bash
python run_benchmark.py <app_name> --prepare_traces [--lambda_values LAMBDA...]
```
Combines incident and baseline traces using configurable distribution parameters.

### Comparing Traces

PandoraTrace provides a robust comparison framework for analyzing baseline and synthetic traces using SQL queries and Wasserstein distance metrics.

#### Basic Implementation

```python
import sqlite3
from comparison import TraceComparator

# Initialize database connection
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