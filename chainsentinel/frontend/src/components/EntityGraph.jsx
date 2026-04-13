import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import './EntityGraph.css';

const NODE_COLORS = {
  attacker: '#d03238',
  victim: '#d03238',
  protocol: '#3498db',
  mixer: '#868685',
  bridge: '#868685',
  cex: '#e67e22',
  unknown: '#555555',
};

const EDGE_COLORS = {
  value: '#d03238',
  structural: '#555555',
};

export function EntityGraph({ nodes = [], edges = [], onNodeClick }) {
  const svgRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const container = containerRef.current;
    const width = container?.clientWidth || 800;
    const height = container?.clientHeight || 600;

    svg.attr('viewBox', `0 0 ${width} ${height}`);

    const g = svg.append('g');

    // Zoom
    const zoom = d3.zoom()
      .scaleExtent([0.3, 5])
      .on('zoom', (event) => g.attr('transform', event.transform));
    svg.call(zoom);

    // Make deep copies so D3 mutation does not affect React props
    const nodesCopy = nodes.map(n => ({ ...n }));
    const edgesCopy = edges.map(e => ({ ...e }));

    // Simulation
    const simulation = d3.forceSimulation(nodesCopy)
      .force('link', d3.forceLink(edgesCopy).id(d => d.id).distance(120))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide(40));

    // Edges
    const link = g.append('g')
      .selectAll('line')
      .data(edgesCopy)
      .join('line')
      .attr('stroke', d => EDGE_COLORS[d.type] || EDGE_COLORS.structural)
      .attr('stroke-width', d => d.type === 'value' ? 2 : 1)
      .attr('stroke-opacity', 0.6);

    // Edge labels
    const linkLabel = g.append('g')
      .selectAll('text')
      .data(edgesCopy.filter(d => d.label))
      .join('text')
      .attr('font-size', '10px')
      .attr('fill', '#868685')
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('text-anchor', 'middle')
      .text(d => d.label);

    // Nodes
    const node = g.append('g')
      .selectAll('circle')
      .data(nodesCopy)
      .join('circle')
      .attr('r', d => d.role === 'attacker' || d.role === 'victim' ? 16 : 12)
      .attr('fill', d => NODE_COLORS[d.role] || NODE_COLORS.unknown)
      .attr('stroke', '#0e0f0c')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .on('click', (event, d) => onNodeClick?.(d))
      .call(d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
      );

    // Node labels
    const nodeLabel = g.append('g')
      .selectAll('text')
      .data(nodesCopy)
      .join('text')
      .attr('font-size', '11px')
      .attr('fill', 'white')
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('text-anchor', 'middle')
      .attr('dy', 28)
      .text(d => d.label || `${d.id.slice(0, 6)}...${d.id.slice(-4)}`);

    // Tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      linkLabel
        .attr('x', d => (d.source.x + d.target.x) / 2)
        .attr('y', d => (d.source.y + d.target.y) / 2);

      node.attr('cx', d => d.x).attr('cy', d => d.y);
      nodeLabel.attr('x', d => d.x).attr('y', d => d.y);
    });

    return () => simulation.stop();
  }, [nodes, edges, onNodeClick]);

  return (
    <div className="entity-graph" ref={containerRef}>
      <svg ref={svgRef} className="entity-graph__svg" />
      <div className="entity-graph__legend">
        <span className="entity-graph__legend-item">
          <span className="entity-graph__legend-dot" style={{ background: NODE_COLORS.attacker }} />
          Attacker / Victim
        </span>
        <span className="entity-graph__legend-item">
          <span className="entity-graph__legend-dot" style={{ background: NODE_COLORS.protocol }} />
          Known Protocol
        </span>
        <span className="entity-graph__legend-item">
          <span className="entity-graph__legend-dot" style={{ background: NODE_COLORS.mixer }} />
          Mixer / Bridge
        </span>
        <span className="entity-graph__legend-item">
          <span className="entity-graph__legend-dot" style={{ background: NODE_COLORS.cex }} />
          CEX
        </span>
      </div>
    </div>
  );
}
