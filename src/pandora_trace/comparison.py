
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Iterator
import sqlite3
from collections import OrderedDict
import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class QueryTemplate:
    """Represents a SQL query template for trace comparison."""
    name: str
    query: str
    relevant_incidents: List[str]
    description: Optional[str] = None


class TraceComparator:
    """Compares trace data between two SQL tables using configurable queries."""

    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize the comparator with a database connection.

        Args:
            connection: SQLite database connection
        """
        self.connection = connection
        self.default_queries = [
            QueryTemplate(
                name="error_traces",
                query="""
                SELECT S1.startTime / 3600 as f, COUNT(*) as c
                FROM {table_name} as S1, {table_name} as S2
                WHERE S1.serviceName = '{entry_point}'
                  AND S1.traceId = S2.traceId
                  AND S2.status = 1
                GROUP BY S1.startTime / 3600;
                """,
                relevant_incidents=["crush", "packet_loss"],
                description="Find traces of a service that having an error"
            ),
            QueryTemplate(
                name="attribute_traces",
                query="""
                SELECT S2.{attr_name} as f, COUNT(*) as c
                FROM {table_name} as S1, {table_name} as S2
                WHERE S1.serviceName = '{entry_point}'
                  AND S1.traceId = S2.traceId
                GROUP BY S2.{attr_name};
                """,
                relevant_incidents=["crush", "packet_loss"],
                description="Find traces that have a particular attribute"
            ),
            QueryTemplate(
                name="system_architecture",
                query="""
                SELECT S1.startTime / 3600 as f, COUNT(*) as c
                FROM {table_name} as S1, {table_name} as S2
                Where S1.spanId = S2.parentId
                    AND S1.serviceName = '{service_name}'
                    AND S2.serviceName = '{service_name2}'
                GROUP BY S1.startTime / 3600;
                """,
                relevant_incidents=["crush", "packet_loss"],
                description="Discover architecture of the whole system"
            ),
            QueryTemplate(
                name="bottlenecks",
                query="""
                SELECT ROUND((S2.endTime - S2.startTime) / (S1.endTime - S1.startTime), 1) AS f, count(*) as c
                FROM {table_name} as S1, {table_name} as S2
                WHERE S1.serviceName = '{entry_point}'
                  AND S2.serviceName = '{service_name}'
                  AND S1.traceId = S2.traceId
                GROUP BY f;
                """,
                relevant_incidents=["cpu_load", "disk_io_stress", "latency", "memory_stress"],
                description="Find bottlenecks"
            ),
            QueryTemplate(
                name="red_rate",
                query="""
                SELECT startTime / 3600 as f, COUNT(*) as c
                FROM {table_name}
                WHERE serviceName = '{service_name}'
                GROUP BY startTime / 3600;
                """,
                relevant_incidents=["crush", "packet_loss", "cpu_load", "disk_io_stress", "latency", "memory_stress"],
                description="RED metrics - rate"
            ),
            QueryTemplate(
                name="red_error",
                query="""
                SELECT endTime - startTime as f, COUNT(*) as c
                FROM {table_name}
                WHERE serviceName = '{service_name}'
                    AND status = 1
                GROUP BY endTime - startTime;
                """,
                relevant_incidents=["crush", "packet_loss", "cpu_load", "disk_io_stress", "latency", "memory_stress"],
                description="RED metrics - error"
            ),
            QueryTemplate(
                name="red_duration",
                query="""
                SELECT endTime - startTime as f, COUNT(*) as c
                FROM {table_name}
                WHERE serviceName = '{service_name}'
                GROUP BY endTime - startTime;
                """,
                relevant_incidents=["crush", "packet_loss", "cpu_load", "disk_io_stress", "latency", "memory_stress"],
                description="RED metrics - duration"
            ),
            QueryTemplate(
                name="attribute_frequency",
                query="""
                SELECT {attr_name} as f, count(*) as c
                FROM {table_name}
                GROUP BY {attr_name};
                """,
                relevant_incidents=["crush", "packet_loss", "cpu_load", "disk_io_stress", "latency", "memory_stress"],
                description="Frequency of an attribute"
            ),
            QueryTemplate(
                name="attribute_max_window",
                query="""
                SELECT startTime / 3600 as f, MAX({int_attr_name}) as c
                FROM {table_name}
                Where serviceName = '{service_name}'
                GROUP BY startTime / 3600;
                """,
                relevant_incidents=["crush", "packet_loss"],
                description="Max value of an attribute for every 5 minute window"
            ),
            QueryTemplate(
                name="filtered_attribute_frequency",
                query="""
                SELECT {attr_name} as f, count(*) as c
                FROM {table_name}
                Where serviceName = '{service_name}'
                GROUP BY {attr_name};
                """,
                relevant_incidents=["crush", "packet_loss"],
                description="Frequency of an attribute after filtering by another attribute"
            )
        ]

    def compare_traces(
            self,
            table1: str,
            table2: str,
            parameters: Dict[str, List[str]],
            queries: Optional[List[QueryTemplate]] = None
    ) -> Dict[str, float]:
        """
        Compare traces between two tables using specified parameters and queries.

        Args:
            table1: Name of first table to compare
            table2: Name of second table to compare
            parameters: Dictionary mapping parameter names to possible values
            queries: Optional list of QueryTemplate objects. Uses default queries if None.

        Returns:
            Dictionary mapping query names to their Wasserstein distances
        """
        queries = queries or self.default_queries
        results = {}

        for query_template in queries:
            distances = []
            for params in self._iterate_parameters(query_template.query, parameters):
                syn_data = self._execute_query(query_template.query, table1, params)
                real_data = self._execute_query(query_template.query, table2, params)

                if len(syn_data) > 0 and len(real_data) > 0:
                    distance = self._calculate_wasserstein(syn_data, real_data)
                    if distance is not None:
                        distances.append(distance)

            if distances:
                results[query_template.name] = np.mean(distances)

        return results

    def _execute_query(self, query: str, table: str, params: Dict[str, str]) -> pd.DataFrame:
        """Execute a query and return results as a DataFrame."""
        formatted_query = query.format(table_name=table, **params)
        return pd.read_sql_query(formatted_query, self.connection)

    @staticmethod
    def _calculate_wasserstein(syn: pd.DataFrame, real: pd.DataFrame) -> Optional[float]:
        """Calculate Wasserstein distance between two distributions."""
        syn["c"] = syn["c"] / syn["c"].sum()
        real["c"] = real["c"] / real["c"].sum()

        all_features = set(syn["f"].values) | set(real["f"].values)
        syn = syn.set_index("f").reindex(all_features).fillna(0)
        real = real.set_index("f").reindex(all_features).fillna(0)

        return stats.wasserstein_distance(syn["c"], real["c"])

    @staticmethod
    def _iterate_parameters(query: str, parameters: Dict[str, List[str]]) -> Iterator[Dict[str, str]]:
        """Generate all possible parameter combinations for a query."""
        from string import Formatter

        def _inner(partial: Dict[str, str], params_left: List[str]) -> Iterator[Dict[str, str]]:
            if not params_left:
                yield partial
                return

            name = params_left[0]
            for value in parameters[name]:
                new_partial = partial.copy()
                new_partial[name] = value
                yield from _inner(new_partial, params_left[1:])

        query_params = {t[1] for t in Formatter().parse(query) if t[1] is not None}
        relevant_params = [p for p in parameters if p in query_params]

        return _inner({}, relevant_params)