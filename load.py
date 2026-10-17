#!/usr/bin/env python3
"""
load.py - FalkorDB loader for Keystone knowledge graph.

Features:
  - Reads data from data/ (or specified directory)
  - Connects using FALKORDB_HOST, FALKORDB_PORT, FALKORDB_PASSWORD (defaults: localhost:6379, graph "keystone")
  - Flag --reset drops graph first
  - Batched UNWIND + MERGE for nodes, then edges (edge props include lists)
  - Creates indexes: Person(id), Person(handle), Person(email), Service(name), Doc(id), Decision(topic), Team(id)
  - Fully idempotent
  - Prints node count per label and edge count per type
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from falkordb import FalkorDB
except ImportError:
    print("Error: 'falkordb' library is required. Install via 'pip install falkordb'.", file=sys.stderr)
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Load Keystone graph into FalkorDB")
    parser.add_argument("--data", type=str, default="data/", help="Path to data directory containing nodes.jsonl and edges.jsonl")
    parser.add_argument("--reset", action="store_true", help="Drop graph before loading")
    parser.add_argument("--host", type=str, default=os.getenv("FALKORDB_HOST", "localhost"), help="FalkorDB host")
    parser.add_argument("--port", type=int, default=int(os.getenv("FALKORDB_PORT", "6379")), help="FalkorDB port")
    parser.add_argument("--password", type=str, default=os.getenv("FALKORDB_PASSWORD") or None, help="FalkorDB password")
    parser.add_argument("--graph", type=str, default=os.getenv("FALKORDB_GRAPH", "keystone"), help="Graph name")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for UNWIND MERGE")
    return parser.parse_args()


def create_indexes(graph):
    """
    Creates required indexes idempotently:
      Person(id), Person(handle), Person(email),
      Service(name), Doc(id), Decision(topic), Team(id)
    """
    indexes = [
        ("Person", "id"),
        ("Person", "handle"),
        ("Person", "email"),
        ("Service", "name"),
        ("Doc", "id"),
        ("Decision", "topic"),
        ("Team", "id"),
    ]
    print("Creating / verifying indexes...")
    for label, prop in indexes:
        query = f"CREATE INDEX FOR (n:{label}) ON (n.{prop})"
        try:
            graph.query(query)
            print(f"  [+] Index created on :{label}({prop})")
        except Exception as e:
            err_msg = str(e).lower()
            if "already indexed" in err_msg or "already exists" in err_msg:
                print(f"  [=] Index already exists on :{label}({prop})")
            else:
                print(f"  [!] Warning on index {label}({prop}): {e}")


def load_nodes(graph, nodes_path, batch_size=1000):
    """
    Loads nodes grouped by label using batched UNWIND + MERGE.
    """
    print(f"Loading nodes from {nodes_path} ...")
    nodes_by_label = defaultdict(list)
    total_nodes = 0

    with open(nodes_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            label = item.get("label", "Node")
            # Create a clean copy of props without the label key
            props = dict(item)
            props.pop("label", None)
            nodes_by_label[label].append(props)
            total_nodes += 1

    for label, items in nodes_by_label.items():
        print(f"  Loading {len(items):,} nodes for label :{label} ...")
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            query = f"UNWIND $batch AS row MERGE (n:{label} {{id: row.id}}) SET n += row"
            graph.query(query, {"batch": batch})

    print(f"Loaded {total_nodes:,} nodes across {len(nodes_by_label)} labels.")


def load_edges(graph, edges_path, batch_size=1000):
    """
    Loads edges grouped by type using batched UNWIND + MERGE.
    Preserves list properties (src_ids, src_conf, src_auth, spans).
    """
    print(f"Loading edges from {edges_path} ...")
    edges_by_type = defaultdict(list)
    total_edges = 0

    with open(edges_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            edge_type = item.get("type", "RELATED_TO")
            edges_by_type[edge_type].append(item)
            total_edges += 1

    for edge_type, items in edges_by_type.items():
        print(f"  Loading {len(items):,} edges for type -[:{edge_type}]-> ...")
        query = f"""
        UNWIND $batch AS row
        MATCH (a {{id: row.src}})
        MATCH (b {{id: row.dst}})
        MERGE (a)-[r:{edge_type} {{eid: row.eid}}]->(b)
        SET r.src_ids = row.src_ids,
            r.src_conf = row.src_conf,
            r.src_auth = row.src_auth,
            r.spans = row.spans,
            r.valid_from = row.valid_from,
            r.valid_to = row.valid_to,
            r.status = row.status,
            r.derived_reason = row.derived_reason
        """
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            graph.query(query, {"batch": batch})

    print(f"Loaded {total_edges:,} edges across {len(edges_by_type)} edge types.")


def print_counts(graph):
    """
    Prints node counts per label and edge counts per type.
    """
    print("\n" + "=" * 50)
    print("GRAPH SUMMARY")
    print("=" * 50)

    # Node count per label
    res_nodes = graph.query("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC")
    print("\nNode Counts per Label:")
    total_nodes = 0
    for row in res_nodes.result_set:
        label, cnt = row[0], row[1]
        print(f"  {label:<15}: {cnt:>8,}")
        total_nodes += cnt
    print(f"  {'Total Nodes':<15}: {total_nodes:>8,}")

    # Edge count per type
    res_edges = graph.query("MATCH ()-[r]->() RETURN type(r) AS edge_type, count(r) AS cnt ORDER BY cnt DESC")
    print("\nEdge Counts per Type:")
    total_edges = 0
    for row in res_edges.result_set:
        etype, cnt = row[0], row[1]
        print(f"  {etype:<15}: {cnt:>8,}")
        total_edges += cnt
    print(f"  {'Total Edges':<15}: {total_edges:>8,}")
    print("=" * 50 + "\n")


def main():
    args = parse_args()
    data_dir = Path(args.data)
    nodes_file = data_dir / "nodes.jsonl"
    edges_file = data_dir / "edges.jsonl"

    if not nodes_file.exists() or not edges_file.exists():
        print(f"Error: Missing data files in {data_dir}. Run generate.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to FalkorDB at {args.host}:{args.port} (graph: '{args.graph}') ...")
    try:
        db = FalkorDB(host=args.host, port=args.port, password=args.password)
        graph = db.select_graph(args.graph)
    except Exception as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        sys.exit(1)

    if args.reset:
        print(f"Reset flag detected. Dropping graph '{args.graph}'...")
        try:
            graph.delete()
            print("Graph deleted successfully.")
        except Exception as e:
            print(f"Note on graph deletion: {e}")
        # Re-select graph after deletion
        graph = db.select_graph(args.graph)

    # 1. Create indexes
    create_indexes(graph)

    # 2. Load nodes
    load_nodes(graph, nodes_file, batch_size=args.batch_size)

    # 3. Load edges
    load_edges(graph, edges_file, batch_size=args.batch_size)

    # 4. Print summary counts
    print_counts(graph)
    print("Graph loading completed successfully.")


if __name__ == "__main__":
    main()
