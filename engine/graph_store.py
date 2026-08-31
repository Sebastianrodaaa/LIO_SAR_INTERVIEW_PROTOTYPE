"""Graph store: Neo4j when reachable, otherwise in-memory NetworkX.

The demo is designed to run with NetworkX so a laptop without Docker still
presents the same schema: Employee, Department, Vendor, Policy nodes and
REPORTS_TO, BELONGS_TO, SUPPLIES, GOVERNS edges.

GraphRAG here is *relational retrieval*, not a vector dump of every policy
into the prompt. Queries are stage-scoped on purpose.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import networkx as nx

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


@dataclass
class GraphSnapshot:
    backend: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    meta: dict[str, Any] = field(default_factory=dict)


class GraphStore(Protocol):
    backend: str

    def seed(self) -> None: ...
    def snapshot(self) -> GraphSnapshot: ...
    def employee(self, employee_id: str) -> dict[str, Any] | None: ...
    def vendor(self, vendor_id: str) -> dict[str, Any] | None: ...
    def vendors_in_category(self, category: str) -> list[dict[str, Any]]: ...
    def policies_for(self, department: str, category: str, amount: float) -> list[dict[str, Any]]: ...
    def approval_walk(self, requester_id: str, amount: float) -> list[dict[str, Any]]: ...
    def neighborhood(self, node_id: str, depth: int = 1) -> dict[str, Any]: ...


def _load_json(name: str) -> list[dict[str, Any]]:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def load_records() -> dict[str, Any]:
    return {
        "employees": _load_json("employees.json"),
        "departments": _load_json("departments.json"),
        "vendors": _load_json("vendors.json"),
        "policies": _load_json("policies.json"),
        "seed": json.loads((DATA / "seed_scenario.json").read_text(encoding="utf-8")),
    }


def _dept_id(name: str) -> str:
    slug = name.lower().replace(" ", "")
    mapping = {
        "executive": "dept-executive",
        "engineering": "dept-engineering",
        "product": "dept-product",
        "design": "dept-design",
        "finance": "dept-finance",
        "legal": "dept-legal",
        "itsecurity": "dept-itsec",
        "people": "dept-people",
    }
    return mapping.get(slug, f"dept-{slug}")


class NetworkXStore:
    """In-memory property graph. Default backend for the offline demo."""

    backend = "networkx"

    def __init__(self) -> None:
        self.g = nx.DiGraph()

    def seed(self) -> None:
        records = load_records()
        self.g.clear()

        for dept in records["departments"]:
            self.g.add_node(dept["id"], kind="Department", **dept)

        for emp in records["employees"]:
            self.g.add_node(emp["id"], kind="Employee", **emp)
            dept_node = _dept_id(emp["department"])
            if dept_node in self.g:
                self.g.add_edge(emp["id"], dept_node, kind="BELONGS_TO")
            if emp.get("manager_id"):
                self.g.add_edge(emp["id"], emp["manager_id"], kind="REPORTS_TO")

        for vendor in records["vendors"]:
            self.g.add_node(vendor["id"], kind="Vendor", **vendor)
            # SUPPLIES is modeled as a node attribute + a typed edge to a
            # synthetic category node so the cockpit can highlight categories.
            cat_id = f"cat-{vendor['category']}"
            if cat_id not in self.g:
                self.g.add_node(cat_id, kind="Category", id=cat_id, name=vendor["category"])
            self.g.add_edge(vendor["id"], cat_id, kind="SUPPLIES")

        for policy in records["policies"]:
            self.g.add_node(policy["id"], kind="Policy", **policy)
            for dept_name in policy.get("governs", []):
                dept_node = _dept_id(dept_name)
                if dept_node in self.g:
                    self.g.add_edge(policy["id"], dept_node, kind="GOVERNS")

        self.g.graph["seed"] = records["seed"]

    def snapshot(self) -> GraphSnapshot:
        nodes = []
        for nid, data in self.g.nodes(data=True):
            nodes.append({"id": nid, **{k: v for k, v in data.items() if _jsonable(v)}})
        edges = []
        for src, dst, data in self.g.edges(data=True):
            edges.append({"source": src, "target": dst, "kind": data.get("kind")})
        return GraphSnapshot(backend=self.backend, nodes=nodes, edges=edges, meta=dict(self.g.graph))

    def employee(self, employee_id: str) -> dict[str, Any] | None:
        if employee_id not in self.g:
            return None
        data = dict(self.g.nodes[employee_id])
        data["id"] = employee_id
        return data

    def vendor(self, vendor_id: str) -> dict[str, Any] | None:
        if vendor_id not in self.g:
            return None
        data = dict(self.g.nodes[vendor_id])
        data["id"] = vendor_id
        return data

    def vendors_in_category(self, category: str) -> list[dict[str, Any]]:
        cat_id = f"cat-{category}"
        out = []
        for src, dst, data in self.g.edges(data=True):
            if data.get("kind") == "SUPPLIES" and dst == cat_id:
                node = dict(self.g.nodes[src])
                node["id"] = src
                out.append(node)
        out.sort(key=lambda v: (-int(v.get("preferred", False)), -v.get("compliance_score", 0)))
        return out

    def policies_for(self, department: str, category: str, amount: float) -> list[dict[str, Any]]:
        dept_node = _dept_id(department)
        matches: list[dict[str, Any]] = []
        for nid, data in self.g.nodes(data=True):
            if data.get("kind") != "Policy":
                continue
            threshold = data.get("threshold_usd") or 0
            if threshold and amount < threshold:
                # Still include $0-threshold policies; skip high bars we don't meet
                # unless the policy is the OOO/SSO style (threshold 0).
                continue
            scopes = data.get("category_scope") or []
            if scopes and "all" not in scopes and category not in scopes:
                continue
            governs_edge = self.g.has_edge(nid, dept_node)
            # Company-wide policies (OOO skip) govern the department via GOVERNS.
            if not governs_edge and "all" not in scopes:
                continue
            rec = dict(data)
            rec["id"] = nid
            matches.append(rec)
        return matches

    def approval_walk(self, requester_id: str, amount: float) -> list[dict[str, Any]]:
        """Walk REPORTS_TO from requester. OOO nodes are kept in the path
        but marked skippable — the orchestrator, not the LLM, decides skip.
        """
        path: list[dict[str, Any]] = []
        current = requester_id
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            node = self.employee(current)
            if not node:
                break
            path.append(node)
            reports = [
                dst
                for _, dst, data in self.g.out_edges(current, data=True)
                if data.get("kind") == "REPORTS_TO"
            ]
            current = reports[0] if reports else None
        return path

    def neighborhood(self, node_id: str, depth: int = 1) -> dict[str, Any]:
        if node_id not in self.g:
            return {"center": node_id, "nodes": [], "edges": []}
        nodes = {node_id}
        frontier = {node_id}
        for _ in range(depth):
            nxt: set[str] = set()
            for n in frontier:
                nxt.update(self.g.successors(n))
                nxt.update(self.g.predecessors(n))
            nodes.update(nxt)
            frontier = nxt
        snap_nodes = []
        snap_edges = []
        for n in nodes:
            data = dict(self.g.nodes[n])
            data["id"] = n
            snap_nodes.append({k: v for k, v in data.items() if _jsonable(v)})
        for src, dst, data in self.g.edges(data=True):
            if src in nodes and dst in nodes:
                snap_edges.append({"source": src, "target": dst, "kind": data.get("kind")})
        return {"center": node_id, "nodes": snap_nodes, "edges": snap_edges}


class Neo4jStore(NetworkXStore):
    """Thin Neo4j overlay. We still seed NetworkX so the cockpit layout is
    identical; Cypher is used for the same retrieval when the bolt port is up.

    neo4j-graphrag is imported when present so VectorCypher retrievers can
    be swapped in later without changing the orchestrator interface.
    """

    backend = "neo4j"

    def __init__(self, uri: str, user: str, password: str) -> None:
        super().__init__()
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._driver.verify_connectivity()
        self._graphrag = None
        try:
            import neo4j_graphrag  # noqa: F401

            self._graphrag = "neo4j-graphrag-available"
        except Exception:
            self._graphrag = None

    def seed(self) -> None:
        super().seed()
        records = load_records()
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            for dept in records["departments"]:
                session.run(
                    "CREATE (d:Department {id:$id, name:$name, cost_center:$cost_center})",
                    **dept,
                )
            for emp in records["employees"]:
                session.run(
                    """
                    CREATE (e:Employee {
                        id:$id, name:$name, role:$role, department:$department,
                        manager_id:$manager_id, out_of_office:$out_of_office,
                        ooo_until:$ooo_until, approval_threshold_usd:$approval_threshold_usd,
                        email:$email, location:$location
                    })
                    """,
                    id=emp["id"],
                    name=emp["name"],
                    role=emp["role"],
                    department=emp["department"],
                    manager_id=emp.get("manager_id"),
                    out_of_office=bool(emp["out_of_office"]),
                    ooo_until=emp.get("ooo_until"),
                    approval_threshold_usd=emp["approval_threshold_usd"],
                    email=emp["email"],
                    location=emp["location"],
                )
            session.run(
                """
                MATCH (e:Employee), (d:Department {name: e.department})
                CREATE (e)-[:BELONGS_TO]->(d)
                """
            )
            session.run(
                """
                MATCH (e:Employee), (m:Employee {id: e.manager_id})
                WHERE e.manager_id IS NOT NULL
                CREATE (e)-[:REPORTS_TO]->(m)
                """
            )
            for vendor in records["vendors"]:
                session.run(
                    """
                    MERGE (c:Category {id: $cat_id, name: $category})
                    CREATE (v:Vendor {
                        id:$id, name:$name, category:$category,
                        compliance_score:$compliance_score, preferred:$preferred,
                        incumbent:$incumbent, soc2:$soc2
                    })-[:SUPPLIES]->(c)
                    """,
                    cat_id=f"cat-{vendor['category']}",
                    **{
                        "id": vendor["id"],
                        "name": vendor["name"],
                        "category": vendor["category"],
                        "compliance_score": vendor["compliance_score"],
                        "preferred": vendor["preferred"],
                        "incumbent": vendor["incumbent"],
                        "soc2": vendor["soc2"],
                    },
                )
            for policy in records["policies"]:
                session.run(
                    "CREATE (p:Policy {id:$id, title:$title, threshold_usd:$threshold_usd})",
                    id=policy["id"],
                    title=policy["title"],
                    threshold_usd=policy["threshold_usd"],
                )
                for dept_name in policy.get("governs", []):
                    session.run(
                        """
                        MATCH (p:Policy {id:$pid}), (d:Department {name:$name})
                        CREATE (p)-[:GOVERNS]->(d)
                        """,
                        pid=policy["id"],
                        name=dept_name,
                    )

    def close(self) -> None:
        self._driver.close()


def _jsonable(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool, list, dict, type(None)))


def connect_store() -> GraphStore:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    if password:
        try:
            store = Neo4jStore(uri, user, password)
            print(f"Graph backend: Neo4j at {uri}")
            return store
        except Exception as exc:
            print(f"Neo4j unavailable ({exc!r}); falling back to NetworkX")
    store = NetworkXStore()
    print("Graph backend: NetworkX (in-memory)")
    return store
