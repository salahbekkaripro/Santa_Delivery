"""
Community Detection — détecte les secteurs de livraison naturels via l'algorithme
Louvain sur le graphe de rues NetworkX/OSMnx.

Produit une enveloppe convexe (convex hull) par secteur pour affichage sur la carte.
"""
from __future__ import annotations

from networkx.algorithms.community import louvain_communities, greedy_modularity_communities
from shapely.geometry import MultiPoint

SECTOR_COLORS = [
    "#e74c3c",  # rouge
    "#3498db",  # bleu
    "#2ecc71",  # vert
    "#f39c12",  # orange
    "#9b59b6",  # violet
    "#1abc9c",  # turquoise
    "#e67e22",  # orange foncé
    "#34495e",  # gris ardoise
]

_LABELS = list("ABCDEFGHIJKLMNOP")


def detect_delivery_sectors(
    graph,
    *,
    seed: int = 42,
    resolution: float = 1.0,
) -> list[dict]:
    """
    Détecte les secteurs de livraison naturels via l'algorithme Louvain.

    Paramètres
    ----------
    graph      : graphe NetworkX dirigé (osmnx, attributs y=lat / x=lon sur les noeuds)
    seed       : graine de reproductibilité
    resolution : résolution Louvain (>1 → plus de secteurs, <1 → moins)

    Retourne
    --------
    list[dict] avec pour chaque secteur :
        sector_id   int
        label       str          "Secteur A", "Secteur B", ...
        color       str          couleur hex
        nodes       list         identifiants OSM des noeuds
        node_count  int
        center_lat  float
        center_lon  float
        polygon     list[list]   anneau GeoJSON fermé [[lat, lon], ...]
    """
    G_und = graph.to_undirected()

    try:
        communities = louvain_communities(G_und, seed=seed, resolution=resolution)
    except Exception:
        # Fallback si Louvain échoue (graph déconnecté, etc.)
        communities = list(greedy_modularity_communities(G_und))

    # Les grands secteurs en premier
    communities = sorted(communities, key=len, reverse=True)

    sectors: list[dict] = []
    for idx, community in enumerate(communities):
        nodes = list(community)
        lats = [float(graph.nodes[n]["y"]) for n in nodes if "y" in graph.nodes[n]]
        lons = [float(graph.nodes[n]["x"]) for n in nodes if "x" in graph.nodes[n]]

        if not lats:
            continue

        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)

        # Enveloppe convexe via Shapely (coordonnées (lon, lat) → retour [lat, lon])
        polygon: list[list[float]] = []
        if len(lats) >= 3:
            mp = MultiPoint(list(zip(lons, lats)))
            hull = mp.convex_hull
            if hull.geom_type == "Polygon":
                polygon = [[lat, lon] for lon, lat in hull.exterior.coords]
            elif hull.geom_type == "LineString":
                polygon = [[lat, lon] for lon, lat in hull.coords]
            elif hull.geom_type == "Point":
                polygon = [[hull.y, hull.x]]
        elif len(lats) == 2:
            polygon = [[lats[0], lons[0]], [lats[1], lons[1]]]
        else:
            polygon = [[lats[0], lons[0]]]

        sectors.append({
            "sector_id": idx,
            "label": f"Secteur {_LABELS[idx % len(_LABELS)]}",
            "color": SECTOR_COLORS[idx % len(SECTOR_COLORS)],
            "nodes": nodes,
            "node_count": len(nodes),
            "center_lat": round(center_lat, 6),
            "center_lon": round(center_lon, 6),
            "polygon": polygon,
        })

    return sectors
