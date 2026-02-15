import { Block } from './block';

export class BlockGrid {
  // Grid is column-major: grid[x][y] where x=column, y=row.
  // null means the block was removed (empty cell).
  public grid: (Block | null)[][] = [];

  constructor(public numCols: number, public numRows: number) {
    for (let x = 0; x < numCols; x++) {
      const col: (Block | null)[] = [];
      for (let y = 0; y < numRows; y++) {
        col.push(new Block());
      }
      this.grid.push(col);
    }
  }

  // --- Step 1: Flood fill to find all connected same-color blocks ---
  private findConnected(x: number, y: number): [number, number][] {
    const block = this.grid[x][y];
    if (!block) return []; // clicked an empty cell, do nothing

    const targetColour = block.colour;
    const visited = new Set<string>();
    const connected: [number, number][] = [];
    const queue: [number, number][] = [[x, y]];
    visited.add(`${x},${y}`);

    while (queue.length > 0) {
      const [cx, cy] = queue.shift()!;
      connected.push([cx, cy]);

      // Check all 4 neighbors: up, down, left, right
      const neighbors: [number, number][] = [
        [cx - 1, cy], // left
        [cx + 1, cy], // right
        [cx, cy - 1], // up
        [cx, cy + 1], // down
      ];

      for (const [nx, ny] of neighbors) {
        // Skip out-of-bounds
        if (nx < 0 || nx >= this.numCols || ny < 0 || ny >= this.numRows) continue;
        // Skip already visited
        const key = `${nx},${ny}`;
        if (visited.has(key)) continue;
        // Skip empty cells
        const neighbor = this.grid[nx][ny];
        if (!neighbor) continue;
        // Skip different colors
        if (neighbor.colour !== targetColour) continue;

        visited.add(key);
        queue.push([nx, ny]);
      }
    }

    return connected;
  }

  // --- Step 2 & 3: Remove blocks, then apply gravity ---
  clicked(x: number, y: number) {
    // Find all connected blocks of the same color
    const connected = this.findConnected(x, y);
    if (connected.length === 0) return;

    // Remove them (set to null)
    for (const [cx, cy] of connected) {
      this.grid[cx][cy] = null;
    }

    // Apply gravity: in each column, non-null blocks sink to the bottom
    for (let col = 0; col < this.numCols; col++) {
      // Collect the surviving (non-null) blocks, keeping their top-to-bottom order
      const surviving = this.grid[col].filter((b): b is Block => b !== null);
      // Pad the top with nulls, then the surviving blocks at the bottom
      const nullCount = this.numRows - surviving.length;
      this.grid[col] = [...new Array(nullCount).fill(null), ...surviving];
    }
  }
}
