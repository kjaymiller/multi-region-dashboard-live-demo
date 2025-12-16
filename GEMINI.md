# Project Overview

This project is a multi-region PostgreSQL testing dashboard. It is a web application built with FastAPI (a Python web framework) that allows users to manage and test PostgreSQL database connections across different geographical regions.

The frontend is built using HTMX, Jinja2, Alpine.js, and Bootstrap, which allows for a dynamic and interactive user interface without the need for a large JavaScript framework.

The application supports two backends for storing connection information: a simple file-based storage and a more robust PostgreSQL backend that uses TimescaleDB for time-series data.

## Key Features

*   **Database Connection Management:** Create, read, update, and delete PostgreSQL connection settings.
*   **Connection Testing:** Test the connectivity to the configured databases.
*   **Latency Measurement:** Measure the latency of queries to the databases.
*   **Load Testing:** Run simple load tests to gauge database performance.
*   **Health Metrics:** View health metrics of the connected databases, such as cache hit ratio and active connections.
*   **Geographic Visualization:** View the location of the database regions on a map.
*   **AI Chat Assistant:** An AI-powered chat assistant to provide performance insights.

# Building and Running

The project uses `uv` for package management and `just` as a command runner.

## Prerequisites

*   Python 3.10 or higher
*   `uv`
*   `just` (optional, but recommended)
*   A PostgreSQL database (for the application's backend storage)

## Setup

1.  **Install dependencies:**
    ```bash
    just setup
    ```
    This will install the necessary Python packages and create a `.env` file from the `.env.example`.

2.  **Configure environment variables:**
    Edit the `.env` file to add your database connection strings and any other required configuration.

3.  **Set up the database schema:**
    ```bash
    just db-setup
    ```
    This will create the necessary tables in the backend database.

## Running the Application

*   **Development:**
    ```bash
    just dev
    ```
    This will start the development server with auto-reload.

*   **Production:**
    ```bash
    just serve
    ```
    This will start the application in production mode.

# Development Conventions

*   **Code Formatting:** The project uses `black` for code formatting. To format the code, run:
    ```bash
    just format
    ```

*   **Linting:** The project uses `ruff` for linting. To lint the code, run:
    ```bash
    just lint
    ```

*   **Type Checking:** The project uses `mypy` for static type checking. To type-check the code, run:
    ```bash
    just typecheck
    ```

*   **All Checks:** To run all checks (formatting, linting, and type-checking), run:
    ```bash
    just check
    ```
