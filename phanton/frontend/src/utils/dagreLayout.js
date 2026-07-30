import dagre from 'dagre'

const NODE_WIDTH = 220
const NODE_HEIGHT = 88

/**
 * Calcula posições Left→Right (ou TB) com dagre para um DAG React Flow.
 * @param {import('@xyflow/react').Node[]} nodes
 * @param {import('@xyflow/react').Edge[]} edges
 * @param {'LR'|'TB'|'RL'|'BT'} direction
 * @returns {{ nodes: import('@xyflow/react').Node[], edges: import('@xyflow/react').Edge[] }}
 */
export function getLayoutedElements(nodes, edges, direction = 'LR') {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))
  dagreGraph.setGraph({
    rankdir: direction,
    ranksep: 250,
    nodesep: 100,
  })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  const layoutedNodes = nodes.map((node) => {
    const pos = dagreGraph.node(node.id)
    return {
      ...node,
      targetPosition: direction === 'LR' ? 'left' : 'top',
      sourcePosition: direction === 'LR' ? 'right' : 'bottom',
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    }
  })

  return { nodes: layoutedNodes, edges }
}
